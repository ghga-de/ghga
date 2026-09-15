# ADR-0028 — Demo and test bed: one self-contained umbrella on kind

- **Status:** accepted
- **Date:** 2026-06-30
- **Amended:** 2026-09-15

## Summary

In the context of **a GHGA that installs with one command, and an integration test bed
that must test what we deploy**

facing **production infrastructure run by operators that is too heavy for a single-node
cluster, and a docker-compose test bed that did not test the charts**

we decided for **one umbrella chart bundling an edge and lightweight infrastructure,
installed as the demo and, with a test-bed profile, as the per-PR test bed, on kind both
in CI and inside the devcontainer**

and neglected **bundling full Istio, a demo flag in the app charts, keeping
docker-compose, minikube, and a host-level cluster**

to achieve **a green integration gate that means the deployable system works, and a
local loop identical to CI**

accepting that **Istio, mesh mTLS and Strimzi are tested only in staging, and the
devcontainer runs a privileged Docker daemon**.

## Details

### Context

`helm install ghga` should give a working GHGA, including a local AAI, on a cluster you
control and without an operations team. App charts own a workload's resources but not
the edge or the infrastructure ([ADR-0031](0031-helm-chart-boundary-hybrid.md)), so
something else has to supply those. Production gets them from Istio, Strimzi and other
operators, which are heavy on a single-node cluster.

The integration suite, BDD and Playwright tests over the whole user journey, ran on
docker-compose, so a green run said nothing about the charts we deploy.

### Decision

**One umbrella.** `deploy/charts/ghga-demo` depends on the app charts and bundles what
production gets from the platform: the Envoy Gateway edge with real ext-authz against
the auth adapter ([ADR-0032](0032-self-contained-edge-envoy-gateway.md)), operator-free
stand-ins for Kafka, MongoDB, S3 and Vault, a local AAI
([ADR-0029](0029-local-aai-generic-oidc.md)), a mail sink, and Jobs that generate the
secrets ([ADR-0035](0035-secrets-and-tls.md)) and seed a data steward. **Amended
2026-09-15:** the S3 stand-in is Chainguard's MinIO build, digest-pinned and tracked by
Renovate, because upstream stopped publishing images.

**The demo is the test bed.** The test bed installs the same umbrella with a test-bed
profile, which adds the state-management service
([ADR-0030](0030-state-management-service-testbed-only.md)). What you install is what CI
tests.

**kind everywhere.** CI runs the umbrella on kind, and so does the local loop, with kind
inside the devcontainer's own Docker daemon. Local runs and CI use the same recipes.

The [architecture
overview](../architecture/overview.md#35-helm--adopt-ghga-common-app-charts--demo-umbrella)
describes what the umbrella contains and how its profiles stack.

### Consequences

- A green integration gate covers the charts, the images, and the real Gateway API
  routing and ext-authz path.
- Production still differs in the edge auth object, mesh mTLS and Strimzi specifics.
  Those are checked in staging, not per pull request.
- The devcontainer is privileged: code running in it is one step from root on the Docker
  host. The unit tests' testcontainers need a Docker daemon there anyway.
- Nested Docker brings its own networking problems, and a devcontainer rebuild loses the
  cluster and its images.
- The whole platform has to fit on one kind node.

### Alternatives

- **Bundle full Istio in the demo.** Closest to production, but heavy on kind and needs
  a multi-step installer.
- **One app chart with a demo flag.** Mixes demo dependencies into the charts production
  uses.
- **Keep docker-compose as the gate.** It does not test the charts.
- **minikube.** Slower to bring up than kind, locally and in CI.
- **A host-level cluster with an unprivileged devcontainer**, reached only through a
  namespace-scoped kubeconfig, and surviving rebuilds. Not built: it needs host setup
  and image delivery per platform, and the unit tests would still need Docker in the
  devcontainer. Worth revisiting once they do not.
- **Mount the host's Docker socket.** Root-equivalent on the host daemon, which is worse
  than a nested one.
- **Build our own MinIO image**, instead of Chainguard's. Puts tracking upstream MinIO
  releases on us instead of a registry that already does it.
- **Swap in SeaweedFS or Garage**, both actively published. Neither is MinIO — a
  different admin surface for no test-bed benefit over a maintained image of the same
  server and client (`mc`).
