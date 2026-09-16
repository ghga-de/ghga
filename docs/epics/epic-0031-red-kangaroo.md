# Angular/Vue for Data Portal (Red Kangaroo)
**Epic Type:** Exploratory Epic

Epic planning and implementation follows the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/)

## Principal Components of Exploration:

This epic seeks to explore the use of Angular and Vue for a refactoring of the Data Portal (party due to the deprecation of Create-React-App) by implementing some basic Metadata Catalog(ue) functionality on both frameworks and deciding on a potential framework for future refactoring.

### Questions to Answer
- Are any of the two options suitable for the development of the data portal?
- If so, which framework is best suited for the development of the data portal?
- Which framework's data handling system is best suited for the requirements of the data portal?
- Are Vue's advantages (e.g. shallower learning curve, less restrictive framework) enough of a positive to counter the lack of previous experience with it in the team?
- How is the overall development ergonomics? How many decisions do we have to make ourselves? How much structure is provided?

## Material and Resources:

Materials to be studied (e.g. articles, book chapters, youtube videos, etc.) and any (external) persons/experts to talk to:

[- Learning material defined here](https://wiki.verbis.dkfz.de/pages/viewpage.action?pageId=266600453)

## User Journeys (Optional)

This epic covers the following user journeys:

- The user views a list of all datasets
- The user filters the list of datasets based on facets provided by the API
- The user can see the summary of the details of the datasets the user selects.
- The user can see the full details of the datasets the user selects
- The user can submit a mock access request form

## Additional Implementation Details:

- Although self-evident, it is important to specify the Metadata Catalog(ue) functionality will be implemented in both Angular and Vue.
- The implementation will require the decelopment of a mock data service to examine the coding required for API calling in both Angular and Vue. This will add to the time required for development.

## Human Resource/Time Estimation:

Number of sprints required: 3

Number of developers required: 1
