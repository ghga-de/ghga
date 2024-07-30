{{- define "ghga-common.serviceaccount" -}}
{{- if .Values.serviceaccount.create }}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ .Release.Name }}
  labels: {{- include "common.labels.standard" . | nindent 4 }}
    app: {{ .Release.Name }}
{{- end }}
{{- end -}}
