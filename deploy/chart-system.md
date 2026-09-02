# The GHGA Library for Kubernetes

Configurations for most GHGA microservice, ready to launch on Kubernetes using [Kubernetes Helm](https://github.com/helm/helm).

## TL;DR

```bash
helm install my-release oci://registry-1.docker.io/ghga/<chart>-chart --version X.Y.Z
```

### Update Chart

Chart content (name, image, values) is generated from workspace metadata by
`deploy/src/create_charts.py` (`just charts`) — see [../deploy/README.md](./README.md).
Chart version/`appVersion` and publishing are not per-merge: they're stamped and pushed
as OCI artifacts only as part of a platform release (`ghga/X.Y.Z` via
[release.yaml](../.github/workflows/release.yaml), ADR-0004), so a chart version always
matches a released set of images.

## Developer notes

### Update library chart ghga-common locally

If you want to try out an update in the dependency Helm chart `ghga-common`, you need to set the dependency to resolve locally. This can be achieved by specifying the path to the local version of the chart.

In your parent chart's Chart.yaml, update the dependency reference for ghga-common to point to the local file path.
```yaml
dependencies:
  - name: ghga-common
    version: <version>
    repository: file://../ghga-common
```

Verify that the local path ../ghga-common correctly points to the updated ghga-common chart on your file system.
Run the following command to update dependencies and pull the local chart:

```bash
helm dependency update
```

Deploy your parent chart and test the integration with the updated ghga-common chart.

```bash
helm install <release-name> ./<parent-chart>
```
