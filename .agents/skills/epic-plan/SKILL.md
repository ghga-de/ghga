---
name: epic-plan
description: Turn an epic specification into a refinable implementation plan, a claude.ai artifact with one story per unit, comments on every point, a pick per decision and a Refine button. Private unless the user asks for public. Run as /epic-plan <epic> [public].
disable-model-invocation: true
compatibility: Claude Code with claude.ai artifacts (the Artifact, ArtifactComments and ArtifactData tools).
---

# Refinable epic plans

This skill turns an epic in `docs/epics/` into an implementation plan the dev refines on the page.
Every numbered point takes comments, every decision takes a pick, and a **Refine plan** button sends both back to this session.
The page scaffold with its styles and script is [assets/plan-template.html](assets/plan-template.html).
How to act on a refine request is in [references/refine-loop.md](references/refine-loop.md).

## Visibility

- **Private is the default.**
  A published artifact is private to its owner; publish it as it is when the user states no preference.
- **Public on request.**
  You cannot change sharing yourself, so:
  - Before publishing, check that the plan holds nothing confidential, as the epic template asks.
  - Declare no capability that blocks public sharing, such as `assets` or `mcp`; the template uses neither.
  - After publishing, tell the user to turn on link or organization access in the page's Share menu.
  - Tell them what visitors get: everyone reads the plan, and commenting and picking need Contributor access.
  - Advise sharing at Contributor level or below: only editors can send to Claude, so the owner then stays the only one who can wake the session.

## Steps

1. **Read** the epic, the root and area `AGENTS.md` files of every member it touches, and the code it names.
2. **Find what the epic leaves out.**
   Search for every implementer and consumer of what it changes: subclasses, protocols that extend it, factories, test fakes.
   Search for exact version pins on the member, such as `rg '"hexkit.*==' -g pyproject.toml`.
   Write each finding in two to four sentences: what the code does, why it matters, and what the plan does about it, with refs.
3. **Decisions** go in only where the epic leaves a real choice.
   For each option, state the concrete change and its cost for consumers, measured in the repo as the members and files it touches.
   Shade one option as recommended; the stories assume it until a pick says otherwise.
4. **Shared contract:** the rules every story follows, so the stories state only what differs.
5. **Stories:** one per unit the epic adds (a function, an endpoint, an event), plus groundwork first and the release last.
   Each story must pass `just lint` and its member's tests on its own, so implementers that a type change forces go into the same story.
   Give each story its dependencies and the decisions it touches, then numbered changes, acceptance criteria, tests by file, and docs.
   - Give no time or size estimates; the dependencies and the story order carry the planning.
   - Show the planned code for a change of 3 to 20 lines that handles something non-trivial, such as an error mapping or a partial-failure path.
     Describe trivial changes, and longer ones, in words.
6. **Delivery, risks and limits, out of scope.**
   Name pull requests, branches and commits by the [conventions](../../../docs/conventions.md#names-branches-prs-commits), and put a version bump in the last story.
7. **Build the page:** copy the template into the scratchpad and replace every `FILL` marker, keeping the styles and the script.
   Give every point a unique ref in `data-point` and a matching `id`.
8. **Publish** with the Artifact tool, icon `plan`, a one-sentence description and these capabilities:

   ```json
   {"comments": {}, "db": {"rules": [{"path": "preferences", "read": "view", "write": "owner"}, {"path": "preferences/{self}", "write": "interact"}, {"path": "comments", "read": "view", "write": "owner"}, {"path": "comments/{self}", "write": "interact"}, {"path": "status", "read": "view", "write": "owner"}]}, "user": {"scopes": ["profile"]}}
   ```

9. **Check once:** ArtifactComments `read`, and ArtifactData `list` on `preferences` and on `comments`, must all answer.
   ArtifactComments `watch` without a URL must show the artifact with auto-replies armed, or Refine cannot reach the session.
10. **Report** the link, the open decisions and the visibility in a few lines.

## Traps

- **Refs are permanent.**
  A page comment names its point by ref, so never renumber or reuse a ref when you republish.
  Give new points new refs, and remove a point only after its threads are resolved.
- **Decision rows are not list points.**
  The template's `.points > .pt` selector keeps the point grid off table rows; a bare `.pt` grid squeezes the option cell and cuts off the pick controls.
- **Comments live in the page's store.**
  A point's button opens a thread panel under the point, so every viewer sees each thread where it belongs.
  Each person's comments sit in their own document, `comments/<user id>`, which the access rules let only them and the owner write, so authorship cannot be forged.
  The claude.ai comment channel only notifies the session, through `sendToClaude` from the Refine button and "Comment and ask Claude"; leave its comment box and markers unused, since they detached or hid threads.
- **Only the owner's requests run.**
  Refine and "Comment and ask Claude" appear for the owner alone, and the session acts on a claude.ai trigger only when its attribution names the owner, as [references/refine-loop.md](references/refine-loop.md) says.
- **A question changes nothing but its thread.**
  Answer "Comment and ask Claude" in the page thread only, even when the answer proposes a change; the plan changes only on a refine request.
- **`sendToClaude` needs the full comments form.**
  Declare `comments: {}`; with `composer_only`, `canSendToClaude` answers `off`.
- **Capabilities on a republish:** omit `capabilities` to keep them, since a non-empty object replaces the whole set.
  A rule at the prefix of a `{self}` rule must set both `read` and `write`.
- **Refine reaches only a watching session.**
  In a new session, run ArtifactComments `watch` with the URL the user gives you to arm it again.
- **A local preview hides the controls**, since it has no `window.claude`; add the class `can-pick` to `<html>` to see the pick controls.
