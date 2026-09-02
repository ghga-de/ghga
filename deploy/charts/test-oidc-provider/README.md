# test-oidc-provider

Test OpenID Connect provider

## Installing

```
helm install test-oidc-provider oci://registry-1.docker.io/ghga/test-oidc-provider-chart
```

## Source

Part of the [GHGA monorepo](https://github.com/ghga-de/ghga/tree/main/services/test-oidc-provider). See
[values.yaml](https://github.com/ghga-de/ghga/blob/main/deploy/charts/test-oidc-provider/values.yaml)
for the full set of configurable values.

## Service Configuration

| Name | Description | Value |
|------|-------------|-------|
| `config.host` | IP of the host. | `"127.0.0.1"` |
| `config.log_level` | The minimum log level to capture. | `"INFO"` |
| `config.service_name` | Short name of this service. NOTE: this chart's configmap.tpl always overwrites config.service_name with the value computed from `serviceName` - a value set directly under config.service_name is silently discarded. Set `serviceName` instead. | `"top"` |
| `config.service_instance_id` | String that uniquely identifies this service instance in log messages | `"default"` |
| `config.log_format` | If set, will replace JSON formatting with the specified string format. If not set, has no effect. In addition to the standard attributes, the following can also be specified: timestamp, service, instance, level, correlation_id, and details | `null` |
| `config.log_traceback` | Whether to include exception tracebacks in log messages. | `true` |
| `config.issuer` | test issuer URL | `"https://op.test/"` |
| `config.user_domain` | domain name of the home organization of the test users | `"home.org"` |
| `config.client_id` | test client ID | `"test-client"` |
| `config.redirect_url` | test redirect URL | `"https://client.test/oauth/callback"` |
| `config.valid_seconds` | default expiration time of access tokens in seconds | `3600` |
| `config.port` | Port to expose the server on the specified host | `8080` |
| `config.auto_reload` | A development feature. Set to `True` to automatically reload the server upon code changes | `false` |
| `config.workers` | Number of workers processes to run. | `1` |
| `config.api_root_path` | Root path at which the API is reachable. This is relative to the specified host and port. NOTE: this chart's configmap.tpl always overwrites config.api_root_path with the value computed from `apiBasePath` - a value set directly under config.api_root_path is silently discarded. Set `apiBasePath` instead. | `""` |
| `config.openapi_url` | Path to get the openapi specification in JSON format. This is relative to the specified host and port. | `"/openapi.json"` |
| `config.docs_url` | Path to host the swagger documentation. This is relative to the specified host and port. | `"/docs"` |
| `config.cors_allowed_origins` | A list of origins that should be permitted to make cross-origin requests. By default, cross-origin requests are not allowed. You can use ['*'] to allow any origin. | `null` |
| `config.cors_allow_credentials` | Indicate that cookies should be supported for cross-origin requests. Defaults to False. Also, cors_allowed_origins cannot be set to ['*'] for credentials to be allowed. The origins must be explicitly specified. | `null` |
| `config.cors_allowed_methods` | A list of HTTP methods that should be allowed for cross-origin requests. Defaults to ['GET']. You can use ['*'] to allow all standard methods. | `null` |
| `config.cors_allowed_headers` | A list of HTTP request headers that should be supported for cross-origin requests. Defaults to []. You can use ['*'] to allow all headers. The Accept, Accept-Language, Content-Language and Content-Type headers are always allowed for CORS requests. | `null` |
| `config.generate_correlation_id` | A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID. If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function. | `true` |

## Parameters

| Name | Description | Value |
|------|-------------|-------|
| `global.imageRegistry` | Registry override applied to every image reference in the umbrella (read by the vendored `common` library chart's `common.images.image` helper) | `""` |
| `global.imagePullSecrets` | Pull secrets applied to every workload in the umbrella, combined with each image's own `pullSecrets` below (read by the vendored `common` library chart's `common.images.renderPullSecrets` helper) | `[]` |
| `commandPrefix` | Path prefix prepended to `executable` before it's rendered into `command`/`args` | `""` |
| `commandStyle` | "shell": wrap executable+args in `command` via a shell string (needs a shell in the image). "exec": render command=[prefixed executable], args as a real argv list - for shell-less hardened runtime images. | `"exec"` |
| `executable` | Executable name and arguments (will be combined into a shell command) | `"test-oidc-provider"` |
| `executableArgs` |  | `[]` |
| `deployment.enabled` | Render the Deployment resource; disable for Job/CronJob-only charts | `true` |
| `job.enabled` | Render a one-off Job resource alongside (or instead of) the Deployment | `false` |
| `cronjobs.default.enabled` |  | `false` |
| `nameOverride` | Override just the chart-name portion of generated resource names (the vendored `common` library chart's `common.names.name` convention) | `""` |
| `fullnameOverride` | Override the entire generated resource name, bypassing the `<release>-<chart>` convention (the vendored `common` library chart's `common.names.fullname`) | `""` |
| `namespaceOverride` | Override the namespace resources render into instead of `.Release.Namespace` (the vendored `common` library chart's `common.names.namespace`) | `""` |
| `commonLabels` | Labels merged onto every rendered resource's metadata - Deployment, CronJob, Job, Service, HPA, DestinationRule, HTTPRoute, Probe, ConfigMap, ServiceAccount, NetworkPolicy, KafkaUser. No separate, narrower per-workload-only value: use service.labels below for Service/DestinationRule-only labels | `{}` |
| `commonAnnotations` | Annotations merged onto the same set of resources as commonLabels (see there); use service.annotations below for Service/DestinationRule-only annotations | `{}` |
| `image.registry` | Default image registry; overridden by global.imageRegistry when set | `"docker.io"` |
| `image.repository` | Image repository path (create_charts.py fills this in per member) | `"ghga/test-oidc-provider"` |
| `image.tag` | Image tag; left empty so it falls back to the chart's appVersion == the platform version (ADR-0004) | `""` |
| `image.digest` | Pin the image by digest instead of tag, when set (takes precedence in the vendored `common` library chart's `common.images.image` helper) | `""` |
| `image.pullPolicy` | imagePullPolicy override; null defaults to Always for a `latest` tag, IfNotPresent otherwise | `null` |
| `image.pullSecrets` | Extra pull secrets for just this image reference | `[]` |
| `replicaCount` | Deployment replica count; ignored when autoscaling.enabled | `1` |
| `revisionHistoryLimit` | Number of old ReplicaSets Kubernetes keeps around for rollback | `1` |
| `shareProcessNamespace` | Share the pod's process namespace across containers; forced true whenever vaultAgent.enabled (the agent sends signals to the app's PID) | `false` |
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
| `podAnnotations` | Annotations applied only to the Pod template; combined with any Vault Agent annotations when vaultAgent.enabled | `{}` |
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
| `containerPorts.http` |  | `8080` |
| `livenessProbe.enabled` | Render a container livenessProbe from this block (minus `enabled`) | `false` |
| `livenessProbe.tcpSocket.port` |  | `8080` |
| `livenessProbe.initialDelaySeconds` |  | `30` |
| `livenessProbe.periodSeconds` |  | `15` |
| `readinessProbe.enabled` | Render a container readinessProbe from this block (minus `enabled`) | `false` |
| `readinessProbe.tcpSocket.port` |  | `8080` |
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
| `envVars` | Extra literal env vars for the main container (the generated CONFIG_YAML env var is appended to this list when configMap.envVar.enabled) | `[]` |
| `envVarsConfigMap` | Name of a ConfigMap to load as bulk env vars via `envFrom` | `""` |
| `envVarsSecret` | Name of a Secret to load as bulk env vars via `envFrom` | `""` |
| `service.enabled` | Render the Service resource | `true` |
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
| `mongodb.service.namespace` | Together with mongodb.service.name and cluster.name, forms the Vault KV path this chart reads a dynamic MongoDB credential from | `"mongodb"` |
| `mongodb.service.name` |  | `"mongodb"` |
| `apiBasePath` | Public API path prefix; combined with apiBasePathPrefix (set by an aliasing umbrella) and injected into config.yaml as api_root_path | `"/op.test/"` |
| `serviceName` | Logical service name; combined with serviceNamePrefix and injected into config.yaml as service_name | `"test-oidc-provider"` |
| `serviceInstanceId.fromPodName` | Inject a <CONFIG_PREFIX>_SERVICE_INSTANCE_ID env var sourced from the Kubernetes Downward API (metadata.name), overriding config.service_instance_id per-pod. Env vars beat the YAML config file in hexkit config_from_yaml priority order, so this makes the value genuinely unique per replica instead of the static per-member string every service currently hardcodes in its own chart-values.yaml config block (which collides across replicas once replicaCount > 1, contradicting hexkit KafkaConfig.service_instance_id's own "uniquely identifies this instance" contract). | `false` |
| `configMap.enabled` | Render the ConfigMap holding config.yaml and mount it into the container | `true` |
| `configMap.mountPath` |  | `"/etc/config.yaml"` |
| `configMap.subPath` |  | `"config.yaml"` |
| `configMap.envVar.enabled` | Also add a `<CONFIG_PREFIX>_CONFIG_YAML` env var pointing at mountPath | `true` |
| `configPrefix` | Prefix for the generated CONFIG_YAML env var and every Vault Agent-injected env var; create_charts.py derives this automatically from the package name | `"top"` |
| `enableServiceLinks` | Standard Kubernetes field: whether to inject `<SVC>_SERVICE_HOST`-style env vars for every Service in the namespace | `true` |
| `successfulJobsHistoryLimit` | Fallback successfulJobsHistoryLimit for any `cronjobs` entry that doesn't set its own | `5` |
| `environment.name` | Identifies which environment this release belongs to; part of the Vault secret path for the "service" secrets bundle | `"default"` |
| `cluster.name` | Identifies which cluster this release belongs to; part of the Vault secret path for MongoDB credentials | `"default"` |
| `httpRoute.enabled` | Render an HTTPRoute (Gateway API, ADR-0012) routing to this service | `false` |
| `httpRoute.port` |  | `8080` |
| `httpRoute.rewritePath` | strip the base path before forwarding. Services that reconstruct their own public URLs (an OIDC discovery document, for example) need the full path instead and rely on api_root_path to route - set this to false for them. | `false` |
| `httpRoute.rules` | Extra HTTPRoute rules rendered before the generated default rule (deduplicated) | `[]` |
| `probe.enabled` | Render a Prometheus-Operator Probe CR blackbox-checking this service over HTTP | `false` |
| `probe.hostname` | Public hostname the blackbox exporter probes (combined with the API base path and healthEndpoint below to build the target URL) | `"default.ghga.dev"` |
| `healthEndpoint` | Path appended to the probe target URL (after the API base path) | `"/health"` |
| `destinationRule.enabled` | Render an Istio DestinationRule for this service | `false` |
| `networkPolicy.enabled` | Render a NetworkPolicy restricting ingress traffic to the pod | `false` |
| `networkPolicy.ingress` | Only allow traffic from namespaces labeled `ghga-ingress: allow`, on the Service's own ports | `[{"from": [{"namespaceSelector": {"matchLabels": {"ghga-ingress": "allow"}}}]}]` |
| `metricsNetworkPolicy.enabled` | Render a second, separate NetworkPolicy scoped to only the `metrics` containerPort - independent of networkPolicy above, which never covers this port regardless of its own ingress rules | `false` |
| `metricsNetworkPolicy.ingress` | Only allow traffic to the metrics port from namespaces labeled `kubernetes.io/metadata.name: monitoring` | `[{"from": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "monitoring"}}}]}]` |
| `strimziApiVersion` | apiVersion used for the rendered Strimzi KafkaUser resource | `"kafka.strimzi.io/v1"` |
| `vaultAgent.enabled` | Inject a Vault Agent sidecar (via pod annotations) that populates secrets/env vars from Vault before/alongside the main container | `false` |
| `vaultAgent.annotations.vault.hashicorp.com/tls-skip-verify` |  | `"false"` |
| `vaultAgent.annotations.vault.hashicorp.com/agent-inject` |  | `"true"` |
| `vaultAgent.annotations.vault.hashicorp.com/agent-init-first` |  | `"true"` |
| `vaultAgent.annotations.vault.hashicorp.com/agent-cache-enable` |  | `"true"` |
| `vaultAgent.annotations.vault.hashicorp.com/agent-pre-populate-only` |  | `"false"` |
| `vaultAgent.annotations.vault.hashicorp.com/agent-run-as-same-user` |  | `"true"` |
| `vaultAgent.role` | Vault auth role to assume; defaults to the release name when empty | `""` |
| `vaultAgent.rolePrefix` | Prefix prepended to the resolved role name above | `""` |
| `vaultAgent.caCert` | Path to a custom CA cert for Vault TLS verification | `""` |
| `vaultAgent.tlsSecret` | Kubernetes secret providing the Vault Agent's TLS material | `""` |
| `vaultAgent.service` | Override the Vault service address the agent talks to | `""` |
| `vaultAgent.tlsServerName` | TLS server name override for the Vault connection | `""` |
| `vaultAgent.pgrepPattern` | Process name the Agent's "kill -TERM" hook searches for to restart the app on secret rotation | `"python"` |
| `vaultAgent.secrets.generic` | Arbitrary Vault KV paths to inject as individual env vars, keyed by name; each entry needs path/parameterName (and optionally dataKey) | `{}` |
| `vaultAgent.secrets.mongodb.enabled` | Inject a MongoDB connection string built from a Vault-issued dynamic credential | `false` |
| `vaultAgent.secrets.mongodb.secretPath` | Vault KV path to read the credential from; computed from mongodb.service.{namespace,name} + cluster.name when empty | `""` |
| `vaultAgent.secrets.mongodb.connectionString` | Connection-string template; {{username}}/{{password}} are substituted by Vault's own templating, not Helm's | `"mongodb://{{username}}:{{password}}@mongodb:27017/admin"` |
| `vaultAgent.secrets.service.enabled` | Inject every key/value pair from one Vault secret as env vars | `false` |
| `vaultAgent.secrets.service.secretPath` | Vault KV path to read from; computed from pathPrefix + environment.name + the release name when empty | `""` |
| `vaultAgent.secrets.service.pathPrefix` |  | `"operational-secrets/data/unique/apps/archive"` |
| `vaultAgent.secrets.crypt4ghInternalPub.enabled` | Inject GHGA's shared internal Crypt4GH public key | `false` |
| `vaultAgent.secrets.crypt4ghInternalPub.secretPath` |  | `"operational-secrets/data/shared/managed-keys/crypt4gh-internal"` |
| `vaultAgent.secrets.crypt4ghInternalPub.mountPath` | Where to write the key when renderToFile is true | `"/keys/crypt4gh-internal/crypt4gh.pub"` |
| `vaultAgent.secrets.crypt4ghInternalPub.dataKey` | Field name to read within the Vault secret | `"crypt4gh.pub"` |
| `vaultAgent.secrets.crypt4ghInternalPub.renderToFile` | true: write to mountPath as a file. false: inject as an env var named parameterName instead | `true` |
| `vaultAgent.secrets.crypt4ghInternalPub.parameterName` |  | `"CRYPT4GH_PUBLIC_KEY"` |
| `vaultAgent.secrets.crypt4ghInternalPriv.enabled` | Inject GHGA's shared internal Crypt4GH private key (same fields as crypt4ghInternalPub above) | `false` |
| `vaultAgent.secrets.crypt4ghInternalPriv.secretPath` |  | `"operational-secrets/data/shared/managed-keys/crypt4gh-internal"` |
| `vaultAgent.secrets.crypt4ghInternalPriv.mountPath` |  | `"/keys/crypt4gh-internal/crypt4gh.sec"` |
| `vaultAgent.secrets.crypt4ghInternalPriv.dataKey` |  | `"crypt4gh.sec"` |
| `vaultAgent.secrets.crypt4ghInternalPriv.renderToFile` |  | `true` |
| `vaultAgent.secrets.crypt4ghInternalPriv.parameterName` |  | `"CRYPT4GH_PRIVATE_KEY"` |
| `vaultAgent.secrets.crypt4ghExternalPriv.enabled` | Inject GHGA's shared external-facing Crypt4GH private key (same fields as crypt4ghInternalPub above) | `false` |
| `vaultAgent.secrets.crypt4ghExternalPriv.secretPath` |  | `"operational-secrets/data/shared/managed-keys/crypt4gh-external"` |
| `vaultAgent.secrets.crypt4ghExternalPriv.mountPath` |  | `"/keys/crypt4gh-external/crypt4gh.sec"` |
| `vaultAgent.secrets.crypt4ghExternalPriv.dataKey` |  | `"crypt4gh.sec"` |
| `vaultAgent.secrets.crypt4ghExternalPriv.renderToFile` |  | `true` |
| `vaultAgent.secrets.crypt4ghExternalPriv.parameterName` |  | `"CRYPT4GH_PRIVATE_KEY"` |
