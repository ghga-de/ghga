# ADR-0022 — Naming branches, pull requests and commits

- **Status:** Accepted
- **Date:** 2026-09-14

## Context

[ADR-0020](0020-branching-strategy.md) settled which branch work is cut from and merged into,
but not what any of it is called. A change carries three names — its branch, its pull request
and the commit that lands on `dev` — and nothing ties them to one another. Left to taste, each
drifts on its own axis: what the prefix names, which case the slug takes, where the issue key
sits, whether the component is named and how it is abbreviated. The cost is not aesthetic. The
branch list, the pull request list and `git log` are the three places work is found, and each
is only as scannable as its least consistent entry — which makes naming one of the conventions
that has to be decided once rather than converged on, because the drift is invisible to the
person creating each name and only shows up to whoever reads the list.

Two further forces make this worth settling here rather than leaving to habit.

**Large work arrives in stacks.** A stack is a chain of pull requests, each based on the
previous one and rooted at `dev`, so that a big change stays reviewable in pieces; a chain can
run to a dozen or more. GitHub supports the stacking itself — a pull request can target
another's branch, and the chain is visible from any one of them — but that support still sits
close to the git underneath it: the chain is read off the branches rather than the stack being
an object in its own right. A stack therefore has no name yet, and the pull request list cannot
yet be grouped or sorted by one, so in the view where work is triaged its entries scatter and
whatever holds them together has to be carried in their names. The name is the only thing
missing: a pull request's position in its chain is already shown, and it shifts every time the
bottom of the stack merges, so it is the one part of a stack that must not be written into a
name. Without a naming rule the gap gets patched per stack — a shared prefix on the branches, a
phrase repeated across the titles — which holds exactly as long as everyone writing an entry
words it the same way. Both gaps look like ones GitHub will close rather than settled facts,
which makes the rule below a workaround with an expiry rather than a permanent fixture. Until
then the name belongs in the branch name and the pull request title, because there is nowhere
else to put it.

**Squash merge makes the pull request the commit.** With one commit per pull request, the title
and description written for review become the permanent record in `git log` — read more often,
and by more tools, than the pull request list ever is. A convention for pull request titles is
therefore a convention for the history, whether or not anyone writes it down as one.

## Decision

> In the context of a monorepo where large work arrives as stacks of pull requests, facing
> a GitHub that stacks pull requests but does not yet name them or let the list be grouped by
> them, and a squash-merge history whose quality is whatever
> the pull request titles happened to be, we decided to derive all three names — branch, pull
> request and commit — from one grammar of kind, stack and description, and to write the
> commits as Conventional Commits, to achieve a legible history and stacks that hold together
> in the pull request list, accepting that every merge rewrites its commit message.

This ADR governs the artifacts of the development process. Naming of code and infrastructure
objects — collections, topics, enums — is a separate matter and stays where it is
(`adr-old/adr010`).

### Kinds

One vocabulary for branches and commits, taken from
[Conventional Commits](https://www.conventionalcommits.org/) wherever the two overlap:

| kind | for | commit type |
|---|---|---|
| `feat` | new functionality | `feat` |
| `fix` | bug fix on unreleased work | `fix` |
| `hotfix` | fix against the latest release | `fix` |
| `docs` | documentation, ADRs, READMEs | `docs` |
| `refactor` | behaviour-preserving restructuring | `refactor` |
| `test` | test bed, test tooling, test-only changes | `test` |
| `chore` | tooling, CI, dependencies, charts — and anything not clearly one of the above | `chore` |

`hotfix` is the only kind that is not also a commit type, because the two answer different
questions. A branch kind says where the work lives — what it was cut from and what it merges
back into — and `hotfix` is the only one whose answer is `main` rather than `dev`
([ADR-0020](0020-branching-strategy.md)), which is what someone scanning a branch list needs
without opening anything. A commit type says what kind of change it is, and by that measure a
hotfix is a fix: Conventional Commits has no type for one, urgency is not a category of change,
and the same fix is back-merged into `dev`, where a `hotfix` type would classify nothing.
Nothing is lost either way — a fix released as a hotfix sits on `main` ahead of a release tag
rather than arriving through a `dev` merge, so the history still says so.

There is deliberately no `release` kind: a release is a merge plus a tag.

The list is short on purpose — anything not clearly one of the others is `chore`. We do not use
Conventional Commits' `perf`, `ci`, `build` or `style`.

### Branch names

```text
<stack>/<kind>/<description>     in a stack
<kind>/<description>             solo
```

Lowercase kebab-case throughout, the YouTrack key excepted — it keeps its upper-case spelling.
Keep the description short and the stack name shorter, ideally one or two words. The stack name
names the stack, not the member the work touches.

A YouTrack key goes in front of the part it belongs to: in front of the description when the
issue covers the individual pull request, in front of the stack name when it covers the stack
as a whole.

| | branch |
|---|---|
| solo | `feat/add-ucs-endpoints` |
| solo, with an issue | `feat/GSI-1234-add-ucs-endpoints` |
| in a stack | `upload/feat/add-ucs-endpoints` |
| in a stack, own issue | `upload/feat/GSI-1234-add-ucs-endpoints` |
| in a stack, issue covers the stack | `GSI-1234-upload/feat/add-ucs-endpoints` |

`renovate/*` and `automated/*` are owned by Renovate and the nightly security scan and follow
none of this.

### Pull request titles

```text
[<stack>] <Description> (<ISSUE>)
```

Prose, not a slug: blanks and ordinary sentence capitalisation. The brackets mark the stack and
are dropped for a solo pull request; the parentheses carry the YouTrack key and are dropped
when there is no issue. Whether the issue covers the pull request or the whole stack, the title
is written the same way — the distinction is visible in the branch name and nowhere else. No
emoji in a title, and no position in the stack: the list already shows it, and merging the
bottom of a stack renumbers everything above it, so a "Part 3" written into a title is wrong by
the next merge.

| branch | pull request title |
|---|---|
| `feat/add-ucs-endpoints` | `Add UCS endpoints` |
| `upload/feat/GSI-1234-add-ucs-endpoints` | `[upload] Add UCS endpoints (GSI-1234)` |
| `GSI-1234-upload/feat/add-ucs-endpoints` | `[upload] Add UCS endpoints (GSI-1234)` |

### Pull request descriptions

Write for the reviewer, who has the diff open and finite patience: a few short paragraphs
saying what changed, why, and what to look at. Not a summary of the diff — they can read that —
and not a report on how the work went. If it runs past a screen, cut it rather than adding
headings — and if the cut would lose something the reviewer genuinely needs, the pull request
is probably too large. Splitting it is what a stack is for.

Plain language, and no model register: no "comprehensive" or "seamlessly", no bulleted
restatement of every file touched, no enthusiasm about the change. Detail that does not fit
belongs in the commit body, or in a review comment on the line it concerns.

Emoji are allowed here, sparingly, as section markers or visual cues that help a reader scan —
never carrying meaning on their own, since an emoji that has to be decoded costs more than the
word it replaced, and a screen reader announces it by its Unicode name. They stay out of branch
names, pull request titles and commit messages entirely: there they are permanent, they travel
into every tool that reads `git log`, they make a subject harder to grep for and to read aloud,
and they buy nothing a word would not.

Where an agent contributed substantially, the description closes with a line saying so:
"Generated by Claude Code" where it wrote the change, "Co-authored by Claude Code" where the
work was genuinely shared. Substantially means it drafted the change; suggesting, explaining or
proofreading earns no line at all. Name the model itself only where that matters.

### Commit messages

Pull requests are squashed ([ADR-0020](0020-branching-strategy.md)), so each merge writes one
commit, in [Conventional Commits 1.0.0](https://www.conventionalcommits.org/) form:

```text
<type>(<scope>): <description>

<body>
```

- **Type** is the branch kind, with `hotfix` becoming `fix`.
- **Scope** is the stack name for a pull request in a stack. For a solo pull request it is
  optional: name the member where one owns the change (`fix(ucs):`), leave it off where none
  does (`chore:`).
- **Description** is imperative and lower case, with no trailing period — "add UCS endpoints",
  not "Added UCS endpoints." or "Adds …".
- **The pull request number** closes the subject as ` (#<PR>)`. GitHub supplies it in the
  prefill, but the subject is rewritten at merge time, so it has to survive that — it is the only
  link from a commit back to the review that produced it.
- **Subject length** is 52 characters where it fits and 72 at the outside, counting that
  suffix.
- **Body** is the pull request description cut down to three to five bullets — fewer for a
  small change — hard-wrapped at 72 columns. Say what changed and why; how the review went
  stays in the pull request.
- **The YouTrack key is not repeated here.** The `(#<PR>)` leads to the pull request, which
  carries it.
- **No emoji**, in the subject or the body.
- **Agent attribution stays out of the commit.** No `Co-authored-by:` line for an agent,
  whatever the tool's own guidance says; it goes in the pull request description instead.
  Human co-authors keep their trailers as usual.
- **A breaking change** is marked with `!` before the colon and explained in a
  `BREAKING CHANGE:` footer. That matters for the members released on their own semver
  ([ADR-0004](0004-versioning-and-release-by-tag.md)).

Branch `upload/feat/GSI-1234-add-ucs-endpoints`, pull request
`[upload] Add UCS endpoints (GSI-1234)`, merged as #207:

```text
feat(upload): add UCS endpoints (#207)

- Add POST /uploads and GET /uploads/{id}
- Resolve the storage alias from the box configuration
- Cover both routes in the UCS API tests
```

The same for a solo pull request, where the scope names the member rather than a stack and a
small change earns fewer bullets — branch `fix/GSI-2477-enable-requeueing`, pull request
`Enable requeueing after failed interrogation (GSI-2477)`, merged as #145:

```text
fix(ucs): requeue after failed interrogation (#145)

- Requeue files whose interrogation failed instead of dropping them
- Cap retries at the configured limit and log the final failure
```

## Consequences

- A stack holds together in the pull request list: every entry carries `[<stack>]` and the
  branches sort together under `<stack>/`. Neither is enforced; both are visible at a glance.
- **Every squash merge rewrites its commit message in the merge dialog.** GitHub prefills the
  subject from the pull request title — `[upload] Add UCS endpoints (GSI-1234) (#207)`, which
  is not a Conventional Commit — and the body from the whole description. Both prefills stay,
  because they are the right thing to edit down. Doing the edit is what pull request titles
  that read as prose and commits that parse cost together; it is also a reasonable thing to
  hand an agent, which is why the rules above are written to be followed from the pull request
  alone.
- Conventional types make a generated changelog possible later. We do not generate one today.
- Which changes a model substantially wrote stays answerable — the commit's `(#<PR>)` leads to
  the pull request that says so — without a trailer on every commit that used one for a
  suggestion. It does mean the answer is on GitHub rather than in the repository.
- Renaming a stack means renaming every branch in it and retargeting the chain, so the stack
  name is worth choosing when its first pull request is opened.
- The stack segment is a workaround for a missing GitHub feature, not something we want to own,
  and it should not outlive the gap. When stacks get names and the pull request list can be
  grouped or sorted by them, `[<stack>]` and the branch segment become redundant and this part
  of the convention should be retired.
- Nothing enforces any of this. A branch-name ruleset and a commitlint hook are both possible,
  but neither would catch the part that matters — the message is written at merge time, after
  every check has already run.
- The convention applies to what is opened after it. Branches and pull requests in flight are
  not renamed, so the two schemes coexist until the older work merges.

## Alternatives considered

- **Member-based branch prefixes** (`ucs/…`, `service-commons/…`), where the first segment
  names the component the work touches. Rejected in the kind slot: a great deal of the work
  crosses members or belongs to none in particular — tooling, CI, charts, the test bed, a
  `libs/` change and the consumers it breaks — so the prefix becomes a judgement call exactly
  where a naming rule should be automatic, and the valid set has to be kept in step with the
  members as they are added and retired. It also names the recoverable half: which components a
  branch touches is evident from its diff, its pull request and `just affected`, whereas the
  kind of change — and with it the branch it was cut from, which is the whole point of
  `hotfix` — is recorded nowhere else. The stack slot is the opposite case, and that is why it
  exists: GitHub stacks pull requests but does not yet name the stack itself, so there is
  nowhere else for one to live. The member survives as the optional
  commit scope on solo changes, and in the description.
- **Conventional-Commit-shaped pull request titles** (`feat(upload): add UCS endpoints`), which
  would make the prefilled squash subject correct with no editing. Rejected: titles are read in
  a list, by reviewers and by people who do not write the code, and prose reads better there
  than a type-scope prefix. The body has to be cut down at merge time regardless, so the dialog
  is open either way and the editing does not actually disappear.
- **The YouTrack key in the commit subject** (`feat(upload): add UCS endpoints (GSI-1234)
  (#207)`). Rejected: two parenthesised suffixes, and eleven of the 52 characters spent on a
  key that `(#207)` already leads to.
- **`feature/` rather than `feat/`**, which is the more readable word. Rejected so that the
  branch kind and the commit type are one vocabulary instead of two with a mapping between
  them.
- **The full Angular type set** (`perf`, `ci`, `build`, `style`). Rejected: four more
  categories to choose between at the margin, for changes that `chore` already describes
  adequately — and `style` is close to dead weight with ruff and prettier autofixing.
- **`Co-authored-by:` for the model in the commit**, which is what the agent tools add by
  default. Rejected: it would land on nearly every commit, including the ones where an agent
  only suggested a name or read a diff back, so it would stop distinguishing anything — and
  the distinction is the only reason to record it. Dropping it entirely was rejected too: an
  agent that drafted a change is worth knowing about at review time, which is where the pull
  request description is read. Naming the exact model was rejected as the default for the
  same reason — it dates fast and rarely changes how the change is read.
- **A tool that models stacks natively** (Graphite and its like), which would make the stack
  segment unnecessary. Not rejected on the merits: it is a larger decision than naming, and
  this convention costs nothing if we adopt one later.
