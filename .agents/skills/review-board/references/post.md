# Posting the review

How the review-board skill posts a decided board to its pull request.

## Before posting

1. Read the statuses with ArtifactData `list` of `findings`; a finding without a document is open.
   With any finding open, post and resolve nothing, and say so in the thread.
2. Compare the head: `gh pr view <n> --json headRefOid`.
   If it moved since the board was built, check every anchor against the new head; if a line moved or changed, post nothing and ask the reviewer whether to rebuild the board.
3. Anchor only lines in the PR's diff, on the head's side, as `gh pr diff <n>` shows them.
   A reference outside the diff goes into the comment's body.

## The comments

| Status | Posted |
|---|---|
| Needs fix | An inline comment with the finding's body, and a suggestion where the fix has one |
| Up to dev | The same, opened with `q: Your call.` |
| Open | Nothing; it blocks the post |
| Fixed, Won't fix | Nothing; its `thread`, if it has one, is resolved after posting |

- A suggestion replaces exactly the anchored lines: its block holds the whole replacement from `start_line` to `line`, without `...` and without the snippet's header comment.
- Fixes in a few places close together share one suggestion over their range, unless another comment anchors inside it; then, and for places far apart, each place gets its own comment, the first with the repro.
  Two comments never anchor on overlapping lines.
- A fix in prose is a plain comment.
- The body is written as the reviewer would write it: GitHub prose, one line per paragraph ([line wrapping](../../../../docs/style.md#line-wrapping)), the observed output as a `text` block.
  A review takes no credit line for the agent ([conventions](../../../../docs/conventions.md#names-branches-prs-commits)).
- The summary names how many comments ask for a fix and how many leave the call to the author, not the board's link: the board is private to the reviewer.

## Posting

The review requests changes when any finding is marked Needs fix, and only comments when every posted finding is Up to dev.
A submitted review keeps its event, so choose it before posting.
GitHub refuses `REQUEST_CHANGES` on the reviewer's own pull request; post `COMMENT` there.

Write the review as JSON in the scratchpad and post it once:

```json
{
  "commit_id": "<head SHA>",
  "event": "REQUEST_CHANGES",
  "body": "<summary>",
  "comments": [
    {"path": "<path>", "start_line": 29, "start_side": "RIGHT", "line": 32, "side": "RIGHT", "body": "<body>"}
  ]
}
```

`gh api repos/ghga-de/ghga/pulls/<n>/reviews --method POST --input <file>` posts it; the permission rules ask before any `gh api` call, a second check.
A single-line comment leaves out `start_line` and `start_side`.

## Resolving threads

After posting, resolve the thread of every finding marked Fixed or Won't fix that has a `thread`.

1. Look up the PR's threads once:

   ```bash
   gh api graphql -F n=<n> -f query='query($n: Int!) { repository(owner: "ghga-de", name: "ghga") { pullRequest(number: $n) { reviewThreads(first: 100) { nodes { id isResolved comments(first: 1) { nodes { databaseId } } } } } } }'
   ```

   A thread belongs to the finding whose `thread` equals its `comments.nodes[0].databaseId`.
2. Skip a thread already resolved, and name a `thread` that matches none in the reply.
3. Resolve each other thread by its `id`:

   ```bash
   gh api graphql -f id=<thread id> -f query='mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }'
   ```

A board with nothing to post but threads to resolve posts no review and resolves only the threads; the button allows that, since closing the fixed threads is all that round asks of the reviewer.
A dry run resolves nothing and lists the threads it would resolve.

## After posting

- Set `review/post` with ArtifactData to `{status: "posted", url, postedAt, resolved}`, where `url` is the review's `html_url` and `resolved` the number of threads resolved: the board shows both and disables its button.
  Without a review, leave out `url`.
- When the post fails, set `{status: "failed", reason}` instead: the board shows the reason and offers the button again.
- Reply in the claude.ai thread with the link or the reason and the number of threads resolved, and resolve the claude.ai thread.
