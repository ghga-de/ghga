{{- define "ghga-common.volumes" -}}
{{- include "ghga-common.kafka-secrets-volume" . -}}
{{- end -}}
{{- define "ghga-common.volume-mounts" -}}
{{- include "ghga-common.kafka-secrets-volume-mount" . -}}
{{- end -}}
