# ghga-common

Shared library chart providing common templates, helpers, and default values used by
every GHGA service chart.

This is a Helm **library** chart — it has no templates of its own and cannot be
`helm install`ed directly. Add it as a dependency in another chart's `Chart.yaml`:

```yaml
dependencies:
  - name: ghga-common
    version: "2.12.0"
    repository: oci://registry-1.docker.io/ghga
```

## Source

Part of the [GHGA monorepo](https://github.com/ghga-de/ghga/tree/main/deploy/charts/ghga-common).
See [values.yaml](values.yaml) for the exported defaults.
