# Agent Instructions for `deploy/`

How we work on the Helm charts and the generator that writes them. The repo-wide rules are
in the root [AGENTS.md](../AGENTS.md), and
[docs/agent-instructions.md](../docs/agent-instructions.md) says what belongs in which
file.

## Where to read

[README.md](README.md) is required reading: it is how the chart system works.

## Generated charts

`deploy/charts/<service>/` charts are **generated**, never edit them by hand; change the
generator (`src/`) or the member's `chart-values.yaml` and run `just charts`.
`ghga-common`, `ghga-demo` and `aai` are hand-maintained.

## Chart tests

`just charts-test` and `just demo-template` are render-level checks that the chart library
and the umbrella produce valid manifests. Run them for any change here — the member unit
tests do not cover rendering.
