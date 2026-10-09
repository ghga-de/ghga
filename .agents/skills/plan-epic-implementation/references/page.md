# The plan page

How the page that the plan-epic-implementation skill publishes keeps its ticket cards, and the traps of building and publishing it.

## Ticket cards

Each story gets a ticket card: the title and description of its YouTrack ticket, which the owner edits and copies into YouTrack, and the ticket's key once it is filed.
The page renders the cards from its store, one document per story at `tickets/<story ref>`, so write no card into the HTML.

| Field | Holds | Written by |
|---|---|---|
| `title` | The story's pull request title without its `(<ISSUE>)` suffix, such as `[batch-dao] Add insert_many to the DAO`, in plain text, since YouTrack renders no Markdown in a summary | Claude, then the owner |
| `description` | Markdown: the story's goal, then `## Changes`, `## Acceptance criteria` and `## Depends on`, naming other stories by title | Claude, then the owner |
| `key` | The YouTrack key, matching `[A-Z]+-\d+`, or `null` | The owner on the card, or Claude from chat |
| `edited` | `true` once the owner has changed the title or the description | The page |
| `state` | `current`, `needs-changes` or `confirm-delete` | Claude; the page sets `current` when the owner edits a flagged description |
| `changed`, `changedIn` | The refs of the story's changed points, and the revision that changed them | Claude |
| `replacedBy` | The stories that replace a dropped one | Claude |
| `regenerate` | The busy state of a Regenerate request: `pending`, `sentAt` and `by` | The page, then Claude |
| `createdAt`, `updatedAt` | ISO timestamps | Both |

- **Self-contained text.**
  A ticket is read in YouTrack without the plan, so its text names no refs and links nowhere on the private page.
- **A card comes with its story**, on the first publish and in every refine that adds a story.
  Write new cards with an ArtifactData `batch` of `set` writes, with `key: null`, `edited: false`, `state: "current"`, `changed: []` and `replacedBy: []`.
- **Keys from chat.**
  When the user gives keys in chat, such as `S1 GSI-2349, S2 GSI-2351`, check each against `[A-Z]+-\d+`, write the valid ones with ArtifactData `update` pinned with `if_version`, and ask again for the rest.
  `all GSI-1234` names one ticket for the whole stack: write it to every card.
- **Delivery carries the keys.**
  P1's branch names and pull request titles take each story's key, as the [conventions](../../../../docs/conventions.md#names-branches-prs-commits) say; each refine fills in the keys added since the last revision.
- **How a refine changes the cards**, and how Regenerate works, is in [refine-loop.md](refine-loop.md#ticket-cards).

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
