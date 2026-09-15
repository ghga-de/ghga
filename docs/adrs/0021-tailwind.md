# Tailwind

Date: 2024-10-11

## Summary

In the context of **deciding for a way to apply CSS rules**

facing **a wish for a simple codebase with few code duplications**

we decided for **using tailwind (CSS)**

and neglected **a single global stylesheet, inline styles or large component style sheets**

to achieve **a well-structured codebase with few code duplications**

accepting that **this will add a dependency**

## Details

### Status

**accepted**

### Context & Requirements

The application we are building will require at least some CSS to function properly. Not all such rules will be provided by our design system and its ui components. As a consequence, we will need to apply some CSS rules.

Angular provides multiple ways to do this (via style tags in the HTML code, via a global style sheet and component-wide style sheets). The CSS style rules in a component style sheet are not available to other components by default leading to code duplication if the same CSS is required in multiple components. The same is true for style tags. A global style sheet does not face this issue but is much harder to maintain because it's hard to check if rules are still in use or not. Importantly, class tags of HTML tags can be set to runtime values in Angular applications.

None of these options seem optimal, and they also offer little assistance for developers to name classes in a consistent and reusable way. As a consequence, it can easily happen, that component stylesheets have lots of duplicated or deprecated classes with names that are hard to map to a functionality.

### Decision

We have decided to use tailwind.css. Tailwind offers a wide range of CSS classes that implement all CSS features in individual classes. This has two main advantages: Styles can be included in the HTML without writing out the more verbose CSS syntax, and the class names are aligned with a standard that is widely used in modern web-applications. Tailwind also performs a browser style reset - this fixes some behaviors that are not homogenous across browsers. Additionally, we will use a [linter plugin to sort the CSS classes](https://tailwindcss.com/blog/automatic-class-sorting-with-prettier). The standard ordering clusters classes by topic so for example all classes about spacing are clustered and then all classes concerning typeface etc. instead of using a more arbitrary scheme like alphabetical sorting. This functionality is available via the [prettier plugin for tailwind](https://github.com/tailwindlabs/prettier-plugin-tailwindcss) or a [eslint plugin](https://github.com/francoismassart/eslint-plugin-tailwindcss/). The configuration process of tailwind in an angular app is described [here](https://tailwindcss.com/docs/guides/angular).

### Consequences

Our codebase will only contain very little custom CSS. The CSS we use will be tree-shaked and optimized, and we will not have to come up with naming conventions for CSS classes. Additionally, we will not have as many code duplication, and it will be easier to see in the HTML markup, what style actually applies to an element.

In exchange, we have an additional dependency. Tailwind requires its own configuration and has to be integrated into the build process to enable tree-shaking of the classes and the minification of the resulting style sheet.

It also takes some time for developers to get used to using tailwind as with all tools that have similarly wide-ranging impact on the codebase. Since the naming conventions in tailwind are clear and consistent, however, this onboarding period is usually pretty short, and the advantages are obvious during development.

By default, we should be able to go without component style sheets. Color definitions and other highly specific style rules can be implemented in the global style sheet instead. Considering the typical setup of having one HTML, one ts, one spec and one CSS file per component, this approach reduces the number of files by a quarter.

### Alternatives

The dominant role of tailwind is a rare occurrence in the web ecosystem in that there are no 2 ways to do what tailwind does. The decision is to either use CSS or to abstract it away using tailwind. Additionally, tailwind classes typically only contain one rule or the minimal amount of CSS to achieve what the class is supposed to do. For example: if a CSS class contains multiple rules, there is no way to get rid of rules that have no effect in a given instance. This often occurs because classes tend to grow over time. Since there is no easy way to find all places that use a specific class, developers are hesitant to remove rules from classes, unsure of the impact such a change might have.

Tailwind classes only contain very few instructions that are completely bound to what the rule does (text-bold only makes the font bold, no padding or margin, no font family or sizing etc.) Additionally, these classes are applied directly where they are used so it is clear to determine what the impact of a change will be.

The alternative would be to use custom CSS and to define processes to tackle the resulting issues manually or to accept that the CSS codebase will deteriorate over time. Another alternative is to allow style rules to be passed on to children thus enabling style sharing across the levels of the application hierarchy. This option, however, makes it even harder to determine, which rules apply where and how changes will impact the application.

A historic alternative would be a CSS style system (like Bootstrap). These systems provide utility classes for purposes (like a button or a dialog) and reduce the amount of CSS that way. We have decided to use Angular Material as a component library and expect it to help us in this way. These components, however, never cover all use cases. For example: If a text element should simply have a bold font, this will require custom CSS or the introduction of a new UI component, that only has the purpose of applying one line of CSS. Tailwind is intended to help in these situations, not to provide full components. It is a utility to make custom CSS easier to manage. An alternative like Bootstrap or other CSS frameworks would not address this issue and leave us with a need for custom CSS.
