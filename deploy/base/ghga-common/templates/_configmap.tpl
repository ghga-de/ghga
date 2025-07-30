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
    {{- $config | toYaml | nindent 4 }}
    {{- include "ghga-common.kafkaTopicsParameters" $ | nindent 2 }}
    {{- if (include "ghga-common.apiBasePath" $) }}
    api_root_path: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.apiBasePath" $) "context" $) }}
    {{- end }}
    {{- if (include "ghga-common.dbName" $) }}
    db_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.dbName" $) "context" $) }}
    {{- end }}
    {{- if (include "ghga-common.serviceName" $) }}
    service_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceName" $) "context" $) }}
    {{- end }}
{{- end -}}
