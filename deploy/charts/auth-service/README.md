# auth-service

Authentication adapter and services used for the GHGA data portal

## Installing

```
helm install auth-service oci://registry-1.docker.io/ghga/auth-service-chart
```

## Source

Part of the [GHGA monorepo](https://github.com/ghga-de/ghga/tree/main/services/auth-service). See
[values.yaml](https://github.com/ghga-de/ghga/blob/main/services/auth-service/values.yaml) for the
full set of configurable values.

## Parameters

| Name | Description | Value |
|------|-------------|-------|
| `global.imageRegistry` | Registry override applied to every image reference in the umbrella (read by the vendored `common` library chart's `common.images.image` helper) | `""` |
| `global.imagePullSecrets` | Pull secrets applied to every workload in the umbrella (same helper as above) | `[]` |
| `global.storageClass` | Default StorageClass for any PVC in the umbrella (a convention from the vendored `common` library chart; this chart renders no PVC template itself, so currently unused here) | `""` |
| `command` | This is the actual Kubernetes `command` field | `["sh", "-c"]` |
| `commandPrefix` | Path prefix prepended to `executable` before it's rendered into `command`/`args` | `""` |
| `commandStyle` | "shell": wrap executable+args in `command` via a shell string (needs a shell in the image). "exec": render command=[prefixed executable], args as a real argv list - for shell-less hardened runtime images. | `"exec"` |
| `executable` | Executable name and arguments (will be combined into a shell command) | `"auth-service"` |
| `executableArgs` |  | `[]` |
| `deployment.enabled` | Render the Deployment resource; disable for Job/CronJob-only charts | `true` |
| `job.enabled` | Render a one-off Job resource alongside (or instead of) the Deployment | `false` |
| `cronjobs.default.enabled` |  | `false` |
| `nameOverride` | Override just the chart-name portion of generated resource names (the vendored `common` library chart's `common.names.name` convention) | `""` |
| `fullnameOverride` | Override the entire generated resource name, bypassing the `<release>-<chart>` convention (the vendored `common` library chart's `common.names.fullname`) | `""` |
| `namespaceOverride` | Override the namespace resources render into instead of `.Release.Namespace` (the vendored `common` library chart's `common.names.namespace`) | `""` |
| `clusterDomain` | Cluster DNS domain suffix (a convention from the vendored `common` library chart); this chart's own templates hardcode `cluster.local` where they build FQDNs (e.g. mongodb.service, destinationRule), so this key isn't actually read here | `"cluster.local"` |
| `annotations` | Extra annotations added to the Deployment/CronJob/Job/HTTPRoute/Probe resources' own metadata (narrower reach than commonAnnotations below) | `{}` |
| `labels` | Extra labels added to the same resources' own metadata (narrower reach than commonLabels below) | `{}` |
| `commonLabels` | Labels merged onto nearly every rendered resource's metadata (Deployment, CronJob, Job, Service, HPA, DestinationRule, HTTPRoute, Probe) | `{}` |
| `commonAnnotations` | Annotations merged onto the same broad set of resources as commonLabels | `{}` |
| `image.registry` | Default image registry; overridden by global.imageRegistry when set | `"docker.io"` |
| `image.repository` | Image repository path (create_charts.py fills this in per member) | `"ghga/auth-service"` |
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
| `ports.enabled` | Render the container's `ports` list below | `false` |
| `ports.ports` |  | `[{"name": "http", "containerPort": 8080, "protocol": "TCP"}]` |
| `livenessProbe.enabled` | Render a container livenessProbe from this block (minus `enabled`) | `false` |
| `livenessProbe.tcpSocket.port` |  | `8080` |
| `livenessProbe.initialDelaySeconds` |  | `30` |
| `livenessProbe.periodSeconds` |  | `15` |
| `readinessProbe.enabled` | Render a container readinessProbe from this block (minus `enabled`) | `false` |
| `readinessProbe.tcpSocket.port` |  | `8080` |
| `readinessProbe.initialDelaySeconds` |  | `30` |
| `readinessProbe.periodSeconds` |  | `15` |
| `startupProbe.enabled` | Render a container startupProbe from this block (minus `enabled`) | `false` |
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
| `service.ports` |  | `[{"name": "http", "protocol": "TCP", "port": 8080, "targetPort": "http"}]` |
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
| `mongodb.dbName` | Database name; combined with dbNamePrefix and injected into config.yaml as db_name. NOTE: mongodb.dbName is the fallback used when the top-level dbName (set per-member, not defaulted here) is empty | `"auth-service"` |
| `mongodb.service.namespace` | Together with mongodb.service.name and cluster.name, forms the Vault KV path this chart reads a dynamic MongoDB credential from | `"mongodb"` |
| `mongodb.service.name` |  | `"mongodb"` |
| `apiBasePath` | Public API path prefix; combined with apiBasePathPrefix (set by an aliasing umbrella) and injected into config.yaml as api_root_path | `"/auth-ext/"` |
| `serviceName` | Logical service name; combined with serviceNamePrefix and injected into config.yaml as service_name | `"auth-service"` |
| `serviceInstanceId.fromPodName` | Inject a <CONFIG_PREFIX>_SERVICE_INSTANCE_ID env var sourced from the Kubernetes Downward API (metadata.name), overriding config.service_instance_id per-pod. Env vars beat the YAML config file in hexkit config_from_yaml priority order, so this makes the value genuinely unique per replica instead of the static per-member string every service currently hardcodes in its own chart-values.yaml config block (which collides across replicas once replicaCount > 1, contradicting hexkit KafkaConfig.service_instance_id's own "uniquely identifies this instance" contract). | `false` |
| `configMap.enabled` | Render the ConfigMap holding config.yaml and mount it into the container | `true` |
| `configMap.mountPath` |  | `"/etc/config.yaml"` |
| `configMap.subPath` |  | `"config.yaml"` |
| `configMap.envVar.enabled` | Also add a `<CONFIG_PREFIX>_CONFIG_YAML` env var pointing at mountPath | `true` |
| `config.mongo_dsn` | MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/ | `null` |
| `config.host` | IP of the host. | `"127.0.0.1"` |
| `config.enable_opentelemetry` | If set to true, this will run necessary setup code.If set to false, no setup code is run, which leaves tracing disabled. | `false` |
| `config.db_version_collection` | The name of the collection containing DB version information for this service | `null` |
| `config.migration_wait_sec` | The number of seconds to wait before checking the DB version again | `null` |
| `config.otel_trace_sampling_rate` | Determines which proportion of spans should be sampled. A value of 1.0 means all and is equivalent to the previous behaviour. Setting this to 0 will result in no spans being sampled, but this does not automatically set `enable_opentelemetry` to False. | `1.0` |
| `config.auth_topic` | The name of the topic containing auth-related events. | `null` |
| `config.second_factor_recreated_type` | The event type for recreation of the second factor for authentication | `null` |
| `config.iva_state_changed_topic` | The name of the topic containing IVA events. | `null` |
| `config.iva_state_changed_type` | The type to use for IVA state changed events. | `null` |
| `config.iva_send_code_type` | The type to use for IVA send code events. | `null` |
| `config.dataset_change_topic` | Name of the topic announcing, among other things, the list of files included in a new dataset. | `null` |
| `config.dataset_deletion_type` | Event type used for communicating dataset deletions | `null` |
| `config.dataset_upsertion_type` | Event type used for communicating dataset upsertions | `null` |
| `config.claims_collection` | Name of the collection for user claims | `"claims"` |
| `config.user_topic` | The name of the topic containing user events. | `"users"` |
| `config.users_collection` | Name of the collection for users | `"users"` |
| `config.user_tokens_collection` | Name of the collection for user tokens | `"user_tokens"` |
| `config.ivas_collection` | Name of the collection for IVAs | `"ivas"` |
| `config.service_name` | Short name of this service. NOTE: this chart's configmap.tpl always overwrites config.service_name with the value computed from `serviceName` - a value set directly under config.service_name is silently discarded. Set `serviceName` instead. | `"auth_service"` |
| `config.service_instance_id` | A string that uniquely identifies this instance across all instances of this service. This is included in log messages. | `null` |
| `config.kafka_servers` | A list of connection strings to connect to Kafka bootstrap servers. | `null` |
| `config.kafka_security_protocol` | Protocol used to communicate with brokers. Valid values are: PLAINTEXT, SSL. | `"PLAINTEXT"` |
| `config.kafka_ssl_cafile` | Certificate Authority file path containing certificates used to sign broker certificates. If a CA is not specified, the default system CA will be used if found by OpenSSL. | `""` |
| `config.kafka_ssl_certfile` | Optional filename of client certificate, as well as any CA certificates needed to establish the certificate's authenticity. | `""` |
| `config.kafka_ssl_keyfile` | Optional filename containing the client private key. | `""` |
| `config.kafka_ssl_password` | Optional password to be used for the client private key. | `""` |
| `config.generate_correlation_id` | A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID. If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function. | `true` |
| `config.kafka_max_message_size` | The largest message size that can be transmitted, in bytes, before compression. Only services that have a need to send/receive larger messages should set this. When used alongside compression, this value can be set to something greater than the broker's `message.max.bytes` field, which effectively concerns the compressed message size. | `1048576` |
| `config.kafka_compression_type` | The compression type used for messages. Valid values are: None, gzip, snappy, lz4, and zstd. If None, no compression is applied. This setting is only relevant for the producer and has no effect on the consumer. If set to a value, the producer will compress messages before sending them to the Kafka broker. If unsure, zstd provides a good balance between speed and compression ratio. | `null` |
| `config.kafka_max_retries` | The maximum number of times to immediately retry consuming an event upon failure. Works independently of the dead letter queue. | `0` |
| `config.kafka_enable_dlq` | A flag to toggle the dead letter queue. If set to False, the service will crash upon exhausting retries instead of publishing events to the DLQ. If set to True, the service will publish events to the DLQ topic after exhausting all retries | `false` |
| `config.kafka_dlq_topic` | The name of the topic used to resolve error-causing events. | `"dlq"` |
| `config.kafka_retry_backoff` | The number of seconds to wait before retrying a failed event. The backoff time is doubled for each retry attempt. | `0` |
| `config.db_name` | the name of the database located on the MongoDB server. NOTE: this chart's configmap.tpl always overwrites config.db_name with the value computed from `mongodb.dbName` - a value set directly under config.db_name is silently discarded. Set `mongodb.dbName` instead. | `"auth-db"` |
| `config.mongo_timeout` | Timeout in seconds for API calls to MongoDB. The timeout applies to all steps needed to complete the operation, including server selection, connection checkout, serialization, and server-side execution. When the timeout expires, PyMongo raises a timeout exception. If set to None, the operation will not time out (default MongoDB behavior). | `null` |
| `config.migration_max_wait_sec` | The maximum number of seconds to wait for migrations to complete before raising an error. | `null` |
| `config.log_level` | The minimum log level to capture. | `"INFO"` |
| `config.log_format` | If set, will replace JSON formatting with the specified string format. If not set, has no effect. In addition to the standard attributes, the following can also be specified: timestamp, service, instance, level, correlation_id, and details | `null` |
| `config.log_traceback` | Whether to include exception tracebacks in log messages. | `true` |
| `config.max_ivas` | Maximum number of IVAs a user can create per day and in total | `5` |
| `config.max_iva_verification_attempts` | Maximum number of verification attempts for an IVA | `10` |
| `config.max_iva_code_validity_days` | Maximum number of days an IVA verification code is valid | `7` |
| `config.max_iva_codes_per_day` | Maximum number of verification code requests per IVA and day | `3` |
| `config.auto_send_iva_code_for_types` | IVA types for which verification codes are sent automatically | `["Phone"]` |
| `config.totp_issuer` | Issuer name for TOTP provisioning URIs | `"GHGA"` |
| `config.totp_image` | URL of the PNG image provided in the TOTP provisioning URIs | `null` |
| `config.totp_algorithm` |  | `"sha1"` |
| `config.totp_digits` | Number of digits used for the TOTP code | `6` |
| `config.totp_interval` | Time interval in seconds for generating TOTP codes | `30` |
| `config.totp_tolerance` | Number of intervals to check before and after the current time | `1` |
| `config.totp_attempts_per_code` | Maximum number of attempts to verify an individual TOTP code | `3` |
| `config.totp_max_failed_attempts` | Maximum number of consecutive failed attempts to verify TOTP codes | `10` |
| `config.totp_secret_size` | Size of the Base32 encoded TOTP secrets | `32` |
| `config.totp_encryption_key` | Base64 encoded key used to encrypt TOTP secrets | `null` |
| `config.session_id_bytes` | Number of bytes to be used for a session ID. | `24` |
| `config.csrf_token_bytes` | Number of bytes to be used for a CSRF token. | `24` |
| `config.session_timeout_seconds` | Session timeout in seconds | `3600` |
| `config.session_max_lifetime_seconds` | Maximum lifetime of a session in seconds | `43200` |
| `config.auth_key` | internal public key for the auth service (key pair for auth adapter) | `null` |
| `config.auth_algs` | A list of all algorithms used for signing GHGA internal tokens. | `["ES256"]` |
| `config.auth_check_claims` | A dict of all GHGA internal claims that shall be verified. | `{"id": null, "name": null, "email": null, "iat": null, "exp": null}` |
| `config.auth_map_claims` | A mapping of claims to attributes in the GHGA auth context. | `{}` |
| `config.port` | Port to expose the server on the specified host | `8080` |
| `config.auto_reload` | A development feature. Set to `True` to automatically reload the server upon code changes | `false` |
| `config.workers` | Number of workers processes to run. | `1` |
| `config.timeout_keep_alive` | The time in seconds to keep an idle connection open for subsequent requests before closing it. This value should be higher than the timeout used by any client or reverse proxy to avoid premature connection closures. | `90` |
| `config.api_root_path` | Root path at which the API is reachable. This is relative to the specified host and port. NOTE: this chart's configmap.tpl always overwrites config.api_root_path with the value computed from `apiBasePath` - a value set directly under config.api_root_path is silently discarded. Set `apiBasePath` instead. | `""` |

> Docker Hub caps this overview at 25000 characters, so the table above stops partway through this chart's parameters. The full list, with defaults and descriptions, is in [values.schema.json](https://github.com/ghga-de/ghga/blob/main/services/auth-service/values.schema.json).
