{{- define "ghga-common.pod-labels" -}}
labels: {{- include "common.labels.standard" . | nindent 2 }}
  app: {{ .Release.Name }}
{{- if .Values.podLabels }}
{{- include "common.tplvalues.render" (dict "value" .Values.podLabels "context" $) | nindent 2 }}
{{- end }}
{{- end -}}
