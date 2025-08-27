# Accessibility and Semantics Best Practices for Developers

The themes of accessibility (aka a11y) and semantics have been joined due to the latter's relationship with the former.
**Where there is good web semantics, there is better accessibility.**

Base HTML5 provides a large number of tools for accessibility-centred development, especially in the form of [ARIA attributes and roles](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference) ([but see some common pitfalls here](https://web.dev/learn/accessibility/aria-html?continue=https%3A%2F%2Fweb.dev%2Flearn%2Faccessibility%2F%23article-https%3A%2F%2Fweb.dev%2Flearn%2Faccessibility%2Faria-html)).
Angular (and Angular Material) provide additional features, including the [Angular Material `a11y` package](https://material.angular.dev/cdk/a11y/overview), and [the binding of ARIA attributes and roles in Angular](https://angular.dev/best-practices/a11y#accessibility-attributes).

The main requirements of the relevant legislation, the [European Accessibility Act (EAA)](https://www.wcag.com/compliance/european-accessibility-act/) are [compliance with WCAG 2.1 level AA, and EU legislation EN 301 549](https://www.wcag.com/compliance/european-accessibility-act/#What_technical_standards_should_you_follow_for_EAA_compliance).
[Developers](https://www.w3.org/WAI/tips/developing/) (who, in our case, are necessarily [designers](https://www.w3.org/WAI/tips/designing/)) must [intimately familiarise themselves](https://www.w3.org/WAI/tutorials/) with both [WCAG 2.1](https://www.w3.org/WAI/WCAG22/quickref/?versions=2.1) [level AA](https://www.wcag.com/resource/what-is-wcag/#The_Three_Levels_of_WCAG_Conformance_A_AA_and_AAA) and [EN 301 549](https://www.wcag.com/compliance/en-301-549/).
There is no real shortcut to this process.
Proper compliance requires a deep understanding of both guidelines.

Here is a list of the ten most crucial accessibility requirements specifically for websites here as a starting point:

- Accessibility for keyboard-only users (e.g. tab-based navigation).
- Screen reader accessible content.
- Clearly labelled forms with clear instructions.
- ARIA labels and roles of custom components (Angular and Angular Material already specify these for most components, and most semantic HTML elements do not need label or role specification).
- Colour contrast (in the case of WCAG 2.1 AA of minimum 4.5 to 1).
- Correct heading and content structure.
- Consistent navigation elements.
- Accessibility of _on hover_ and _on focus_ content.
- Understandable context in link text (e.g. not having a link that only says 'here' or 'click')

Evaluation of our compliance with WCAG 2.1 AA and EN 301 549 should be based on the [actual guidelines](https://www.w3.org/TR/WCAG21/); however, when developing, we have access to validation tools for many aspects of our website's compliance.
The W3C has a [guide on web accessibility evaluation](https://www.w3.org/WAI/test-evaluate/), including a [list of evaluation tools (both websites and browser extensions)](https://www.w3.org/WAI/test-evaluate/tools/list/), and browsers come with a set of accessibility tools by default.

**Our team uses the [SilkTide toolbar](https://silktide.com/toolbar/) for the GHGA website with great success.**

The [WAVE Web Accessibility Evaluation Tool](https://wave.webaim.org), the [ARC Toolkit](https://www.tpgi.com/arc-platform/arc-toolkit/), and the [Skynet Technologies Free Accessibility Checker](https://www.skynettechnologies.com/accessibility-checker) are also great options to evaluate the current compliance status.
Angular ESLint has a [template plugin](https://github.com/angular-eslint/angular-eslint/blob/main/packages/eslint-plugin-template/README.md) with several rules for accessibility, such as [`alt-text`](https://github.com/angular-eslint/angular-eslint/blob/main/packages/eslint-plugin-template/docs/rules/alt-text.md) and [`mouse-events-have-key-events`](https://github.com/angular-eslint/angular-eslint/blob/main/packages/eslint-plugin-template/docs/rules/mouse-events-have-key-events.md). There is also this three-part Angular ESLint Rules for Accessibility articles series:

- [Article 1 about Keyboard Accessibility Rules for ESLint](https://dev.to/angular/angular-eslint-rules-for-keyboard-accessibility-236f),
- [Article 2 about ESLint Rules for ARIA](https://dev.to/angular/angular-eslint-rules-for-aria-3ba1),
- and [Article 3 about ESLint Rules for Accessible HTML Content](https://dev.to/angular/angular-eslint-rules-for-accessible-html-content-kf5).

We adopt and consistently use these tools, because all pages (except administrator pages) in the data portal MUST be compliant with EAA requirements.
[These compliance checking tools do not check adherence to _all_ the WCAG 2.1 AA guidelines, and thus provide very inconsistent results. Thus no single tool should be relied on exclusively. Accessibility testing cannot be done in a fully automated manner, so the use of multiple tools along with manual evaluation is required.](https://www.w3.org/WAI/test-evaluate/tools/selecting/) In many cases, these tools only test the _deployed_ version of the data portal. Therefore, [improving accessibility is an iterative process](https://www.wcag.com/solutions/accessibility-checker/#Implementation_process).
Developers must at least include [screen reader testing and contrast testing](https://www.w3.org/WAI/test-evaluate/easy-checks/) in the process of development to verify at least basic compliance, as well as verify the compliance of other developers' code.
For administration pages (currently available to data stewards only), we can be less strict since individual requirements can be catered to individually, but maintaining the same standards for all pages would be ideal.

The GHGA brand colours are not high-contrast enough to be compliant.
Therefore we need a high-contrast mode and palette.
These styles can be applied with either native CSS (using [`prefers-contrast`](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-contrast)) or a dedicated toggle button (which requires a session cookie to persist the setting across pages and reloads).
Tools to check for colour contrast ratios can be found in the links above.

See also [links in Epic Spec 79](https://github.com/ghga-de/epic-docs/blob/main/79-miniature-horse/technical_specification.md#list-of-online-resources).
