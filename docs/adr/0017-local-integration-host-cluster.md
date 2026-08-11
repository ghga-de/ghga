# ADR-0017 — Local integration runs on a host-level cluster; no DinD/DooD in the devcontainer

- **Status:** Accepted (amends [ADR-0009](0009-testbed-kind-minikube.md)'s local story;
  amended 2026-07-27 and 2026-08-11 — see below)
- **Date:** 2026-07-10
- **Deciders:** Leon Kuchenbecker

> **Amendment (2026-08-11) — naming only, no decision changed.** The 2026-07-27
> amendment described its loop in terms of OrbStack on macOS. Nothing about it is
> specific to that runtime, so the product names are gone from this ADR and from the
> deployment comments; OrbStack is supported, not required. What the loop does require is
> that the devcontainer's host networking reaches the browser on the host computer:
> Docker Engine on Linux provides that directly, since the container shares the host's
> namespace; Docker Desktop (whatever the host OS) needs Settings > Resources > Network >
> "Enable host networking", because its VM otherwise forwards only published ports and
> port 80 never leaves it; OrbStack forwards host-network ports unprompted. Getting this
> wrong presents as a connection refused in the browser while the port listens correctly
> inside the container — see `.devcontainer/devcontainer.json`. The scope of the
> 2026-07-27 amendment and every constraint in the Decision section below stand unchanged.

> **Amendment (2026-07-27):** on single-user hosts, the *fast iteration loop*
> runs **kind inside the devcontainer's inner docker daemon** instead: with the
> devcontainer on host networking, the kind-published gateway NodePort binds where the
> browser on the host computer reaches it as a bare localhost (verified
> empirically, browser included), image visibility is solved by `kind load` from the
> same daemon, and the loop is identical to CI's kind path. This trades the
> rebuild-persistence and resource-isolation goals of the host cluster for a
> zero-host-setup, fully in-container loop; the host-level cluster remains the
> target for persistent, closer-to-real local use once the demo stabilises. The
> DinD disk/memory pressure caveats apply (see the docker-prune tooling).

## Context

ADR-0009 chose kind (CI) / minikube (local) but left open *where* the local cluster runs. The
interim setup ran Docker-in-Docker inside the devcontainer, which has two problems:

- **Security.** The DinD feature makes the devcontainer privileged; any code executing inside it
  (dependencies, tests, agent tooling) is one step from root on the VM kernel — on native Linux,
  the host kernel.
- **Fragility.** Nested daemons caused a whole class of networking bugs (bridge-gateway
  advertised listeners, TLS cert SANs, mocked-host lists) that cost real debugging time, and the
  cluster/images die with every container rebuild.

## Decision

- **The local integration cluster runs on the host, outside the devcontainer**: minikube, or
  whatever single-node Kubernetes the host's container runtime offers (rootless podman driver
  where it works). CI keeps
  kind on the runner (unchanged from ADR-0009).
- **No DinD/DooD for the integration path.** The devcontainer stays unprivileged and mounts no
  docker socket; it interacts with the cluster only as an API client (`kubectl`, `helm`, the
  testbed suite).
- **The devcontainer gets a namespace-scoped kubeconfig, not cluster-admin.** The cluster
  bootstrap creates a ServiceAccount bound to the testbed namespace and enables Pod Security
  Admission on it. (A cluster-admin kubeconfig would be root-on-node-equivalent via a privileged
  pod — the scoped credential is what makes the security argument real.) The API server cert
  must be valid for the name the container uses (e.g. minikube
  `--apiserver-names=host.docker.internal`).
- **Images are built next to the cluster, not in the devcontainer**, and delivered without a
  registry:

  | Platform | Cluster | Image path |
  |---|---|---|
  | Runtime with built-in k8s (e.g. OrbStack) | that runtime's k8s | shared image store — locally built images are directly visible to it |
  | Linux / WSL2 | minikube | `minikube image build` / `minikube image load` |
  | CI | kind | runner `docker build` + `kind load image-archive` |

  Charts use `imagePullPolicy: IfNotPresent` with deterministic local tags. Host-side build
  steps are wrapped in `just` recipes and documented as host-side.
- **Affected-only builds + a baseline** keep the image pipeline tractable: rebuild what a change
  touches; take the rest from cache (shared `docker/Dockerfile`, one uv build layer across all
  services) or from the last released tags once the monorepo publishes.

## Consequences

- The dev environment spans host + container: a documented host-side bootstrap step
  (start/enable cluster, build images) replaces "everything inside the devcontainer".
- The DinD networking bug class disappears from the integration path, and the cluster (and its
  image store) survives devcontainer rebuilds.
- **Component tests still use DinD for now** (testcontainers need a daemon), so the
  devcontainer keeps the feature until in-memory/lightweight providers in `hexkit` make the
  container-based fixtures optional. The security posture fully improves only when that lands.
- Not adopted (yet), revisit if host-side builds prove annoying: in-cluster BuildKit
  (`docker buildx` kubernetes driver) + minikube registry addon would allow daemonless builds
  driven from the devcontainer; Tilt/Skaffold would give a watch→build→deploy inner loop.

## Alternatives considered

- **Keep DinD (kind inside the devcontainer).** Rejected: privileged container, nested-daemon
  fragility, nothing survives rebuilds.
- **DooD (mount the host docker socket).** Rejected: socket access is root-equivalent on the
  host daemon — strictly worse than a scoped kubeconfig.
- **Remote/shared dev cluster.** Rejected for now: heavier ops, needs per-dev isolation and
  connectivity; the local cluster keeps the loop offline-capable.
