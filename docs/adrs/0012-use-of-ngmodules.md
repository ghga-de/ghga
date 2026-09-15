# Angular with Standalone Components instead of NgModules

Date: 2024-09-25

## Summary

In the context of structuring Angular Components

facing the choice between NgModules and standalone components

we decided for using only standalone components

and neglected NgModules or using "Single Angular Component Modules"

to achieve a modern, flexible code base that allows fine-grained lazy-loading

accepting that dependencies need to be declared on the component level.

## Details

### Status

**accepted**

### Context & Requirements

NgModules have long been a core concept of Angular and have seen widespread use. However, with the introduction of the newer concept of standalone components, we need to decide whether to adopt this new approach for building Angular applications or continue using NgModules.

### Decision

We decided to use standalone components exclusively.

They are a more flexible and lightweight approach than NgModules and allow more fine-grained lazy-loading. We don't see any limitations or downsides following this approach. The feature has matured and known issues have been solved over the last versions of Angular, so that it will become the default in the upcoming version 19.

### Consequences

Creating new components and restructuring code will become significantly easier. Additionally, lazy-loading will be more powerful, as it can now be leveraged at the level of individual components. Dependencies will be more fine-grained, making it simpler to verify necessary imports. Although listing imports in the component decorator may seem like a disadvantage, the visibility of the explicit imports in the component file actually should be seen as an advantage.

### Alternatives

The only alternative would be to continue using NgModules, thereby missing out on the benefits of standalone components.
