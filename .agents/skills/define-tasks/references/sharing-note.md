---
name: sharing-define-tasks-plans
description: How to share a define-tasks plan page — Contributor, by name, is the one level; never Editor, Owner, a channel, a public link or organization-wide access
metadata:
  type: reference
---

# Sharing define-tasks plans

Share a define-tasks plan page by name, at Contributor, with the people who should comment on it.
The define-tasks skill copies this note into memory word for word from `.agents/skills/define-tasks/references/sharing-note.md`, so a session can answer sharing questions without the skill.

## Sharing a plan

- **Recommended: Contributor, added by name, as the one level to use.**
  Contributors comment and pick on the page, which is what sharing a plan is for.
  The risks that come with Contributor:
  - Everyone you add can read the whole plan: every comment, Claude's replies, everyone's picks and the ticket cards.
    A plan built from review or triage findings repeats those findings, so don't add anyone who shouldn't see them, for example while a security issue is still unfixed.
  - A comment reaches Claude only when you adopt it, and then arrives as your own request.
    Read it before you adopt it, since pasted text can carry instructions.
  - A Contributor can fill the page's store up to its cap of 25,000 documents; new comments and ticket cards then fail until you delete documents.
  - Everyone with access sees the names of the people who comment.
- **Strongly discouraged: every level above Contributor.**
  - **Editor** can publish a new page version, which runs in your browser as you and sends to Claude under your name, and can send comments straight to your Claude session.
    No skill change prevents either.
  - **Owner, granted in the share menu,** has the same rights as Editor, so the same risks.
    It does not make them the plan's owner.
  - **A channel or project granted Editor or Owner** gives those rights to everyone who can post there.
- **Also avoid a public link and organization-wide access.**
  You no longer choose who joins: a link admits every member of your organization as a Contributor, and signed-in outsiders read every comment and pick.
