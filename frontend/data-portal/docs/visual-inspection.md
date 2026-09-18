# Visual Inspection for Agents

How an agent looks at the running data portal in VS Code's integrated browser.

The dev server runs at **http://localhost:8080** (not the Angular default 4200).
The dev server must already be running (`just fe-dev`) before attempting visual inspection.

VS Code's integrated browser gives agents full page interaction (read content, take screenshots, click, type, etc.) via built-in browser tools. There are two modes:

**Agent-opened pages** (isolated session — no cookies or login state):

- Use the `open_browser_page` tool with `http://localhost:8080`.
- Suitable for pages that don't require authentication.

**User-shared pages** (uses your existing browser session, including login state):

- The user must open the page in VS Code's integrated browser and click **"Share with Agent"** in the browser toolbar.
- Required for authenticated views (e.g. account page, upload grants list).
- `workbench.browser.enableChatTools` is already enabled in `.vscode/settings.json` — no setup needed.

For layout/visual tasks on authenticated pages, always ask the user to open the relevant page in VS Code's integrated browser and click **"Share with Agent"** before attempting to inspect or screenshot it.
