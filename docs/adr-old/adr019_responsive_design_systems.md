# Responsive Design Systems

Date: 2024-09-27

## Summary

In the context of **requiring a consistent-looking and reusable set of components, iconography, layouts, and overall look of the elements of the web UI; a [design system](https://help.figma.com/hc/en-us/articles/14552901442839-Overview-Introduction-to-design-systems)**

facing **the need for a well-supported (e.g. with component libraries for Angular), well-known, and well-documented design system**

we decided for **selecting the Material Design System by Google**

and neglected **alternative design systems, such as Ant, Clarity, and Bootstrap, as well as those with e.g. no available Angular component libraries**

to achieve **consistent design across the data portal pages with considerable flexibility in the choice of component libraries to use**

accepting that **other design systems might be opinionated in a way more compatible with our use case, or provide better-looking results (e.g. for large screens)**.

## Details

### Status

**accepted**

### Context & Requirements

A design system is necessary to achieve a consistent look of elements and pages in any website, which is vital for providing clear and uncomplicated user experiences.
Although it would be possible to create one from scratch, this can be a considerable amount of work.
In addition, since we already are using a fully-fledged well-maintained and widely-adopted Javascript framework, the implementation of existing design systems is trivially easy with a component or style library implementation.

### Decision

There exist many publicly available design systems, each with distinct focus, style, elements, interactions, and opinionation.
We explored several options, a perhaps non-exhaustive list, but with a wide enough reach to encompass the most popular ones, taking it as a correlation for wide adoption and good maintenance.
The shortlist of suggestions consisted of: Bootstrap, Material, Ant, Tailwind, Clarity, Carbon, Fluent, Chakra, Foundation, and Spartan UI.

One important factor to consider was whether these design systems had implementations (i.e. component and style libraries) for Angular.
Without these, the work of implementing the selected design system would fall on the development team, and this is an unnecessary workload to add to the refactoring.
For this reason, Foundation, Fluent (in its version 2), and Chakra were quickly eliminated.
Tailwind CSS is only a CSS styling library, and although very well-made, it lacks any UI components.
The components are included only in the paid Tailwind *UI* component library, which is separate from Tailwind CSS (though based on it).
Its CSS classes might still prove very useful for styling our site and components whilst adhering to the selected design system, but it is not sufficient as a design system on its own.
Spartan UI is part of the spartan toolset, which is itself an entire 'opinionated full-stack' of tools, of which Spartan UI is a subset, and Tailwind CSS the base of Spartan UI.
Spartan UI is not necessarily a design system, and its components are only in alpha, making it unsuitable for much discussion here.

As this was very subjective choice, since the remaining five were all comparable in many aspects, the final choice would be simply based on developer choice.
In this case, the decision was made to choose Material as the design system to use.
Material's open source nature, its backing by a large corporation (Google, in this case), its popularity in both adoption and support through various component libraries for Angular (e.g. [Angular Material](https://material.angular.io/)), its likely familiarity to many users due to its use in the Google ecosystem (Android, ChromeOS, Google web apps, etc.) and its continuous development (now currently at version 3, and version 1 for its Web specification) can all be seen as useful criteria for justifying the decision.

### Consequences

Some popular systems were eschewed, and there is a possibility that they could have been more appropriate for the data portal than the selected one, but were not selected due to their broad characteristics, as well as their current (though perhaps not future) lack of implementations for Angular.
However, the choice of Material will simplify development since we can resort to existing, well-maintained and documented libraries, particularly Angular Material, and this will help achieve a consistent look that is familiar to many users.
On the other hand, Material is opinionated and less familiar to users accustomed to Microsoft or Apple products.

### Alternatives

The other design systems that were evaluated but not selected remain alternatives, as are many other design systems that were not even assessed in this process.
