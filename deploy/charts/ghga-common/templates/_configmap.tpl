{{- define "ghga-common.configmap" -}}
{{- if .Values.configMap.enabled -}}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "common.names.fullname" . }}
  namespace: {{ include "common.names.namespace" . | quote }}
  labels: {{- include "common.labels.standard" . | nindent 4 }}
    {{- if .Values.commonLabels }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonLabels "context" $ ) | nindent 4 }}
    {{- end }}
  {{- if .Values.commonAnnotations }}
  annotations:
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonAnnotations "context" $ ) | nindent 4 }}
  {{- end }}
data:
  config: |
    {{- $config := .Values.config -}}
    {{- $config := omit $config "db_name" "api_root_path" "service_name" -}}
    {{- $config := merge $config (include "ghga-common.kafkaTopicsParameters" $ | fromYaml) -}}
    {{- if (include "ghga-common.apiBasePath" $) }}
    {{- $config := merge $config (dict "api_root_path" (include "ghga-common.apiBasePath" $)) -}}
    {{- end }}
    {{- if (include "ghga-common.dbName" $) }}
    {{- $config := merge $config (dict "db_name" (include "ghga-common.dbName" $)) -}}
    {{- end }}
    {{- if (include "ghga-common.serviceName" $) }}
    {{- $config := merge $config (dict "service_name" (include "ghga-common.serviceName" $)) -}}
    {{- end }}

    {{- $config | toYaml | nindent 4 }}
{{- end -}}
{{- end -}}
