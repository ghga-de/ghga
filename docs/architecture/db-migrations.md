# MongoDB migrations in services

A service whose stored documents change shape migrates its database with hexkit's migration framework.
The framework, its version records and its lock are described on hexkit's [MongoDB Migrations](../../libs/hexkit/user_guide/providers/mongodb_migrations.qmd) page; this page adds how GHGA services use it.
Each service keeps its migrations in a `migrations/` package and runs them with its `migrate-db` command.
The chart runs that command in an init container before every pod start, and every other command first checks that the database is at the version the release expects.
The work package service (wps) is the model: [`wps/migrations/`](../../services/work-package-service/src/wps/migrations/), [`wps/main.py`](../../services/work-package-service/src/wps/main.py), [`wps/cli.py`](../../services/work-package-service/src/wps/cli.py) and [`tests/migrations/`](../../services/work-package-service/tests/migrations/).
[ADR-0022](../adrs/adr-0022-db-migrations.md) records why migrations live in each service.

Twelve services migrate today: ars, auth-service, dcs, dlqs, fis, ifrs, nos, ns, pcs, rs, rts and wps.

## The parts

| Part | Where, in wps | What it holds |
|---|---|---|
| Definitions | `migrations/definitions/v2.py`, `v3.py` | One `MigrationDefinition` subclass per version, named `V<n>Migration` |
| Migration map | `migrations/entry.py` | `MIGRATION_MAP: MigrationMap = {2: V2Migration, 3: V3Migration}`, exported by `migrations/__init__.py` |
| Target version | `main.py` | `DB_VERSION = 3`, the version this release expects |
| Migration entry point | `main.py` | `migrate_db()`, which opens `MigrationManager` with `DB_VERSION` and `MIGRATION_MAP` and calls `migrate_or_wait()` |
| Commands | `cli.py` | `migrate-db`, which runs `migrate_db()`, and a typer callback that calls `check_db_version()` before any other command |
| Config | `config.py` | `Config` inherits `MigrationConfig` |
| Chart values | `chart-values.yaml` | `migrationInitContainer` with `executable` and `executableArgs: [migrate-db]`, and the migration settings under `config` |

Most services keep their definitions in one flat `migrations/definitions.py`; for a new service, use the package with one module per version, as wps, dcs and ifrs do.

The migration settings are the same everywhere: `db_version_collection` is `<abbr>DbVersions` (`wpsDbVersions`), `migration_wait_sec` is 10 and `migration_max_wait_sec` is 600 in the chart values.
The maximum wait makes a pod waiting on a stuck lock fail after ten minutes instead of hanging; hexkit's default is to wait forever.

## How a release migrates

The chart generator (`deploy/src/create_charts.py`) sets `migrationInitContainer.enabled: true` for every member whose `chart-values.yaml` names a migration command, and `ghga-common` then prepends a `migration` init container to each of the service's pods.
It runs `<executable> migrate-db` with the main container's image and environment, so it reads the same config.
Every pod of the service runs it, the REST and the consumer pod alike; the lock in the version collection lets one migrate while the others wait.

After the init container, the main container's command checks the version first.
`check_db_version()` raises `DbVersionMismatchError` unless the database version equals `DB_VERSION`, and its message says whether the database is behind or ahead.
The equality is deliberate: a pod of the old release that restarts after the new release has migrated stops instead of working on a schema it does not know.
Anything else that starts a service, such as a local run, must run `migrate-db` first, too.

A database is never migrated backward in a deployment.
`migrate-db` always targets the release's `DB_VERSION`, and an older release's map lacks the newer definitions, so its `migrate-db` fails with `NotImplementedError` on a database that is ahead.
`unapply()` runs only from code that has the newer definition, in practice the migration tests.

## Adding a migration

1. Change the model, then write `V<n>Migration` for the next version in `migrations/definitions/`, with `version = n`.
2. Add it to `MIGRATION_MAP` and to the exports of `migrations/__init__.py`.
3. Set `DB_VERSION` in `main.py` to `n`.
4. Write its test (below).

Most definitions follow one of these shapes:

- **Convert documents in place:** a change function passed to `migrate_docs_in_collection()` inside `async with self.auto_finalize(coll_names=[...], copy_indexes=True)`, with `validation_model` and `id_field` so each document is checked against the current model.
  wps [`v2.py`](../../services/work-package-service/src/wps/migrations/definitions/v2.py) uses hexkit's `convert_uuids_and_datetimes_v6` helper; [`v3.py`](../../services/work-package-service/src/wps/migrations/definitions/v3.py) writes its own change function.
- **Persisted events:** the collection of a `PersistentKafkaPublisher` takes `id_field="compaction_key"` and `PersistentKafkaEvent` as the validation model, as in pcs.
  Pass a smaller `batch_size` for large documents, as fis does (25).
- **Changed IDs or indexes:** pass `copy_indexes=False` when the migration changes the index layout or the `_id`, as dcs [`v3.py`](../../services/dcs/src/dcs/migrations/definitions/v3.py) does.
- **Validating against a model that has changed since:** define it locally in the definition, as ifrs [`v2.py`](../../services/ifrs/src/ifrs/migrations/definitions/v2.py) does with `FileMetadata`.
  Validation runs only in the last migration of a run; pass `force_validate=True` to run it in every migration.
- **Beyond the helpers:** work on `self._db` directly when documents move between collections or into GridFS (rts), when a collection is dropped (ns), or when outbox documents with `__metadata__` cannot pass validation (rs).

Whatever the shape:

- **Make the change function idempotent.**
  If a document is already in the new shape, return it unchanged, and raise on a shape that is neither old nor new, as wps `v3.py` does.
  A database whose version record is missing then passes through the migration unchanged, and an unknown shape stops it before anything is written.
- **Make it reversible when you can:** inherit `Reversible` and implement `unapply()`, so the test can check the round trip.
  A migration that drops data or derives new IDs cannot be reversed (dcs V3, ifrs V3, ns V2); leave `Reversible` out.

## The first migration of a service

ucs, dins and mass use MongoDB without migrations.
ucs already inherits `MigrationConfig` in its `Config`, so deployments need no config change when its first migration comes; dins and mass add it with theirs.

The first migration is version 2, since hexkit reserves version 1 for an unversioned database.
Add, besides the definition, everything in the [table](#the-parts): the `migrations/` package, `DB_VERSION = 2`, `migrate_db()`, the `migrate-db` command and the version check in `cli.py`, the chart values, the `migrate-db` line in the README's list of commands, and `tests/.../test_db_version.py`.
Run `just charts` and `just service-docs` afterwards, since the chart and the README's parameter list are generated.

## Testing

A service's migrations have two kinds of test; in wps both are under `tests/migrations/`.

- **One test per version** (`test_v2.py`, `test_v3.py`): insert documents in the old shape with hexkit's `MongoDbFixture`, migrate to `n`, compare with the expected documents, and for a reversible migration migrate back to `n - 1` and compare with the originals.
  The test opens `MigrationManager` with the service's `MIGRATION_MAP` through a small local helper, as hexkit's own [migration tests](../../libs/hexkit/tests/integration/migrations/test_mongodb_migrations.py) do.
  Add a case with documents already in the new shape when the change function guards against them.
- **The version check** (`test_db_version.py`): every command except `migrate-db` refuses an empty database and runs once `migrate-db` has migrated it.
  The test reads the commands from the typer app, so a new command is covered without a change.

`just test services/<member>` runs both; they need Docker for the MongoDB test container.

## In the demo and the test bed

The demo and the test bed deploy the same charts, so their pods migrate in the init container as in production.

- **"We start on a clean slate"** empties every collection through the state management service except those ending in `DbVersions`, so the version records stay and the services keep passing the check.
- **`just testbed-reset`** stops the services, drops their databases with the version records, and starts them again, so each migrates from an empty database.
- **A database with documents but no version record** is treated as version 1, and the migrations run over documents that are already current.
  An idempotent change function passes them through; others fail and the init container crash-loops.
  `just testbed-reset` repairs it.

## Older documents

[Epic 62](../epics/epic-0062-california-condor/README.md) specified the framework before it was built, and the built one differs in the lock, the record fields, the temporary collection names and the version 1 reservation.
For the mechanism, read the hexkit page; for the conventions, this one.
