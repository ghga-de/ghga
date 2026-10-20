# The plan page

How the page that the define-tasks skill publishes names its points and keeps its ticket cards, what sharing it exposes, and the traps of building and publishing it.

## Refs

Every plan uses the same refs, so a ref names the same kind of point in every plan.
Use no other prefix, and number each one from 1 in page order on the first publish; groundwork is the one exception, as `T0`.

| Section | Ref | Example |
|---|---|---|
| Findings, only for a findings artifact | `F` | `F1` |
| Gaps in the source | `G` | `G1` |
| Decisions, and their options | `D`, then a letter per option | `D1`, `D1.A` |
| Shared contract | `C` | `C1` |
| Tasks | `T`, from `T0` when the plan has groundwork | `T1` |
| A task's points | the task, then a number running across its changes, criteria, tests and docs | `T1.3` |
| Delivery, and after the merge | `P`, a number running across both lists | `P1` |
| Risks and limits | `R` | `R1` |
| Not in this plan | `X` | `X1` |

The `id` of a point is its ref in lower case with dashes for dots, such as `t1-3`.

## Ticket cards

Each task gets a ticket card: the title and description of its YouTrack ticket, which the owner edits and copies into YouTrack, and the ticket's key once it is filed.
The page renders the cards from its store, one document per task at `tickets/<task ref>`, so write no card into the HTML.

| Field | Holds | Written by |
|---|---|---|
| `title` | The task's pull request title without its `(<ISSUE>)` suffix, such as `[batch-dao] Add insert_many to the DAO`, in plain text, since YouTrack renders no Markdown in a summary | Claude, then the owner |
| `description` | Markdown: the task's goal, then `## Changes`, `## Acceptance criteria` and `## Depends on`, naming other tasks by title | Claude, then the owner |
| `key` | The YouTrack key, matching `[A-Z]+-\d+`, or `null` | The owner on the card, or Claude from chat |
| `edited` | `true` once the owner has changed the title or the description | The page |
| `state` | `current`, `needs-changes` or `confirm-delete` | Claude; the page sets `current` when the owner edits a flagged description |
| `changed`, `changedIn` | The refs of the task's changed points, and the revision that changed them | Claude |
| `replacedBy` | The tasks that replace a dropped one | Claude |
| `regenerate` | The busy state of a Regenerate request: `pending`, `sentAt` and `by` | The page, then Claude |
| `createdAt`, `updatedAt` | ISO timestamps | Both |

- **Self-contained text.**
  A ticket is read in YouTrack without the plan, so its text names no refs and links nowhere on the private page.
  The same holds for a findings artifact: restate what a finding says in place of its ID or a link to it.
- **A card comes with its task**, on the first publish and in every refine that adds a task.
  Write new cards with an ArtifactData `batch` of `set` writes, with `key: null`, `edited: false`, `state: "current"`, `changed: []` and `replacedBy: []`.
- **Keys from chat.**
  When the user gives keys in chat, such as `T1 GSI-2349, T2 GSI-2351`, check each against `[A-Z]+-\d+`, write the valid ones with ArtifactData `update` pinned with `if_version`, and ask again for the rest.
  `all GSI-1234` names one ticket for the whole stack: write it to every card.
- **Delivery carries the keys.**
  P1's branch names and pull request titles take each task's key, as the [conventions](../../../../docs/conventions.md#names-branches-prs-commits) say; each refine fills in the keys added since the last revision.
- **How a refine changes the cards**, and how Regenerate works, is in [refine-loop.md](refine-loop.md#ticket-cards).

## Sharing

If the user asks about sharing the plan, name what it exposes before they decide:

- Everyone they share it with reads the plan and its ticket cards, and with Contributor access also comments and picks.
- A plan from a findings artifact repeats its findings, also for people who cannot open that artifact.
- A refine reads those comments into this session, which has the repository and its tools; the session treats them as data, but they remain text from other people.
- Editors can send to Claude, and every comment sent to Claude starts this session's automatic reply before any check of the sender.

## Traps

- **Decision rows are not list points.**
  The template's `.points > .pt` selector keeps the point grid off table rows; a bare `.pt` grid squeezes the option cell and cuts off the pick controls.
- **Comments live in the page's store.**
  A point's button opens a thread panel under the point, so every viewer sees each thread where it belongs.
  Each person's comments sit in their own document, `comments/<user id>`, which the access rules let only them and the owner write, so authorship cannot be forged.
  The claude.ai comment channel only notifies the session, through `sendToClaude` from the Refine button and "Comment and ask Claude"; leave its comment box and markers unused, since they detach or hide threads.
- **`sendToClaude` needs the full comments form.**
  Declare `comments: {}`; with `composer_only`, `canSendToClaude` answers `off`.
- **Capabilities on a republish:** omit `capabilities` to keep them, since a non-empty object replaces the whole set.
  A rule at the prefix of a `{self}` rule must set both `read` and `write`.
  A plan published before ticket cards lacks the `tickets` rule: republish it once with the full capabilities from the skill's publish step, then create its cards.
- **A local preview hides the controls and the ticket cards**, since it has no `window.claude`; add the class `can-pick` to `<html>` to see the pick controls.
