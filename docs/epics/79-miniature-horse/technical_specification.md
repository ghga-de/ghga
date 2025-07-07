# Data Portal Accessibility, Responsiveness, and Semantics Overhaul and SOPs (Miniature Horse)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://docs.ghga-dev.de/main/sops/sop001_epic_planning.html).

## Scope
### Outline:
This epic seeks to perform two tasks in three different domains.  
These domains are: accessibility, responsiveness, and semantics.

The first task of this epic relates to the overhaul of the data portal to improve its accessibility and semantics, as well as attempt to standardise the implementation of its responsiveness.

The second task is that of creating an ADR that contains guidelines (viz. SOPs) and best practices in the implementation of accessibility, responsiveness, and semantics in the data portal.

### Included/Required:
- The data portal should be fully compliant with the European Accessibility Act (EAA, which also makes reference to EN 301 549), and the Web Content Accessibility Guidelines (WCAG).
- The data portal should make full use of semantic tags and aria attributes whenever applicable, and should ensure the full implementation of [ADR016](http://github.com/ghga-de/adrs/blob/main/docs/adrs/adr016_semantic_web_technologies.md)).
- The data portal should implement responsiveness in a more standardised manner that nevertheless remains suited for the specific purpose of the elements to make responsive.
- Developers should have available documentation and SOPs for best practices on the implementation of accessibility, responsiveness, and semantics, as well as for ensuring that any new features to be released are accessibility-compliant.

### Optional:
- Developers should have available a list of useful tools and extensions to better implement accessibility features.

### Not included:
- The development of our own accessibility standards; only best practices for implementing legally required and any additional standards.
- The implementation of accessibility standards for the administration features unless this is required by relevant staff in GHGA.

## User Journeys (optional)

This epic covers the following user journeys:

- Screen reader users should be able to navigate and use all available public-facing* features of the data portal with minimal hindrance.
- Users with limited vision should be able to easily navigate and use all available public-facing* features of the data portal (to verify with high-contrast settings).
- Users with limited or no perception of colour should be able to easily navigate and use all available public-facing* features of the data portal (to verify with colourblind settings)

^*^: These also include all features available to logged-in users (e.g. request access features, IVA creation, etc.), but not the data steward specific administration pages and features.

## Additional Implementation Details:

- The documentation and implementation should be based on the a11y and responsiveness features that are already provided by Angular, Angular Material, Tailwind CSS, and any other library already in use that provides relevant features. Additional helper code can be provided in the shared directory of the data portal if needed, and additional libraries can be also added for this purpose.

### List of online resources
- [Getting to know the European legislation on accessibility](https://accessible-eu-centre.ec.europa.eu/getting-know-european-legislation-accessibility_en)
- [AccessibleEU Guidelines and Support Materials](https://accessible-eu-centre.ec.europa.eu/guidelines-and-support-materials_en)
- [Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/)
- [Official Angular Accessibility Best Practices](https://angular.dev/best-practices/a11y)
- [angular.love article on the EAA](https://angular.love/digital-accessibility-2025-how-to-avoid-fines-and-win-more-users)
- [Guide to EAA 2025 Compliance by COAX software](https://coaxsoft.com/blog/guide-to-eaa-2025-compliance)
- [Web Accessibility in Angular - Introduction by Angular Architects](https://www.angulararchitects.io/blog/web-accessibility-in-angular/)
- [Accessibility Testing Tools for Angular by Angular Architects](https://www.angulararchitects.io/blog/accessibility-testing-tools/)
- [MDN Curriculum on Semantic HTML](https://developer.mozilla.org/en-US/curriculum/core/semantic-html/)
- [MDN Glossary on Semantics in HTML](https://developer.mozilla.org/en-US/docs/Glossary/Semantics#semantics_in_html)
- [MDN Reference for HTML elements](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements)
- [Angular Accessibility Workshop by Angular Architects](https://www.angulararchitects.io/en/training/angular-accessibility-workshop/)

## Human Resource/Time Estimation:

Number of sprints required: 4

Number of developers required: 1
