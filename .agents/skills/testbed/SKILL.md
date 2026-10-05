---
name: testbed
description: Write or change a test-bed feature, or find why a test-bed run failed, timed out or still shows the old behaviour. Use for features and steps under testbed/ and for any failure of just testbed.
paths:
  - "testbed/**"
---

# Test bed

How to set it up and run it is in the root README's [test-bed walkthrough](../../../README.md#run-the-test-bed-locally), and its layout in [testbed/README.md](../../../testbed/README.md).
This skill gives the order of the work and the symptoms of what still goes wrong.

## Does the test belong here?

Only when its outcome depends on backend state changing across services ([testbed/AGENTS.md](../../../testbed/AGENTS.md#what-belongs-here)).
What one portal page renders belongs in the data portal's Playwright tests in `frontend/data-portal/tests`, against the MSW mocks.
One service's own logic, DAO or API belongs in that member's tests, run with `just test services/<member>`.

## Writing a feature

1. Choose the number first.
   Pytest runs `steps/test_NNN_*.py` in name order, and a feature takes the states earlier ones hand on (`set the state to`, `we have the state`).
   The hundreds group the flows: 0xx metadata, 1xx users, 2xx upload, 3xx browse, 4xx access and download, 5xx portal, 6xx deletion, 7xx dead letters.
   A feature that revokes, deletes or changes something runs after every feature that still needs it: grep the later features for the states and data yours touches.
2. Write `features/NNN_name.feature` and `steps/test_NNN_name.py`, same number, same name; the module binds the file with `scenarios("../features/NNN_name.feature")`.
   Copy the shape of a neighbour in the same hundred.
3. Reuse steps before writing new ones: grep the step text in `steps/conftest.py`, `conftest_1x.py`, `conftest_2x.py` and `conftest_5x.py`, and take the fixtures from `fixtures/`.
4. Wait for backend state by polling with a deadline, never with `time.sleep`: events, projections and the DHFS poll run on their own schedule.
   Use `fixtures.mongo.wait_for_document`, `wait_for_documents` or `wait_for_removal`, `has_reached` for upload states, and `expect(...)` with `UI_TIMEOUT` in the browser.
5. Tag the feature with a marker from `markers` in `testbed/pytest.ini`, which `just testbed -m` selects; register a new one there.
   A browser scenario also gets `@frontend`, which arms the tracing.
6. Local and CI runs are black-box (`black_box_mode` in `tb.kind.yaml`): reach MongoDB, Kafka and S3 through the fixtures, which go through the state-management service, and expect internal APIs to answer 404.

## Debugging a failed run

Read the first failure: the features after it fail on states it never set.

1. **"not every deployment is available"** at the start: `just logs` lists the deployments, `just logs <service>` follows one.
   A `MigrationStepError` there after a restart is no code bug: the suite's clean slate removes the migration records, so a restarted service re-runs its migrations over migrated data.
   Run `just testbed-reset`, and do not touch the migration.
   It is a code bug when the branch changed that migration, or when the service still fails after the reset, which runs every migration over empty databases.
   `just testbed-up` on such a cluster waits its 15 minutes for the same pods and fails, so reset first.
2. **A step timed out waiting for a state:** the wait names the service that owns the state.
   Run `just logs` for it and for the services before it in the flow; uploads pass the connector, UCS, DHFS, FIS and EKSS, downloads WPS, WKVS and DCS, metadata DSKit, metldata and MASS.
   Fix the cause, and never raise the timeout: the upload waits already allow 60 s against the 2 s DHFS poll.
   To check the fix, rebuild the image, recreate the pods (3), rerun from the start (4), and watch `just logs <service>` for the error to go.
3. **The old behaviour after a rebuild:** images are tagged `:local` with `IfNotPresent`, so `just testbed-up` loads them but restarts no pod.
   `just testbed-reset` recreates the pods.
4. **"The expected state … has not yet been set":** the feature ran without the ones before it.
   `just testbed-reset` drops every database, the states included, so after it run the suite from the start, or every feature from 010 up to yours, never one feature alone.
5. **A locator timeout in a browser step:** record a trace before you touch a selector, `TB_TRACE=1` for the failed tests or `TB_TRACE=all` when the failing test's own trace looks innocent, since the browser session is shared and an earlier test may be the cause.
   `just testbed-trace <name>` serves it on port 9323.
   For a fault in what the portal renders, `playwright-cli` on the live portal is cheaper than reading a trace, but it cannot see the run's browser session; setup in [references/playwright-cli.md](references/playwright-cli.md).
6. **Feature 110 fails while `just fe-dev` runs:** the dev server holds port 8080, so the lox24 port-forward fails without a message; stop the dev server.
7. **EKSS-backed steps fail after Vault restarted:** dev-mode Vault forgets the secrets EKSS stored, so a scoped run of a later feature such as 420 fails; run from 010.

When a reset does not help, start over with `just down` and `just testbed-up mono`.
Only one worktree runs the test bed at a time, since all share one kind cluster.
