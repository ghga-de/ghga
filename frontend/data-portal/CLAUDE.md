# Claude Code Instructions

Read the [Agent Instructions](AGENTS.md) first as the AI-specific entrypoint, and keep shared AI-specific rules there. Project guidance in [README](README.md) and relevant files in [docs](docs/) is also authoritative for both human developers and agents. This file is intentionally small.

When making changes:

- Prefer minimal diffs
- Explain non-obvious refactors
- Run tests before suggesting changes

## MCP configuration

Claude Code and Copilot read different MCP config files, so the repo carries both:

- `.mcp.json` (key `mcpServers`) is Claude Code's config; `.vscode/mcp.json` (key `servers`) is Copilot's. They are kept separate on purpose — do not try to reconcile them into one.
- `.mcp.json` lists only `angular-cli`. `context7` is omitted there because Claude Code already has Context7 via the claude.ai-hosted connector, so the npx server would be redundant. (Copilot has no such connector, so `.vscode/mcp.json` lists both.)
- See [AGENTS.md](AGENTS.md) for how to use the `angular-cli` and `context7` MCP servers.
