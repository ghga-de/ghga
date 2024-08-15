{{- define "ghga-common.configmap" -}}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}
data:
{{- if .Values.parameters -}}
{{/* Use rest and consumer parameters for configmap */}}
{{- if or .Values.parameters.rest .Values.parameters.consumer }}
{{- if .Values.parameters.rest }}
  parameters-rest: |
    {{- merge .Values.parameters.rest .Values.parameters.default | toYaml | nindent 4 }}
{{- end -}}
{{- if .Values.parameters.consumer }}
  parameters-consumer: |
    {{- merge .Values.parameters.consumer .Values.parameters.default | toYaml | nindent 4 }}
{{- end -}}
{{/* Create default parameter configmap */}}
{{- else if .Values.parameters.default }}
  parameters: |
    {{- toYaml .Values.parameters.default | nindent 4 }}
{{- else }}
  parameters: |
    {{- toYaml .Values.parameters | nindent 4 }}
{{- end -}}
{{- end -}}
{{- end -}}
