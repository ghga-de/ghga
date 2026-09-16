# Agent Instructions for `testbed/`

How we work on the integration test bed. The repo-wide rules are in the root
[AGENTS.md](../AGENTS.md), what it is and how to run it in its [README](README.md) and the
root README's [walkthrough](../README.md#run-the-test-bed-locally), and
[docs/agent-instructions.md](../docs/agent-instructions.md) says what belongs in which
file.

## Not a workspace member

The test bed is **not** a uv workspace member: it runs from its own `.venv-testbed`
(`just testbed-install`) while shelling out to the workspace-built `ghga-connector` and
`ghga-datasteward-kit`.

## What belongs here

`just testbed` runs pytest-bdd feature files and Playwright against the full platform on
kind. It is the only level that can verify a cross-service flow end to end — events
consumed, projections updated, files actually served — so a test whose outcome depends on
backend state changing belongs here rather than in a member suite or in the data portal's
Playwright tests. Setup, scoping and resets are in the root README's
[walkthrough](../README.md#run-the-test-bed-locally).

## Generated artifacts

The artifact model overlay (`values-artifacts.yaml`) is derived by `just testbed-artifacts`
and not committed.
