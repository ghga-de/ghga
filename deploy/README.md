# The GHGA Library for Kubernetes

Configurations for most GHGA microservice, ready to launch on Kubernetes using [Kubernetes Helm](https://github.com/helm/helm).

## TL;DR

```bash
helm repo add ghga https://ghga-de.github.io/charts
helm search repo ghga
helm install my-release ghga/<chart>
```

### Update Chart

- Update `appVersion` in Chart.yaml to desired version
- Update values.yaml or add service parameters (only required or parameters which differ from default on purpose)
- Create PR

## Developer notes

### Update library chart `ghga-common` locally

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

> [!IMPORTANT]
> If you intend to use the updated version of the `ghga-common` chart in a wider or production context, you will need to publish the updated chart to your chart repository before using it in the parent charts.
