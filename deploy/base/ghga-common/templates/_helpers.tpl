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
{{- dict "envVars" $envVars | toYaml -}}
{{- end -}}