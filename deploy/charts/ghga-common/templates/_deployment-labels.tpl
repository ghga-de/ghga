{{- define "ghga-common.deployment-labels" -}}
labels:
  app: {{ .Release.Name }}
{{- include "common.labels.standard" . | nindent 2 }}
{{- if .Values.labels }}
{{- include "common.tplvalues.render" ( dict "value" .Values.labels "context" $ ) | nindent 2 }}
{{- end }}
{{- if .Values.commonLabels }}
{{- include "common.tplvalues.render" ( dict "value" .Values.commonLabels "context" $ ) | nindent 2 }}
{{- end }}
{{- end -}}
