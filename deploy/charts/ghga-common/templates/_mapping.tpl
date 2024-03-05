{{- define "ghga-common.mapping" -}}
{{ if .Values.mapping.enabled }}
apiVersion: getambassador.io/v3alpha1
kind: Mapping
metadata:
  name: {{ .Release.Name }}
spec:
  ambassador_id: {{ .Values.mapping.ambassador_id }}
  service: "{{ .Release.Name }}-svc:{{ .Values.port }}"
  hostname: {{ .Values.mapping.hostname }}
  prefix: {{ .Values.mapping.prefix }}
  rewrite: {{ .Values.mapping.rewrite }}
  timeout_ms: {{ .Values.mapping.timeout_ms }}
{{ end }}
{{- end -}}
