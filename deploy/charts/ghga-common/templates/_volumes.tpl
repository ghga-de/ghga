{{- define "ghga-common.volumes" -}}
{{- if .Values.kafkaSecrets.enabled -}}
{{- include "ghga-common.kafka-secrets-volume" . -}}
{{- end -}}
{{- end -}}
{{- define "ghga-common.volume-mounts" -}}
{{- if .Values.kafkaSecrets.enabled -}}
{{- include "ghga-common.kafka-secrets-volume-mount" . -}}
{{- end -}}
{{- end -}}
