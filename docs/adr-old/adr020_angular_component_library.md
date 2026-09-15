# Angular UI Component Library Selection

Date: 2024-10-11

## Summary

In the context of **the need for a component library for the development of the refactored data portal**

facing **a previous choice to use the Material design system**

we decided for **Angular Material**

and neglected **several available component libraries listed below**

to achieve **a hassle-free implementation of Material design for Angular with a component library made specifically for the design system**

accepting that **other libraries may have more components that could prove useful**.

## Details

### Status

**accepted**

### Context & Requirements

Having chosen Material as the design system we would implement for the refactoring of the data portal ([ADR 019](./adr019_responsive_design_systems.md)), we needed to select a suitable component library that either has already implemented the Material design system, or has enough styling flexibility to allow for us to do so if we choose to.
The primary requirements were the ability to implement the Material design system without having to repurpose the library entirely (e.g. having to rewrite all of Nebular's styles to suit Material UI because it is based on the Eva design system); thus component libraries based on other design systems (this does not include libraries that have a default theme but not based on a design system specifically, such as Bootstrap) would be rejected.
Finally, the goal was to have a solution aiming to avoid excessive work (e.g. rewriting all the theming for Material), was well-maintaned (i.e. so that updates to Material design would be applied to the library without much delay), and comprehensive (i.e. so that the necessary components would be available).

### Decision

Several alternatives had been explored previously (in an earlier ADR that has since been superseded and is not part of this repository); a list consisting of: Angular Material, ng- and ngx-Bootstrap, PrimeNG, Nebular, Semantic UI, UIKit, and Foundation.
Developer feedback and our own follow-up evaluation raised concerns about the previously preferred option, PrimeNG, which are described in the alternatives section below.
We therefore widened the search.

Additional exploration of the libraries Tailwind CSS, Taiga UI, Onsen UI, ng-lightning and Spartan UI was thus undertaken in preparation, along with an updated look at the libraries in the previous list.
In addition, if we were to consider the research done on component libraries of design systems included in [ADR 019](./adr019_responsive_design_systems.md), we could add Clarity, Ant, and Fluent to this list; though these would be rejected *a priori* in any case, as were Syncfusion and Kendo UI, due to their paid nature which goes against our aim to be based on free and open source software only.
Due to being based on other design systems, ng-lightning, Nebular (Eva design system), and Foundation were rejected outright.

This left us only with Angular Material, ng- and ngx-Bootstrap, PrimeNG, Semantic UI, UIKit, Tailwind CSS, Taiga UI, Onsen UI, and Spartan UI.

Angular Material is the main Angular component library implementation of Material design.
Its set of components, while extensive, is not exhaustive for fancier elements (e.g. file drag and drop); though the library offsets this weakness by being very well-maintained, currently (according to its documentation) already implementing Material version 3, the current version of the design system.
It also has the advantage of being focused entirely on the Material design system; a sign that updates to the design specifications would be implemented quickly.

Tailwind CSS, lacking components (these only come as part of Tailwind UI, a paid component library), was not suitable as a component library, though its style framework may prove useful for our implementation.
UIKit, although highly customisable, is not an Angular component library specifically, but just a front-end framework, much like Tailwind CSS, though with special classes for its defined components that are applied to the required HTML tags (e.g. navigation `uk-dotnav` class must be assigned to an `<ul>`).
Considering that UIKit has no (official) existing implementation of Material design, using it would require more development time than we can spend to reach the state we need.
Similarly lacking an Angular-specific implementation (like UIKit) Semantic UI does however implement Material-based theming.
At the time of evaluation, this implementation of Material appeared to be out of date or incomplete for our requirements, and its component set was smaller than that of Angular Material.

Onsen UI is a library that implements both Material and Flat (the iOS design system), and has an Angular-specific implementation.
Its implementation of Material seems to be well done, though it is unclear what version of the design system is being used for this.
However its focus seems to be more on small-screen sites and PWAs, as shown by the manner in which the component previews are shown.

At the time of evaluation, the Bootstrap-based libraries offered fewer of the components we needed than Angular Material, and neither provided a readily available Material implementation.
Taiga UI offered a larger component set, but its theming capabilities did not appear sufficient to implement Material without substantial additional work.
Spartan UI is a component library based on Tailwind CSS, but as of this writing, its components (a slightly larger list than Angular Material) are only in an alpha stage, with the documentation stating one should expect breaking changes.
Together with the Material theming we would have had to add ourselves, this made it unsuitable for our needs at that time.

### Consequences

Angular Material becomes the component library to use.
Other component libraries are rejected.

### Alternatives

Although most librares did not meet our main requirements, a few of the most viable alternatives to the selection made here are the following:
PrimeNG offers a wider range of useful components than our selection.
In our evaluation, however, we ran into behavioural and performance issues in several of the components we tried, and only the basic themes are available free of charge, while further themes and the theming tools are part of a paid offering, which does not fit our aim to build on free and open source software only.
Onsen UI could also be an interesting choice because it ships a Material implementation, but its focus on small-screen sites and PWAs is a weaker match for our portal.
