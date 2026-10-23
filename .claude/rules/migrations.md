---
paths:
  - "services/**/migrations/**"
---

# Rules for service database migrations

A service's MongoDB migrations follow [db-migrations.md](../../docs/architecture/ac-0010-db-migrations.md); read it before adding or changing one.
hexkit's [MongoDB Migrations](../../libs/hexkit/user_guide/providers/mongodb_migrations.qmd) page explains the mechanism.

- **Copy the work package service**, `services/work-package-service`, for the layout, the CLI and the tests.
- **A new version needs four changes:** the definition, its `MIGRATION_MAP` entry and export, `DB_VERSION` in `main.py`, and a `test_v<n>.py`.
- **Migrations run only in `migrate-db`**, which the chart's init container calls; every other command checks the version first.
  Never call `MigrationManager` from an app entry point.
