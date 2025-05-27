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
    {{- include "ghga-common.apiBasePath" $ | nindent 4 }}
    {{- include "ghga-common.dbName" $ | nindent 4 }}
    {{- if eq $container.type "consumer"}}
    service_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceNameConsumer" $) "context" $) }}
    {{- include "ghga-common.serviceInstanceIdConsumer" $ | nindent 4 }}
    {{- else }}
    service_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceName" $) "context" $) }}
    {{- include "ghga-common.serviceInstanceId" $ | nindent 4 }}
    {{- end }}
{{- end }}
  parameters: |
    {{- toYaml .Values.parameters.default | nindent 4 }}
    {{- include "ghga-common.kafkaTopicsParameters" . | nindent 2 }}
    {{- include "ghga-common.apiBasePath" . | nindent 4 }}
    {{- include "ghga-common.dbName" . | nindent 4 }}
    service_name: {{ include "common.tplvalues.render" (dict "value" (include "ghga-common.serviceName" $) "context" $) }}
    {{- include "ghga-common.serviceInstanceId" . | nindent 4 }}
{{- end -}}
