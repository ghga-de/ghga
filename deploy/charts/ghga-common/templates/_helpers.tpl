{{- define "ghga-common.apiFullBasePath" -}}
{{ .Values.apiBasePathPrefix | empty | ternary .Values.apiBasePath (cat .Values.apiBasePathPrefix .Values.apiBasePath ) | nospace | trimSuffix "/" }}
{{- end -}}
{{- define "ghga-common.apiBasePath" -}}
{{- if .Values.apiBasePath -}}
    {{- include "ghga-common.apiFullBasePath" . -}}
{{- end -}}
{{- end -}}
{{- define "ghga-common.dbName" -}}
{{- if .Values.dbName -}}
    {{ .Values.dbNamePrefix | empty | ternary .Values.dbName (cat .Values.dbNamePrefix "-" .Values.dbName ) | nospace }}
{{- end -}}
{{- if .Values.mongodb.dbName -}}
    {{ .Values.dbNamePrefix | empty | ternary .Values.mongodb.dbName (cat .Values.dbNamePrefix "-" .Values.mongodb.dbName ) | nospace }}
{{- end -}}
{{- end -}}
{{- define "ghga-common.serviceName" -}}
{{- if .Values.serviceName -}}
    {{- .Values.serviceNamePrefix | empty | ternary .Values.serviceName (cat .Values.serviceNamePrefix "-" .Values.serviceName ) | nospace -}}
{{- end -}}
{{- end -}}
{{- define "ghga-common.serviceInstanceId" -}}
{{- if .Values.serviceInstanceId -}}
    {{ .Values.serviceInstanceIdPrefix | empty | ternary .Values.serviceInstanceId (cat .Values.serviceInstanceIdPrefix "-" .Values.serviceInstanceId ) | nospace }}
{{- end -}}
{{- end -}}

{{- define "ghga-common.volumes" -}}
{{- $volumes := list -}}
{{- if .Values.configMap.enabled -}}
{{- $configmap := dict "name" "config" "configMap" (dict "name" (include "common.names.fullname" $) "items" (list (dict "key" "config" "path" .Values.configMap.subPath))) -}}
{{- $volumes = append $volumes $configmap }}
{{- end -}}
{{- if .Values.kafkaUser.enabled }}
{{- $kafkauser := dict "name" "kafka-secret" "secret" (dict "secretName" (print .Release.Namespace "-"  (include "common.names.fullname" $)) "optional" false) }}
{{- $cluster_ca_cert := dict "name" "cluster-ca-cert" "secret" (dict "secretName" .Values.kafkaUser.caCertSecretName "optional" false) }}
{{- $volumes = append $volumes $kafkauser }}
{{- $volumes = append $volumes $cluster_ca_cert }}
{{- end }}
{{- if .Values.extraVolumes }}
{{- $volumes = concat $volumes .Values.extraVolumes }}
{{- end }}
{{- $volumes | toYaml -}}
{{- end -}}

{{- define "ghga-common.volumemounts" -}}
{{- $volumemounts := list -}}
{{- if .Values.configMap.enabled -}}
{{- $configmap := dict "name" "config" "mountPath" .Values.configMap.mountPath "subPath" .Values.configMap.subPath "readOnly" true -}}
{{- $volumemounts = append $volumemounts $configmap -}}
{{- end -}}
{{- if .Values.kafkaUser.enabled }}
{{- $volumemounts = append $volumemounts (dict "mountPath" "/kafka-secrets/" "name" "kafka-secret" "readOnly" true) }}
{{- $volumemounts = append $volumemounts (dict "mountPath" "/cluster-ca-cert/" "name" "cluster-ca-cert" "readOnly" true) }}
{{- end }}
{{- if .Values.extraVolumeMounts }}
{{- $volumemounts = concat $volumemounts .Values.extraVolumeMounts }}
{{- end }}
{{- $volumemounts | toYaml }}
{{- end -}}

{{- define "ghga-common.env-vars" -}}
{{- $envVars := .Values.configMap.envVar.enabled | ternary (append .Values.envVars (dict "name" (print .Values.configPrefix "_CONFIG_YAML" | upper) "value" .Values.configMap.mountPath)) .Values.envVars }}
{{- if .Values.serviceInstanceId.fromPodName }}
{{- $envVars = append $envVars (dict "name" (print .Values.configPrefix "_SERVICE_INSTANCE_ID" | upper) "valueFrom" (dict "fieldRef" (dict "fieldPath" "metadata.name"))) }}
{{- end }}
{{- /* Keep requests like the health probes out of traces and HTTP metrics, unless
the values set OTEL_PYTHON_EXCLUDED_URLS themselves. */}}
{{- if .Values.otelExcludedUrls }}
{{- $ownExclusions := false }}
{{- range $envVars }}{{ if eq .name "OTEL_PYTHON_EXCLUDED_URLS" }}{{ $ownExclusions = true }}{{ end }}{{ end }}
{{- if not $ownExclusions }}
{{- $envVars = append $envVars (dict "name" "OTEL_PYTHON_EXCLUDED_URLS" "value" .Values.otelExcludedUrls) }}
{{- end }}
{{- end }}
{{- /* Name the pod in the OpenTelemetry resource of traces and metrics, unless the
values set OTEL_RESOURCE_ATTRIBUTES themselves. K8S_POD_NAME comes first, since
$(VAR) only expands variables defined earlier in the list. */}}
{{- if .Values.otelResource.podName }}
{{- $ownAttributes := false }}
{{- range $envVars }}{{ if eq .name "OTEL_RESOURCE_ATTRIBUTES" }}{{ $ownAttributes = true }}{{ end }}{{ end }}
{{- if not $ownAttributes }}
{{- $envVars = append $envVars (dict "name" "K8S_POD_NAME" "valueFrom" (dict "fieldRef" (dict "fieldPath" "metadata.name"))) }}
{{- $envVars = append $envVars (dict "name" "OTEL_RESOURCE_ATTRIBUTES" "value" "k8s.pod.name=$(K8S_POD_NAME)") }}
{{- end }}
{{- end }}
{{- dict "envVars" $envVars | toYaml -}}
{{- end -}}

{{/*
Render a container probe from its values block, minus `enabled`. A probe takes one
handler, so when the values add another handler next to the default one, the
default (`.handler`) is dropped rather than rendered alongside it.
*/}}
{{- define "ghga-common.container-probe" -}}
{{- $probe := omit .probe "enabled" -}}
{{- if gt (len (pick $probe "httpGet" "tcpSocket" "exec" "grpc")) 1 -}}
{{- $probe = omit $probe .handler -}}
{{- end -}}
{{- include "common.tplvalues.render" (dict "value" $probe "context" .context) -}}
{{- end -}}
