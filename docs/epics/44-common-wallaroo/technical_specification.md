# Choose frontend framework and component library (Common Wallaroo)

**Epic Type:** Exploratory Epic

## Principle Components of Exploration:

In order to start refactoring our frontend, we need to make a final decision regarding the frontend framework, design system and  component library that we will use to build the next version of the data portal and potentially also the follow-up products.

We are limiting the scope to the three most popular frameworks: React (Next.js), Angular, and Vue (Nuxt) that we have already used or evaluated in the Red Kangaroo Epic.

This evaluation can be split into the following tasks:
- Create a list of criteria for the frontend framework that are relevant for us (like: various core features, maturity, stability, popularity, future support, flexibility, completeness, static typing, documentation, testing, licensing, additional features like SSR).
- Define weights for these criteria.
- Evaluate the three frameworks given these criteria, using the insights gained in the Red Kangaroo epic, and finalize the decision for the frontend framework.
- Find three responsive design systems with open source license that would work for us (e.g. Bootstrap, Google Material Design, Foundation). Consider that the design system should work particularly well on desktop screen sizes, mobile is less important for us.
- Create a list of UI components that are most needed and important for us.
- Create a list of 6 popular component libraries for the selected frontend framework supporting these components and design systems.
- Create a list of criteria for these libraries (like: how well do they support the favored design system, how well do they support the selected framework, how well do they support the needed components, maturity, documentation, licensing and possible pricing, maintenance and future support)
- Define weights for these criteria.
- Try to evaluate the libraries given these criteria, without creating test implementations, and finalize the decision for the component library.
- Summarize the decisions in an architecture decision record (ADR).

## Not part of this Exploration:

Aspects that shall be ignored during the exploration:

- Creating test implementations for different component libraries or mock designs with various systems (this would be too time-consuming).

## Material and Resources:

- see [Red Kangaroo](../31-red-kangaroo/technical_specifications.md) epic for frontend frameworks
- [What Is a Front-End Design System, and Why Is It Necessary?](https://semaphoreci.com/blog/front-end-design-system)
- [Overview of 25+ UI Component Libraries in 2023](https://www.builder.io/blog/25-plus-ui-component-libraries)

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
