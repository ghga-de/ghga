# The board page

Every board is [assets/board-template.html](../assets/board-template.html) with one JSON block filled in.
Its layout and script are the same for every board, so a fix to the page is a change to the template, made once.

## Filling it

1. Copy the template into the session's scratchpad as `review-board-<n>.html`.
2. Replace `PR_NUMBER` in `<title>` with the PR's number, and `BOARD_DATA` with the JSON below, every `</` in it written as `<\/`.
3. Open the file once in a local browser: the findings, their statuses and a comment preview show, and the console has no errors.
4. Publish it privately with `capabilities: {db: {}, comments: {}, user: {}}`, the icon `checklist` and a one-sentence description.

Later findings go into the JSON, and the page is republished to the same artifact: the same file path in the session that published it, or the board's `url` from another session.
A publish without `url` from a new session makes a second board.
The statuses survive in the store.

## The data block

| Field | Holds |
|---|---|
| `pr` | `number`, `title`, `url`, `head` (the reviewed commit) and `base` |
| `date` | The review's date |
| `dryRun` | `true` only for a test board: its button asks for a draft, never a post |
| `summary` | The first sentence of the review's summary |
| `footer` | Lines under the board, such as where the probe scripts are |
| `bands` | `id`, `title` and `gloss` per band, worst first |
| `findings` | Per finding the fields in [SKILL.md](../SKILL.md#write-each-finding); `code` takes `codeLang` (default `python`), `fix` is `{text, patches: [{lang, code}]}`, and `post` a list of `{path, line, start_line, body, suggestion}` |

`what`, `verdict`, `fix.text` and the `footer` lines are HTML with `<code>` and `<em>` only.
Code, output, comment bodies and suggestions are plain text, which the page escapes.

## What the template does

- Statuses live in the store's `findings` collection, one document per finding at `findings/f<id>`, holding `{status, updatedAt}`; seed known ones with ArtifactData after publishing, never in the page.
- Under each finding marked Needs fix or Up to dev, **Show the comments to post** shows each comment's anchor and exact text, as [post.md](post.md) builds them, and the panel shows the review's summary.
- The **Post review** button works for the owner alone, as in `define-tasks`, and only when no finding is open and at least one is to be posted.
  A press sends a claude.ai thread starting "Post the review of #<n>" (or "Dry run:" on a test board) and sets `review/post` to `{status: "requested", requestedAt}`; the session sets it to `posted` with the review's `url`, or `failed` with a `reason`, and a request without an answer frees after 30 minutes.
- Next to the button the page says why it is disabled; a line with each check's result (store, owner, sending to Claude) appears only when one fails, and a permissions button only when a capability is denied.
- Without the store, statuses stay in the viewer's browser, and the page says so.

## Changing the template

Test a change locally (statuses, previews, no console errors) and on one board in claude.ai before it merges.
A local preview lacks the reset that claude.ai's page skeleton adds, so the template carries its `[hidden]` rule: without it, the filter leaves every finding on screen.
A script error after the first draw leaves the findings on screen but stops the store and the button without a message.
