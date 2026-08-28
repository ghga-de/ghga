# auth-km-jobs

GHGA Auth Key Management Jobs - refreshes signing keys and re-encrypts secrets used by GHGA; runs as a Kubernetes Job, either regularly or on demand.

## Installing

```
helm install auth-km-jobs oci://registry-1.docker.io/ghga/auth-km-jobs-chart
```

## Source

Part of the [GHGA monorepo](https://github.com/ghga-de/ghga/tree/main/tools/auth-km-jobs). See
[values.yaml](values.yaml) for the full set of configurable values.
