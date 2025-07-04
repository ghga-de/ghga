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
    {{- with .Values._topics -}}
    {{- $topicsACL := list -}}
    {{- range $topicKey, $topicValue := . }}
    {{- $kafkaUser := hasKey $topicValue "kafkaUser" | ternary (get $topicValue "kafkaUser") dict -}}
    {{- $kafkaUser := hasKey $kafkaUser "operations" | ternary $kafkaUser (merge $kafkaUser (dict "operations" (list "All"))) -}}
    {{- $kafkaUser := hasKey $kafkaUser "resource" | ternary $kafkaUser (merge $kafkaUser (dict "resource" (dict "patternType" "literal" "type" "topic"))) -}}
    {{- $kafkaUser := set $kafkaUser "operations" (append $kafkaUser.operations "Describe" | uniq) -}}
    {{- if eq $topicKey "wildcard" }}
    {{- $kafkaUser = (merge $kafkaUser (dict "resource" (dict "name" $topicValue.topic.value))) -}}
    {{- /* The services do not support a configurable topic name or prefix at the moment for the `retry` topics. */ -}}
    {{- /* The serviceName is prefixed with the deployment name. */ -}}
    {{- else if and (eq $topicKey "deadLetterQueueRetry") $.Values.serviceNameConsumer }}
    {{- $topicValue := $.Values.topicPrefix | empty | ternary (list $topicValue.topic.value "-" (include "ghga-common.serviceNameConsumer" $)) (list $.Values.topicPrefix "-" $topicValue.topic.value "-" (include "ghga-common.serviceNameConsumer" $)) -}}
    {{- $kafkaUser = merge $kafkaUser (dict "resource" (dict "name" (join "" $topicValue))) -}}
    {{- else if and (eq $topicKey "deadLetterQueueRetry") $.Values.serviceName }}
    {{- $topicValue := $.Values.topicPrefix | empty | ternary (list $topicValue.topic.value "-" (include "ghga-common.serviceName" $)) (list $.Values.topicPrefix "-" $topicValue.topic.value "-" (include "ghga-common.serviceName" $)) -}}
    {{- $kafkaUser = merge $kafkaUser (dict "resource" (dict "name" (join "" $topicValue))) -}}
    {{- else }}
    {{- $topicValue := $.Values.topicPrefix | empty | ternary (list $topicValue.topic.value) (list $.Values.topicPrefix "-" $topicValue.topic.value) -}}
    {{- $kafkaUser = merge $kafkaUser (dict "resource" (dict "name" (join "" $topicValue))) -}}
    {{- end }}
    {{- $topicsACL = append $topicsACL $kafkaUser -}}
    {{- end }}
    {{- include "common.tplvalues.render" (dict "value" $topicsACL "context" $) | nindent 4 }}
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