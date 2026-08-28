# aai

Local AAI for the self-contained demo/test bed — a generic OIDC provider standing in for
LS Login (ADR-0007). Default profile is Navikt mock-oauth2-server; swap via values for
keycloak or point services at an external issuer.

## Installing

```
helm install aai oci://registry-1.docker.io/ghga/aai-chart
```

## Source

Part of the [GHGA monorepo](https://github.com/ghga-de/ghga/tree/main/deploy/charts/aai).
See [values.yaml](values.yaml) for the full set of configurable values.
