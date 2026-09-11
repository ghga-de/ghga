# ADR-0022 — Naming branches, pull requests and commits

- **Status:** Accepted
- **Date:** 2026-09-14

## Context

[ADR-0020](0020-branching-strategy.md) settled which branch work is cut from and merged into,
but not what any of it is called. A change carries three names — its branch, its pull request,
and the commit that lands on `dev` — and all three currently drift. Branch prefixes name the
member (`ucs/`, `service-commons/`, and `service_commons/` alongside it), slugs mix kebab-case
and snake_case, YouTrack keys turn up at either end of the slug or not at all, and pull request
titles carry ad-hoc component abbreviations in whatever casing the author chose: `UCS:`, `RS:`,
`DHFS:`, `dskit:`, `Connector:`, `metldata:`, `Notification-Service:`.

Two forces make this worth deciding rather than leaving to taste.

**We work in stacks.** A stack is a chain of pull requests, each based on the previous one and
rooted at `dev`, so that a large piece of work stays reviewable in pieces. Three are open at
the time of writing; the longest is sixteen pull requests deep. GitHub models none of it: it
shows one flat list, and the only thing telling a reader that two entries belong together is
what they are called. Today that is improvised — "Part 1", "Part 2" in the title, or a shared
member prefix on the branch — so a stack comes apart in the list as soon as one entry is worded
differently. The name of the stack has to live in the branch name and the pull request title
because there is nowhere else to put it.

**Squash merge makes the pull request the commit.** With one commit per pull request, the title
and description a reviewer skims become the permanent record in `git log` — which is read more
often, and by more tools, than the pull request list ever is.

## Decision

> In the context of a monorepo where large work arrives as stacks of pull requests, facing
> GitHub's lack of any notion of a stack and a squash-merge history whose quality is whatever
> the pull request titles happened to be, we decided to derive all three names — branch, pull
> request and commit — from one grammar of kind, stack and description, and to write the
> commits as Conventional Commits, to achieve a legible history and stacks that hold together
> in the pull request list, accepting that every merge needs its commit message edited by hand.

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

`hotfix` is the only kind that is not also a commit type. It marks the one branch cut from
`main` rather than `dev` ([ADR-0020](0020-branching-strategy.md)) — a fact that matters while
the branch exists and not afterwards, so its commits are typed `fix`. There is deliberately no
`release` kind: a release is a merge plus a tag.

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
is written the same way — the distinction is visible in the branch name and nowhere else.

| branch | pull request title |
|---|---|
| `feat/add-ucs-endpoints` | `Add UCS endpoints` |
| `upload/feat/GSI-1234-add-ucs-endpoints` | `[upload] Add UCS endpoints (GSI-1234)` |
| `GSI-1234-upload/feat/add-ucs-endpoints` | `[upload] Add UCS endpoints (GSI-1234)` |

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
- **Subject length** is 52 characters where it fits and 72 at the outside, counting the
  ` (#<PR>)` that GitHub appends.
- **Body** is the pull request description cut down to three to five bullets — fewer for a
  small change — hard-wrapped at 72 columns. Say what changed and why; how the review went
  stays in the pull request.
- **The YouTrack key is not repeated here.** The appended `(#<PR>)` leads to the pull request,
  which carries it.
- **A breaking change** is marked with `!` before the colon and explained in a
  `BREAKING CHANGE:` footer. That matters for the members released on their own semver
  ([ADR-0004](0004-versioning-and-release-by-tag.md)).

Pull request `[upload] Add UCS endpoints (GSI-1234)`, merged as #194, lands as:

```text
feat(upload): add UCS endpoints (#194)

- Add POST /uploads and GET /uploads/{id}
- Resolve the storage alias from the box configuration
- Cover both routes in the UCS API tests
```

## Consequences

- A stack holds together in the pull request list: every entry carries `[<stack>]` and the
  branches sort together under `<stack>/`. Neither is enforced; both are visible at a glance.
- **Every squash merge needs its commit message edited in the merge dialog.** GitHub prefills
  the subject from the pull request title — `[upload] Add UCS endpoints (GSI-1234) (#194)`,
  which is not a Conventional Commit — and the body from the whole description. Both prefills
  stay, because they are the right thing to edit down; the editing is what pull request titles
  that read as prose and commits that parse cost together.
- Conventional types make a generated changelog possible later. We do not generate one today.
- Renaming a stack means renaming every branch in it and retargeting the chain, so the stack
  name is worth choosing when its first pull request is opened.
- Nothing enforces any of this. A branch-name ruleset and a commitlint hook are both possible,
  but neither would catch the part that matters — the message is written by hand at merge time,
  after every check has already run.
- Branches and pull requests already in flight are not renamed; the three open stacks keep
  their member-prefixed names.

## Alternatives considered

- **Member-based branch prefixes** (`ucs/…`, `service-commons/…`) — the de facto convention
  today, and what most open branches use. Rejected in the kind slot: a great deal of the work
  crosses members or belongs to none in particular — tooling, CI, charts, the test bed, a
  `libs/` change and the consumers it breaks — so the prefix becomes a judgement call exactly
  where a naming rule should be automatic, and the valid set has to be kept in step with the
  members as they are added and retired. It also names the recoverable half: which components a
  branch touches is evident from its diff, its pull request and `just affected`, whereas the
  kind of change — and with it the branch it was cut from, which is the whole point of
  `hotfix` — is recorded nowhere else. The stack slot is the opposite case, and that is why it
  exists: a stack has no representation in GitHub at all. The member survives as the optional
  commit scope on solo changes, and in the description.
- **Conventional-Commit-shaped pull request titles** (`feat(upload): add UCS endpoints`), which
  would make the prefilled squash subject correct with no editing. Rejected: titles are read in
  a list, by reviewers and by people who do not write the code, and prose reads better there
  than a type-scope prefix. The body has to be cut down at merge time regardless, so the dialog
  is open either way and the editing does not actually disappear.
- **The YouTrack key in the commit subject** (`feat(upload): add UCS endpoints (GSI-1234)
  (#194)`). Rejected: two parenthesised suffixes, and eleven of the 52 characters spent on a
  key that `(#194)` already leads to.
- **`feature/` rather than `feat/`**, which is the more readable word. Rejected so that the
  branch kind and the commit type are one vocabulary instead of two with a mapping between
  them.
- **The full Angular type set** (`perf`, `ci`, `build`, `style`). Rejected: four more
  categories to choose between at the margin, for changes that `chore` already describes
  adequately — and `style` is close to dead weight with ruff and prettier autofixing.
- **A tool that models stacks natively** (Graphite and its like), which would make the stack
  segment unnecessary. Not rejected on the merits: it is a larger decision than naming, and
  this convention costs nothing if we adopt one later.
