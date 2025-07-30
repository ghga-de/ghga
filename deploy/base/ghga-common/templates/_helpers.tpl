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
{{- define "ghga-common.configVolume" -}}
{{- if .Values.configMap.enabled -}}
name: config
configMap:
    name: {{ include "common.names.fullname" $ }}
    items:
    - key: config
      path: {{ .Values.configMap.subPath }}
{{- end -}}
{{- end -}}
{{- define "ghga-common.configVolumeMount" -}}
{{- if .Values.configMap.enabled -}}
name: config
mountPath: {{ .Values.configMap.mountPath }}
subPath: {{ .Values.configMap.subPath }}
readOnly: true
{{- end -}}
{{- end -}}
{{- define "ghga-common.env-vars" -}}
{{- $envVars := .Values.configMap.envVar.enabled | ternary (append .Values.envVars (dict "name" (print .Values.configPrefix "_CONFIG_YAML" | upper) "value" .Values.configMap.mountPath)) .Values.envVars }}
{{- dict "envVars" $envVars | toYaml -}}
{{- end -}}
