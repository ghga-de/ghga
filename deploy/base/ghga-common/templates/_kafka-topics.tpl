{{/* Transforms topic values to serivce config parameters. */}}
{{- define "ghga-common.kafkaTopicsParameters" -}}
{{- if .Values.kafkaTopicsParameters }}
{{- $topics := merge (.Values.global.topics | default dict) .Values.topics -}}
{{- range $key, $value := $topics -}}
{{- if $value.topic }}
  {{- if or (not $value.topic.name) (eq $value.topic.name "wildcard") }}
  {{- continue }}
  {{- end }}
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
{{- end }}
{{- if .Values.kafkaUser.enabled }}
  kafka_ssl_password: ""
  kafka_ssl_cafile: /cluster-ca-cert/ca.crt
  kafka_ssl_certfile: /kafka-secrets/user.crt
  kafka_ssl_keyfile: /kafka-secrets/user.key
  kafka_security_protocol: SSL
{{- end }}
{{- end -}}
{{- define "ghga-common.kafkauser" -}}
---
{{- if .Values.kafkaUser.enabled -}}
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  labels:
    strimzi.io/cluster: {{ .Values.kafkaUser.clusterName }}
  name: {{ .Release.Namespace }}-{{ include "common.names.fullname" . }}
  namespace: {{ .Values.kafkaUser.clusterNamespace }}  
spec:
  authentication:
    type: tls
  authorization:
    acls:
    {{ with .Values.topics }}
    {{- range $key, $value := . }}
    {{- if eq $key "wildcard" }}
    - operation: All
      resource:
        name: '{{ $value.topic.value }}'
        patternType: literal
        type: topic
    {{- else if and (eq $key "deadLetterQueueRetry") $.Values.serviceNameConsumer }}
    - operation: All
      resource:
        name: '{{ $.Values.topicPrefix | empty | ternary (cat $.Values.serviceNameConsumer "-" $value.topic.value ) (cat $.Values.topicPrefix "-" $.Values.serviceNameConsumer "-" $value.topic.value ) | nospace }}'
        patternType: literal
        type: topic
    {{- else if and (eq $key "deadLetterQueueRetry") $.Values.serviceName }}
    - operation: All
      resource:
        name: '{{ $.Values.topicPrefix | empty | ternary (cat $.Values.serviceName "-" $value.topic.value ) (cat $.Values.topicPrefix "-" $.Values.serviceName "-" $value.topic.value ) | nospace }}'
        patternType: literal
        type: topic
    {{- else }}
    - operation: All
      resource:
        name: '{{ $.Values.topicPrefix | empty | ternary $value.topic.value (cat $.Values.topicPrefix "-" $value.topic.value ) | nospace }}'
        patternType: literal
        type: topic
    {{- end }}
    {{- end }}
    {{- end }}
    - operation: All
      resource:
        name: '*'
        patternType: literal
        type: group
    type: simple
  template:
    secret:
      metadata:
        annotations:
          reflector.v1.k8s.emberstack.com/reflection-allowed: "true"
          reflector.v1.k8s.emberstack.com/reflection-allowed-namespaces: {{ .Release.Namespace }}
          reflector.v1.k8s.emberstack.com/reflection-auto-enabled: "true"
{{- end -}}
{{- end -}}
