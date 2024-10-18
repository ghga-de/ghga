{{/* Transforms topic values to serivce config parameters. */}}
{{- define "ghga-common.kafkaTopicsParameters" -}}
{{- $topics := merge (.Values.globals.topics | default dict) .Values.topics -}}
{{- range $key, $value := $topics -}}
{{- if $value.topic }}
  {{ $value.topic.name }}: {{ $value.topic.value }}
{{- end -}}
{{- if $value.type }}
  {{ $value.type.name }}: {{ $value.type.value }}
{{- end -}}
{{- end -}}
{{- end -}}
