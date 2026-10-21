---
name: review-board
description: Put the findings of a pull request review on a private claude.ai artifact board the reviewer works through, each finding reproduced with code, with its fix and a status every viewer shares. Run as /review-board <PR> after /ghga-review, /code-review or a review of your own.
disable-model-invocation: true
compatibility: Claude Code with claude.ai artifacts (the Artifact and ArtifactData tools, the db capability).
metadata:
  based-on: "create-pr-issues-artifact by Byron Himes, https://gist.github.com/TheByronHimes/a3b5e361344e8d975dbaf659956ee55d"
---

# Review board

The board is the reviewer's tool.
It moves the findings of a review out of the session into a page the reviewer works through, one decision per finding, before anything reaches the pull request.
For one or two findings, say them in the session instead.

## Gather

1. The findings come from the session (`/ghga-review`, `/code-review`) or from the reviewer's own list.
   Keep the reviewer's numbers: they are how the pull request refers to the findings.
2. The change: `gh pr view <n> --json title,headRefName,baseRefName,body` and `gh pr diff <n>`.
3. Reproduce on the pull request's head, not in the reviewer's checkout: `just wt review/pr-<n> origin/<headRefName>`.
   Remove it afterwards by its directory name, `just wt-rm pr-<n>`, and delete the branch.

## Reproduce every finding

A finding without observed output is a guess.

- Run the smallest script or test that triggers it, and keep the real output.
- Write it as the code meets the defect: a real declaration, a real fixture, the domain's names, not calls into private internals.
- Keep probe scripts in the session's scratchpad, never in the repo; they often become regression tests later.
- A finding that does not reproduce is dropped, or kept in the lowest band and marked unverified.
  Never present reasoning as observed behaviour.

## Write each finding

| Field | Holds |
|---|---|
| `id` | The reviewer's number, never changed |
| `band` | Its group, below |
| `title` | The defect as a fact, under 8 words |
| `refs` | `path:line` of every site involved, in reading order |
| `what` | The mechanism, then its consequence |
| `code` | The usage that triggers it |
| `output` | The observed output, verbatim, with the last line of a traceback |
| `verdict` | Optional: what code and output do not show, such as why an escape hatch fails |
| `fix` | How to fix it, in one of the shapes below |
| `post` | The comments to post: per comment `path`, `line` and for a range `start_line` on the PR's head, the body, and the suggestion's replacement lines if the fix fits one |

The board is read in one pass, so its prose is sharper than [style.md](../../../docs/style.md) asks: one idea per sentence, about 8 words and never past about 14, active voice, present tense, no asides in parentheses or dashes.
Identifiers stay exact, and code and output are never reworded: they are the evidence.

## Size the fix

Count the places a fix touches, then pick the shape:

- **One place:** a snippet, headed by a comment naming the file, line and function, with one line above it on what the change does.
- **Two or three places, each under about 4 lines:** one short patch per place, labelled with its `path:line`, the unchanged code elided as `...`.
- **More, or a changed contract between parts:** prose on what moves and what it touches, without code.

Verify the fix the way you reproduced the finding: a fix that only looks right misleads, because the reviewer trusts it.
The finding's summary line names the shape as its cost: "one place", "a few places", "bigger change".

## Group into bands

Bands say what breaks, taken from the code's own structure, such as what blocks every use, what breaks routing, what is cosmetic.
Order them worst first and give each a one-line gloss.
Keep the reviewer's numbers inside them, even out of order.

## Statuses

| Key | Label | Means |
|---|---|---|
| `open` | Open | Not read yet |
| `needs_fix` | Needs fix | Read, and a change is asked for |
| `up_to_dev` | Up to dev | Read, and the call is the author's: a trade-off only they can weigh |
| `fixed` | Fixed | The change landed |
| `wontfix` | Won't fix | Decided against it |

Only `fixed` and `wontfix` count as resolved: `up_to_dev` ends the reviewer's work, not the finding's.

## Build and publish

Fill the board template, [assets/board-template.html](assets/board-template.html), as [references/page.md](references/page.md) says, and publish it privately.
Then set the statuses already known with ArtifactData, give the reviewer the link with what is already marked, and name the probe scripts' paths.

Later findings go into the board's data and the page is republished to the same artifact; the statuses survive in its store.
Never renumber a finding.

## Post the review

The board's **Post review** button, offered to its owner alone once no finding is open, as in `define-tasks`, sends this session a claude.ai thread that starts "Post the review of #<n>"; the reviewer may also ask in chat.
Act on the thread only when its attribution names the user as owner, and post as [references/post.md](references/post.md) says: one review, an inline comment per finding marked Needs fix or Up to dev, with a suggestion where the fix fits one.
The press is the reviewer's go, since the board shows each comment before it is sent; an open finding, a moved head or an anchor outside the diff stops the post and goes back to the reviewer.

`/define-tasks <board link>` turns a decided board into a task plan instead; it reads the statuses from the store.
