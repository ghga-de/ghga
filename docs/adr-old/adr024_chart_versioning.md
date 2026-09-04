# Helm Charts Versioning

Date: 2025-02-24

## Summary

In the context of **Helm Charts semantic versioning**

facing **the need to simplify the process of releasing and versioning Charts**

we decided for **using a common Chart version for all microservice Charts**

and neglected **service specific versioning**

to achieve **a lightweight, custom solution facilitating and accelerating our CD pipelines**

accepting that **more convincing reasons for a service specific versioning or using of a Helm super Chart may come up in the future**.

## Details

### Status

**Accepted**

### Context & Requirements

Currently the Chart version is bumped by either a new (i) service release or an update of the (ii) library chart.
The microservice Charts are instances of the library chart differing only in their values.

We need a way to handle Chart update events more elegantly. We are maintaining a separate application chart per microservice, plus one library chart.
With a growing number of services, this leads to a version landscape that is more complex than necessary. Also, due to our microservice and application behavior, this process often requires a lot of back and forth development in order to lift it into Kubernetes.

### Decision

We propose to implement a custom solution that takes into account our Chart architecture (library chart) and application architecture (microservices):
1. Use only one Chart version for all Charts belonging to one application^1.
2. Bump Chart version analog to version change for case (i) and (ii).

^1 The definition of application is another topic. Since we have only one currently, this could be straight forward.

### Consequences

This change will make it easier and clearer what to do in case of both events.
It reduces the number of coexisting versions, hence reducing the complexity.
Additionally only one version needs to be updated in the downstream applications (CD pipeline).
Also, by using a *super* version the inter-service dependency and superordinate application is highlighted.

On the other hand, we lose fine grain control of Chart versions.
We will update all Charts for every change in the application version, which produces plenty of releases.

### Alternatives

An alternative would be to use a Helm super chart. However, this approach doesn't work well with our downstream CD pipeline (Helmfile), due to the nested values. It might be possible to use Helm instead of Helmfile in the future, but this requires exploration how it affects the (hierarchical) templating of values.

Another solution could be to use a local Charts repository. This would reduce the credibility of the version, since it would suggest less agreement with semver guarantees. However, developing Charts is often a back and forth process, and looking at this component in isolation is helpful.
