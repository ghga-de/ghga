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

### End-to-end testing of ghga-common

In some scenarios, it makes sense to run end-to-end tests—for example, when changes in ghga-common need to be validated all the way through to a fully functional deployment. To achieve this, follow these steps:

- Create an empty branch (for better diffs) in ghga-de/charts with the prefix ghga-common/.

- Create an empty branch in ghga-de/devops-kubernetes-hub with the prefix testing and push an empty commit, e.g., `git commit --allow-empty -m "Init"`.

- Open a PR and add the labels: `deployed` and `repoRef: ghga-common/<your-suffix>`.

- Verify that the rendered manifests were pushed to the GitOps branch gitops-testing.

- Update your charts branch in ghga-de/charts. If no diffs are present in ghga-de/devops-kubernetes-hub, rerun the GitOps action manually.

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

