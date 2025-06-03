{{- define "ghga-common.configmap" -}}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "common.names.fullname" . }}
data:
{{- range $container := .Values.containers }}
  parameters-{{ $container.type }}: |
    {{- merge (get $.Values.parameters $container.type) $.Values.parameters.default | toYaml | nindent 4 }}
    {{- include "ghga-common.kafkaTopicsParameters" $ | nindent 2 }}
    api_root_path: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.apiBasePath" $) "context" $) }}
    db_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.dbName" $) "context" $) }}
    {{- if eq $container.type "consumer"}}
    {{- if (include "ghga-common.serviceNameConsumer" $) }}
    service_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceInstanceIdConsumer" $) "context" $) }}
    {{- end }}
    service_instance_id: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceInstanceId" $) "context" $) }}
    {{- else }}
    {{- if (include "ghga-common.serviceName" $) }}
    service_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceName" $) "context" $) }}
    {{- end }}
    service_instance_id: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceInstanceId" $) "context" $) }}
    {{- end }}
{{- end }}
  parameters: |
    {{- toYaml .Values.parameters.default | nindent 4 }}
    {{- include "ghga-common.kafkaTopicsParameters" . | nindent 2 }}
    api_root_path: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.apiBasePath" $) "context" $) }}
    db_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.dbName" $) "context" $) }}
    {{- if (include "ghga-common.serviceName" $) }}
    service_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceName" $) "context" $) }}
    {{- end }}
    service_instance_id: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceInstanceId" $) "context" $) }}
{{- end -}}
