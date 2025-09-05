{{- define "ghga-common.configmap" -}}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "common.names.fullname" . }}
  namespace: {{ include "common.names.namespace" . | quote }}
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
