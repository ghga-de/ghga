{{/* Transforms topic values to serivce config parameters. */}}
{{- define "ghga-common.kafkaTopicsParameters" -}}
{{- $topics := merge (.Values.global.topics | default dict) .Values.topics -}}
{{- range $key, $value := $topics -}}
{{- if $value.topic }}
  {{ $value.topic.name }}: {{ $.Values.topicPrefix | empty | ternary $value.topic.value (cat $.Values.topicPrefix "-" $value.topic.value ) | nospace }}
{{- end -}}
{{- if $value.type }}
  {{ $value.type.name }}: {{ $value.type.value }}
{{- end -}}
{{- if $value.types }}
{{- range $key, $value := $value.types }}
  {{ $value.name }}: {{ $value.value }}
{{- end }}
{{- end -}}
{{- end -}}
{{- end -}}
