{{/* Transforms topic values to serivce config parameters. */}}
{{- define "ghga-common.kafkaTopicsParameters" -}}
{{- if .Values.kafkaTopicsParameters }}
{{- $topics := merge (.Values.global._topics | default dict) .Values._topics -}}
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
    {{ with .Values._topics }}
    {{- range $topicKey, $topicValue := . }}
    {{- $kafkaUser := hasKey $topicValue "kafkaUser" | ternary (get $topicValue "kafkaUser") dict -}}
    {{- $kafkaUser := hasKey $kafkaUser "operations" | ternary $kafkaUser (merge $kafkaUser (dict "operations" (list "ALL"))) -}}
    {{- $kafkaUser := hasKey $kafkaUser "patternType" | ternary $kafkaUser (merge $kafkaUser (dict "patternType" "literal")) -}}
    {{- $kafkaUser := hasKey $kafkaUser "type" | ternary $kafkaUser (merge $kafkaUser (dict "type" "topic")) -}}
    {{- if eq $topicKey "wildcard" }}
    - resource:
        name: '{{ $topicValue.topic.value }}'
      {{- include "common.tplvalues.render" (dict "value" $kafkaUser "context" $) | nindent 8 }}
    {{- else if and (eq $topicKey "deadLetterQueueRetry") $.Values.serviceNameConsumer }}
    - resource:
        name: '{{ $.Values.topicPrefix | empty | ternary (cat $.Values.serviceNameConsumer "-" $topicValue.topic.value) (cat $.Values.topicPrefix "-" $.Values.serviceNameConsumer "-" $topicValue.topic.value) | nospace }}'
      {{- include "common.tplvalues.render" (dict "value" $kafkaUser "context" $) | nindent 8 }}
    {{- else if and (eq $topicKey "deadLetterQueueRetry") $.Values.serviceName }}
      resource:
        name: '{{ $.Values.topicPrefix | empty | ternary (cat $.Values.serviceName "-" $topicValue.topic.value ) (cat $.Values.topicPrefix "-" $.Values.serviceName "-" $topicValue.topic.value) | nospace }}'
      {{- include "common.tplvalues.render" (dict "value" $kafkaUser "context" $) | nindent 8 }}
    {{- else }}
    - resource:
        name: '{{ $.Values.topicPrefix | empty | ternary $topicValue.topic.value (cat $.Values.topicPrefix "-" $topicValue.topic.value ) | nospace }}'
      {{- include "common.tplvalues.render" (dict "value" $kafkaUser "context" $) | nindent 8 }}
    {{- end }}
    {{- end }}
    {{- end }}
    - operations:
      - All
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