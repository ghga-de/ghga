{{- define "ghga-common.mapping" -}}
{{ if .Values.mapping.enabled }}
apiVersion: getambassador.io/v3alpha1
kind: Mapping
metadata:
  name: {{ include "common.names.fullname" . }}
  namespace: {{ include "common.names.namespace" . | quote }}
spec:
  ambassador_id: {{ .Values.mapping.ambassador_id }}
  service: "{{ include "common.names.fullname" . }}:{{ .Values.mapping.port }}"
  hostname: {{ .Values.mapping.hostname }}
  prefix: {{ .Values.apiBasePath | empty | ternary .Values.mapping.prefix (include "ghga-common.apiFullBasePath" .) }}
  rewrite: {{ .Values.mapping.rewrite }}
  timeout_ms: {{ .Values.mapping.timeout_ms }}
{{ end }}
{{- end -}}
