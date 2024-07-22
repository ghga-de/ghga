{{- define "ghga-common.pod-labels" -}}
labels:
  app: {{ .Release.Name }}
{{- include "common.labels.standard" . | nindent 2 }}
{{- if .Values.podLabels }}
{{- include "common.tplvalues.render" (dict "value" .Values.podLabels "context" $) | nindent 2 }}
{{- end }}
{{- end -}}
