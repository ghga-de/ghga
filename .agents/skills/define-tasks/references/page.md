# The plan page

How the page that the define-tasks skill publishes names its points, keeps its ticket cards and its store, what sharing it exposes, and the traps of building and publishing it.

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

## Gists

Every ref the page shows links to its point and shows the point's gist on hover: in the "What changed" block, and in the text, tags and question lines of every other point.
The page's how-to line tells readers so.

- **Give every point a `data-gist`**, except a task or decision head, whose heading serves as its gist.
  Write what the point does or says in up to ten words, without paths, file names or refs, such as `data-gist="Each transport builds its own budget"`.
  Write a double quote in it as `&quot;`, since a bare one ends the attribute.
- **Keep the gist with the point.**
  Give every new point one in the refine that adds it, and change a gist only when its point's meaning changes.
- **Write refs as plain text** in the text and tags, and the script links them.
  A ref inside `code`, a link or an SVG stays text, and so does a point's mention of itself.
  Write a source's own IDs and words that only look like refs, such as Cloudflare's R2, in `code`, or the page links them to the plan's point of that name.

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

## Store layout

The page keeps its comments, picks, ticket cards and busy states in the artifact's store, under these access rules: everyone admitted reads, each person writes their own area and their own `people` entry, and only the owner writes the rest.

| Document | Holds | Written by |
|---|---|---|
| `data/users/<id>/c-<comment id>` | One comment: `point`, `text`, `thread` (null on a first comment, else that comment's id), `createdAt`; `resolved` on a first comment; `askedClaude` on a question | Its author, and the owner |
| | `byClaude` on Claude's replies, which sit in the owner's area only; `adoptedFrom` with `author` and `comment` on a copy the owner adopted; `applied`, the revision a refine applied it in | The owner, and Claude |
| | `removed`, `removedBy` and `removedAt` on a removed first comment whose replies keep it, with its text emptied | The owner |
| `data/users/<id>/picks` | The person's pick per decision, such as `"D1": "A"` | Its person; Claude for the owner |
| `people/<id>` | That the person has an area, so the page reads it | Its person, and the owner on a first visit |
| `tickets/<task ref>` | A ticket card, as [Ticket cards](#ticket-cards) lists | The owner, and Claude |
| `status/refine`, `status/page` | Refine's busy state, and the version Claude last published | The owner's page, and Claude |
| `status/owner` | The owner's id, so every viewer knows which area is the owner's | The owner's page, on a first visit |

- **Only the owner talks to Claude.**
  The page honours `byClaude` and `askedClaude` only in the owner's area, which only the owner and Claude write.
  Claude's replies there read "Claude" for every viewer; the same flags in anyone else's area are ignored, so those comments read as their author's.
- **Everyone sees the owner's picks**, since those are the ones a refine applies: Contributors and Viewers get an "Owner's pick" tag on the picked row and a line under the table.
  Contributors also pick for themselves; Viewers get no pick controls.
  The owner sees everyone else's picks, by name, under each table.
- **The owner adopts comments on the page.**
  Adopt copies a teammate's comment into the owner's area as a first comment on the same point; adopting a reply offers the first comment it answers too, and puts the reply under that copy.
  The page hides the copy and tags the original instead, and shows replies to the copy, such as Claude's answer, in the original's thread; `adoptedFrom` counts only in the owner's area.
  It shows the copy only when the original is gone or its text has changed since, so the page always holds the text a refine applies.
  Undo adoption, on the original, deletes the copy.
- **A refine reads `data/users/me`**, which the store resolves to the session's user, the owner: the owner's comments, the comments the owner adopted, Claude's replies and the owner's picks.
  The plan guard refuses every other area, so a teammate's comment reaches a refine only when the owner adopts it.
- **The owner removes comments on the page.**
  A reply, or a first comment without replies, is deleted; a first comment with replies keeps its document without text, as a "Comment removed" line, until its last reply goes.
- **Each comment is its own document**, so the 256 KiB limit applies per comment; the store holds at most 25,000 documents in all.

## Moving a plan to this layout

A plan published before this layout keeps each person's comments in `comments/<id>` under `items`, and their picks in `preferences/<id>`.
Move it once, before sharing it, in a session the user starts with `GHGA_PLAN_GUARD=off`, so the guard lets the session publish with capabilities:

1. **Save the old documents to files:** ArtifactData `list` on `comments` and on `preferences`, each with an `out_dir` in the scratchpad, so the comment text goes to files and stays out of the session.
2. **Reshape them:** run `python3 .agents/skills/define-tasks/scripts/migrate_store.py <out_dir> <new_dir>`.
   It writes one file per new document, and `batches.json`: the ArtifactData batches that write them and delete the old documents, naming files, not text.
3. **Send the batches** with ArtifactData `batch`, one entry of `batches.json` at a time.
4. **Bring the page up to date:** replace its `<style>` and `<script>` blocks with the current template's, add the `data-define-tasks-plan` attribute to its `.page` element, and publish it with the full capabilities from the skill's publish step.

Then end the session; the next one works on the plan under the guard.

## Sharing

If the user asks about sharing the plan, answer from [the sharing note](sharing-note.md): Contributor, added by name, is the one level to use.
Before they decide, name what sharing exposes:

- Everyone they share it with reads the plan, its ticket cards, every comment and every pick.
- A plan from a findings artifact repeats its findings, also for people who cannot open that artifact.
- Only the owner's area reaches a refine; a teammate's comment reaches it only when the owner adopts it, and then as the owner's own text.
- Editors can send to Claude, and can publish new page versions, which run as the owner in the owner's browser; that is why the sharing note rules Editor out.

## Traps

- **Decision rows are not list points.**
  The template's `.points > .pt` selector keeps the point grid off table rows; a bare `.pt` grid squeezes the option cell and cuts off the pick controls.
- **Comments live in the page's store.**
  A point's button opens a thread panel under the point, so every viewer sees each thread where it belongs.
  Each comment sits in its author's area, as [Store layout](#store-layout) lists, which the access rules let only them and the owner write, so authorship cannot be forged.
  The claude.ai comment channel only notifies the session, through `sendToClaude` from the Refine button and "Comment and ask Claude"; leave its comment box and markers unused, since they detach or hide threads.
- **Keep the `data-define-tasks-plan` attribute and the template's script.**
  The plan guard recognises a plan by the attribute, and refuses a publish whose script differs from every committed version of the template.
- **`sendToClaude` needs the full comments form.**
  Declare `comments: {}`; with `composer_only`, `canSendToClaude` answers `off`.
- **Capabilities on a republish:** omit `capabilities` to keep them, since a non-empty object replaces the whole set.
  A rule at the prefix of a `{self}` rule must set both `read` and `write`.
  A plan published before the per-comment layout lacks its rules; move it as [Moving a plan to this layout](#moving-a-plan-to-this-layout) says, then create any missing ticket cards.
- **A local preview hides the controls and the ticket cards**, since it has no `window.claude`; add the class `can-pick` to `<html>` to see the pick controls.
- **The page's own writes show before the server confirms them**, and that pending view can hold only the fields just written.
  The script merges it over the document's last confirmed body in `settledBody`; read every store document through it, or a reply hides its thread until the server confirms.
