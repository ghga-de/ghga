# auth-km-jobs

GHGA Auth Key Management Jobs - refreshes signing keys and re-encrypts secrets used by GHGA; runs as a Kubernetes Job, either regularly or on demand.

## Installing

```
helm install auth-km-jobs oci://registry-1.docker.io/ghga/auth-km-jobs-chart
```

## Source

Part of the [GHGA monorepo](https://github.com/ghga-de/ghga/tree/main/tools/auth-km-jobs). See
[values.yaml](https://github.com/ghga-de/ghga/blob/main/deploy/charts/auth-km-jobs/values.yaml)
for the full set of configurable values.

## Service Configuration

| Name | Description | Value |
|------|-------------|-------|
| `config` | The service's own configuration payload (merged with the computed kafka/api/db/service-name values below into the rendered config.yaml) | `{}` |

## Parameters

| Name | Description | Value |
|------|-------------|-------|
| `global.imageRegistry` | Registry override applied to every image reference in the umbrella (read by the vendored `common` library chart's `common.images.image` helper) | `""` |
| `global.imagePullSecrets` | Pull secrets applied to every workload in the umbrella, combined with each image's own `pullSecrets` below (read by the vendored `common` library chart's `common.images.renderPullSecrets` helper) | `[]` |
| `global.localImageIds` | Image ID per image reference, set by `just up` and `just testbed-up` for the images loaded into the kind node; a Deployment whose image is listed gets it as its `local-image-id` pod annotation, so a rebuilt image restarts its pods; empty outside the local cluster | `{}` |
| `commandPrefix` | Path prefix prepended to `executable` before it's rendered into `command`/`args` | `""` |
| `commandStyle` | "shell": wrap executable+args in `command` via a shell string (needs a shell in the image). "exec": render command=[prefixed executable], args as a real argv list - for shell-less hardened runtime images. | `"exec"` |
| `executable` | Executable name and arguments (will be combined into a shell command) | `"auth-km-jobs"` |
| `executableArgs` |  | `["refresh-int-keys"]` |
| `deployment.enabled` | Render the Deployment resource; disable for Job/CronJob-only charts | `false` |
| `job.enabled` | Render a one-off Job resource alongside (or instead of) the Deployment | `false` |
| `cronjobs.default.enabled` |  | `true` |
| `nameOverride` | Override just the chart-name portion of generated resource names (the vendored `common` library chart's `common.names.name` convention) | `""` |
| `fullnameOverride` | Override the entire generated resource name, bypassing the `<release>-<chart>` convention (the vendored `common` library chart's `common.names.fullname`) | `""` |
| `namespaceOverride` | Override the namespace resources render into instead of `.Release.Namespace` (the vendored `common` library chart's `common.names.namespace`) | `""` |
| `commonLabels` | Labels merged onto every rendered resource's metadata - Deployment, CronJob, Job, Service, HPA, DestinationRule, HTTPRoute, Probe, ConfigMap, ServiceAccount, NetworkPolicy, KafkaUser. No separate, narrower per-workload-only value: use service.labels below for Service/DestinationRule-only labels | `{}` |
| `commonAnnotations` | Annotations merged onto the same set of resources as commonLabels (see there); use service.annotations below for Service/DestinationRule-only annotations | `{}` |
| `image.registry` | Default image registry; overridden by global.imageRegistry when set | `"docker.io"` |
| `image.repository` | Image repository path (create_charts.py fills this in per member) | `"ghga/auth-km-jobs"` |
| `image.tag` | Image tag; left empty so it falls back to the chart's appVersion == the platform version (ADR-0027) | `""` |
| `image.digest` | Pin the image by digest instead of tag, when set (takes precedence in the vendored `common` library chart's `common.images.image` helper) | `""` |
| `image.pullPolicy` | imagePullPolicy override; null defaults to Always for a `latest` tag, IfNotPresent otherwise | `null` |
| `image.pullSecrets` | Extra pull secrets for just this image reference | `[]` |
| `replicaCount` | Deployment replica count; ignored when autoscaling.enabled | `1` |
| `revisionHistoryLimit` | Number of old ReplicaSets Kubernetes keeps around for rollback | `1` |
| `shareProcessNamespace` | Share the pod's process namespace across containers, e.g. so a secrets sidecar can signal the app to reload | `false` |
| `secretEnvFiles.enabled` | Source every file in `dir` into the shell before the command runs, so secrets a sidecar writes there reach the environment; needs commandStyle=shell | `false` |
| `secretEnvFiles.dir` | Directory whose files are sourced when enabled | `"/vault/secrets"` |
| `podSecurityContext.fsGroup` | Group ID Kubernetes chowns mounted volumes to | `1000` |
| `initContainers` | Extra init containers to run before the main container (the migration init container below is prepended to this list when enabled) | `[]` |
| `migrationInitContainer.enabled` | Run a dedicated init container for DB migrations before the main container starts | `false` |
| `migrationInitContainer.image` | Image for the migration init container; defaults to the main container's image when empty | `""` |
| `migrationInitContainer.imagePullPolicy` | imagePullPolicy for just the migration init container; defaults to the main container's own imagePullPolicy when unset | `null` |
| `migrationInitContainer.executable` | Executable name and arguments run inside the migration init container | `""` |
| `migrationInitContainer.executableArgs` |  | `[]` |
| `migrationInitContainer.env` | Extra env vars for just the migration init container | `[]` |
| `migrationInitContainer.resources` |  | `{}` |
| `migrationInitContainer.volumeMounts` | Extra volume mounts for just the migration init container (on top of the shared volumeMounts every container gets) | `[]` |
| `hostAliases` | Extra `/etc/hosts` entries for the pod | `[]` |
| `podLabels` | Labels applied only to the Pod template (Deployment/CronJob/Job pod spec), distinct from `labels`/`commonLabels` on the parent resource | `{}` |
| `podAnnotations` | Annotations applied only to the Pod template, e.g. the Vault Agent injection annotations the platform renders per release | `{}` |
| `podAffinityPreset` | Pod-affinity preset name (e.g. "soft"/"hard"), from the vendored `common` library chart; empty disables it | `""` |
| `podAntiAffinityPreset` | Pod-anti-affinity preset name (vendored `common` library chart convention); "soft" spreads replicas across nodes when possible | `"soft"` |
| `nodeAffinityPreset.type` | Node-affinity preset type ("soft"/"hard"), from the vendored `common` library chart; empty disables it | `""` |
| `nodeAffinityPreset.key` | Node label key to match | `""` |
| `nodeAffinityPreset.values` | Node label values to match | `[]` |
| `affinity` | Raw Kubernetes affinity spec; overrides all three presets above when set | `{}` |
| `nodeSelector` | Plain node-selector labels for pod scheduling | `{}` |
| `tolerations` | Taints the pod tolerates | `[]` |
| `topologySpreadConstraints` | Kubernetes pod topology spread constraints | `[]` |
| `priorityClassName` | PriorityClass to schedule the pod with | `""` |
| `schedulerName` | Alternate Kubernetes scheduler to use | `""` |
| `terminationGracePeriodSeconds` | Grace period before SIGKILL on pod termination | `""` |
| `updateStrategy.type` | Deployment rollout strategy (e.g. RollingUpdate/Recreate) | `"RollingUpdate"` |
| `podRestartPolicy` | Pod-level restart policy for the Deployment (Jobs/CronJobs set their own, ignoring this) | `"Always"` |
| `containerPorts` | Container ports, name -> port (bare number = TCP; {port, protocol} for anything else). Also the single source the Service's and NetworkPolicy's own `ports:` are derived from - a Service always exposes exactly what its container listens on here, so there's one map to keep in sync, not several. A map, not a list, so an overlay can add/override one named port without repeating the rest. Empty = no ports declared anywhere. | `{}` |
| `livenessProbe.enabled` | Render a container livenessProbe from this block (minus `enabled`) | `false` |
| `livenessProbe.tcpSocket.port` |  | `8080` |
| `livenessProbe.initialDelaySeconds` |  | `30` |
| `livenessProbe.periodSeconds` |  | `15` |
| `readinessProbe.enabled` | Render a container readinessProbe from this block (minus `enabled`) | `false` |
| `readinessProbe.httpGet.path` |  | `"{{ .Values.healthEndpoint }}"` |
| `readinessProbe.httpGet.port` |  | `"http"` |
| `readinessProbe.initialDelaySeconds` |  | `30` |
| `readinessProbe.periodSeconds` |  | `15` |
| `startupProbe.enabled` | Render a container startupProbe from this block (minus `enabled`) | `false` |
| `startupProbe.tcpSocket.port` |  | `8080` |
| `startupProbe.periodSeconds` |  | `10` |
| `startupProbe.failureThreshold` |  | `30` |
| `containerSecurityContext.enabled` | Render the container securityContext from this block (minus `enabled`) | `true` |
| `containerSecurityContext.runAsUser` |  | `1000` |
| `containerSecurityContext.capabilities.drop` |  | `["ALL"]` |
| `containerSecurityContext.seccompProfile.type` |  | `"RuntimeDefault"` |
| `containerSecurityContext.readOnlyRootFilesystem` |  | `true` |
| `containerSecurityContext.runAsNonRoot` |  | `true` |
| `containerSecurityContext.allowPrivilegeEscalation` |  | `false` |
| `lifecycleHooks` | Container lifecycle hooks (postStart/preStop) | `{}` |
| `resources.limits.cpu` |  | `"1500m"` |
| `resources.limits.memory` |  | `"2048M"` |
| `resources.requests.cpu` |  | `"1000m"` |
| `resources.requests.memory` |  | `"1024M"` |
| `extraVolumes` | Extra volumes for the pod (on top of the config/kafka-secret volumes this chart already renders) | `[]` |
| `extraVolumeMounts` | Extra volume mounts for the main container (on top of the shared ones every container gets) | `[]` |
| `sidecars` | Extra full container specs appended alongside the main container | `[]` |
| `envVars` | Extra literal env vars for the main container (the generated CONFIG_YAML env var is appended to this list when configMap.envVar.enabled) | `[{"name": "AUTH_KM_JOBS_TOKEN", "value": ""}, {"name": "AUTH_KM_JOBS_VAULT_ADDR", "value": "https://hashicorp-vault.vault:8200"}, {"name": "AUTH_KM_JOBS_VAULT_NAMESPACE", "value": "vault"}, {"name": "AUTH_KM_JOBS_VAULT_ROLE", "value": "auth-km-jobs-role"}]` |
| `envVarsConfigMap` | Name of a ConfigMap to load as bulk env vars via `envFrom` | `""` |
| `envVarsSecret` | Name of a Secret to load as bulk env vars via `envFrom` | `""` |
| `service.enabled` | Render the Service resource | `false` |
| `service.type` |  | `"ClusterIP"` |
| `service.labels` | Extra labels on just the Service (and DestinationRule, which shares its address) | `{}` |
| `service.annotations` | Extra annotations on just the Service (and DestinationRule, which shares its address) - e.g. cloud load-balancer or ingress-controller annotations | `{}` |
| `serviceAccount.create` | Create a dedicated ServiceAccount for this release | `true` |
| `autoscaling.enabled` | Render a HorizontalPodAutoscaler targeting the Deployment | `false` |
| `autoscaling.minReplicas` |  | `3` |
| `autoscaling.maxReplicas` |  | `5` |
| `autoscaling.targetCPU` | Target average CPU utilization percentage; omit/empty to skip this metric | `80` |
| `autoscaling.targetMemory` | Target average memory utilization percentage; omit/empty to skip this metric | `80` |
| `autoscaling.metrics` | Extra raw HPA metric entries appended after CPU/memory | `[]` |
| `topicPrefix` | Prefix prepended to every Kafka topic name this chart renders/references | `""` |
| `kafkaTopicsParameters` | Fold `_topics`/`_consumerGroup` into the rendered config.yaml as service config parameters (topic name/type env vars); set false to render topics for KafkaUser ACLs only, without also injecting them as config | `true` |
| `kafkaUser.enabled` | Render a Strimzi KafkaUser (TLS cert + ACLs from _topics/_consumerGroup) | `false` |
| `kafkaUser.clusterName` |  | `"kafka"` |
| `kafkaUser.clusterNamespace` |  | `"strimzi"` |
| `kafkaUser.caCertSecretName` | Secret holding the Kafka cluster's CA cert, mounted alongside the user's own TLS secret | `"kafka-cluster-ca-cert"` |
| `mongodb.dbName` | Database name; combined with dbNamePrefix and injected into config.yaml as db_name. NOTE: mongodb.dbName is the fallback used when the top-level dbName (set per-member, not defaulted here) is empty | `""` |
| `apiBasePath` | Public API path prefix; combined with apiBasePathPrefix (set by an aliasing umbrella) and injected into config.yaml as api_root_path | `""` |
| `serviceName` | Logical service name; combined with serviceNamePrefix and injected into config.yaml as service_name | `""` |
| `serviceInstanceId.fromPodName` | Inject a <CONFIG_PREFIX>_SERVICE_INSTANCE_ID env var sourced from the Kubernetes Downward API (metadata.name), overriding config.service_instance_id per-pod. Env vars beat the YAML config file in hexkit config_from_yaml priority order, so this makes the value genuinely unique per replica instead of the static per-member string every service currently hardcodes in its own chart-values.yaml config block (which collides across replicas once replicaCount > 1, contradicting hexkit KafkaConfig.service_instance_id's own "uniquely identifies this instance" contract). | `false` |
| `configMap.enabled` | Render the ConfigMap holding config.yaml and mount it into the container | `false` |
| `configMap.mountPath` |  | `"/etc/config.yaml"` |
| `configMap.subPath` |  | `"config.yaml"` |
| `configMap.envVar.enabled` | Also add a `<CONFIG_PREFIX>_CONFIG_YAML` env var pointing at mountPath | `false` |
| `configPrefix` | Prefix for the generated CONFIG_YAML and SERVICE_INSTANCE_ID env vars; create_charts.py derives this automatically from the package name | `"auth_km_jobs"` |
| `enableServiceLinks` | Standard Kubernetes field: whether to inject `<SVC>_SERVICE_HOST`-style env vars for every Service in the namespace | `true` |
| `successfulJobsHistoryLimit` | Fallback successfulJobsHistoryLimit for any `cronjobs` entry that doesn't set its own | `5` |
| `concurrencyPolicy` | Fallback concurrencyPolicy for any `cronjobs` entry that doesn't set its own. `Forbid` skips a run while the previous one is still active, so hung runs cannot pile up; `Allow` runs them side by side; `Replace` kills the active run | `"Forbid"` |
| `activeDeadlineSeconds` | Fallback activeDeadlineSeconds for any `cronjobs` entry that doesn't set its own: Kubernetes kills a run still active after this many seconds. null means no limit; set it per cronjob, since run times differ too much for a shared value | `null` |
| `startingDeadlineSeconds` | Fallback startingDeadlineSeconds for any `cronjobs` entry that doesn't set its own: a run that could not start within this many seconds of its schedule is skipped. null means no limit | `null` |
| `httpRoute.enabled` | Render an HTTPRoute (Gateway API, ADR-0032) routing to this service | `false` |
| `httpRoute.port` |  | `8080` |
| `httpRoute.rewritePath` | strip the base path before forwarding. Services that reconstruct their own public URLs (an OIDC discovery document, for example) need the full path instead and rely on api_root_path to route - set this to false for them. | `true` |
| `httpRoute.rules` | Extra HTTPRoute rules rendered before the generated default rule (deduplicated) | `[]` |
| `probe.enabled` | Render a Prometheus-Operator Probe CR blackbox-checking this service over HTTP | `false` |
| `probe.hostname` | Public hostname the blackbox exporter probes (combined with the API base path and healthEndpoint below to build the target URL) | `"default.ghga.dev"` |
| `healthEndpoint` | Path appended to the probe target URL (after the API base path) | `"/health"` |
| `destinationRule.enabled` | Render an Istio DestinationRule for this service | `false` |
| `networkPolicy.enabled` | Render a NetworkPolicy restricting ingress traffic to the pod | `false` |
| `networkPolicy.ingress` | Only allow traffic from namespaces labeled `ghga-ingress: allow`, on the Service's own ports | `[{"from": [{"namespaceSelector": {"matchLabels": {"ghga-ingress": "allow"}}}]}]` |
| `strimziApiVersion` | apiVersion used for the rendered Strimzi KafkaUser resource | `"kafka.strimzi.io/v1"` |
| `cronSchedule` |  | `"0 0 1 1 0"` |
