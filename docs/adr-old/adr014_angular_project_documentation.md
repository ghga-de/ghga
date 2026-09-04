# Angular Project Documentation

Date: 2024-09-24

## Summary

In the context of **establishing a documentation for the angular codebase**

facing **a need for easy-to-follow rules, no hassle in development and the ability to understand the codebase quickly for new developers**

we decided for **for using [JSDoc](https://jsdoc.app/about-getting-started), the [eslint plugin for jsdoc](https://www.npmjs.com/package/eslint-plugin-jsdoc) and [Compodoc](https://compodoc.app/)**

and neglected **[Storybook](https://storybook.js.org/), [TypeDoc](https://typedoc.org), [documentation.js](http://documentation.js.org/)**

to achieve **a good level of documentation that is easy to onboard new developers with and easy to maintain**

accepting that **features vary between frameworks and there will be effort involved in documenting the codebase**.

## Details

### Status

**accepted**

### Context & Requirements

JSDoc is a natural choice because its style is aligned with that of JavaDoc, for example, and is therefore known to most developers. The more important question is which tools to use on top of the information stored in JSDoc and to decide on specifics of how to use JSDoc.

Documentation always entails extra work. The goal in documenting the codebase is therefore to do it in such a way that the benefits outweigh this additional effort, leading to two main levers: Increasing the advantages the documentation provides and decreasing the effort.

On the side of generating benefits, the first question is the audience of the documentation. Four groups of readers come to mind: The developers currently working on the codebase, the designers working on the project, new developers joining the project and finally, external developers who use the project as an API or dependency. In discussions, we have decided not to focus on design aspects at this time because at this time there are no designers in the project whose input would be required for these decisions. Due to its focus on UI design, we set Storybook aside for now: its main benefits address design workflows that we do not currently have, while maintaining the required stories would add ongoing effort.

TypeDoc is a framework that is frequently used for API documentation, offering a clear list of all the exposed APIs and the types they use. Since we don't offer APIs externally and this project will not be a dependency for others, we can neglect TypeDoc, since other frameworks offer more features to document the internal structure of the project (instead of focussing on the external interfaces).

After these considerations, documentation.js and Compodoc are left as competitors. At the time of writing, the documentation.js repository showed no commits for about two years. Since the JS and TS language standards evolve quickly, we preferred a tool with a more recent release history for our documentation pipeline.

Compodoc offers multiple main advantages:
- Compodoc is developed for Angular, so the documentation understands concepts like Angular components, services, pipes etc.
- It creates a graphic visualization of Angular components (that is compatible with standalone components) that allows new developers understand how the component tree is structured quickly.
- It builds a website to quickly read and search the docs.
- The framework is actively maintained.
- It provides a coverage report for the documentation, that will allow us to track how we are doing in documenting our code.

### Decision

Use a stack of JSDoc documentation, an ESlint plugin to enforce documentation and using Compodoc to visualize the information.
The [Eslint plugin JSDoc](https://www.npmjs.com/package/eslint-plugin-jsdoc) offers a recommended set of documentation rules that we can start with and possible adapt if problems or different wishes arise.

An additional guiding principle is to focus on documenting *public* functions specifically, since these are more likely to be used by other developers who will depend on the documentation to understand these functions. It also makes sense to focus on programming in such a way that makes it almost unnecessary to document functions because their names describe it completely.

### Consequences

We will be able to onboard developers faster thanks to the documentation that will be available, and be provided with useful insights in the IDE (because JSDoc is well-supported).
We will *not* have visual documentation of component states because only Storybook provides this feature and maintaining the required codebase would not be worth the (small) benefits.
Once we have some experience with this stack, we can set goals and (lower) limits for our documentation effort to trigger action if the level of documentation drops.

The documentation does not have to be deployed anywhere - it can be generated from the codebase and run locally on the devs machine.

### Alternatives

Several alternatives were listed above and their properties discussed. If large problems arise from the chosen stack, migrating to different tools is easy. Moving to a different documentation language (away from JSDoc) would be more effort but still a semi-automatic refactoring.
