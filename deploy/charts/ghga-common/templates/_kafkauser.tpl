{{- define "ghga-common.kafkauser" -}}
{{- if .Values.kafkaUser.enabled -}}
---
apiVersion: {{ .Values.strimziApiVersion }}
kind: KafkaUser
metadata:
  labels:
    strimzi.io/cluster: {{ .Values.kafkaUser.clusterName }}
    {{- if .Values.commonLabels }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonLabels "context" $ ) | nindent 4 }}
    {{- end }}
  {{- if .Values.commonAnnotations }}
  annotations:
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonAnnotations "context" $ ) | nindent 4 }}
  {{- end }}
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
    {{- $kafkaUser := set $kafkaUser "operations" (concat $kafkaUser.operations (list "Describe" "Create") | uniq) -}}
    {{- if eq $topicKey "wildcard" }}
    {{- $kafkaUser = (merge $kafkaUser (dict "resource" (dict "name" $topicValue.topic.value))) -}}
    {{- /* The services do not support a configurable topic name or prefix at the moment for the `retry` topics. */ -}}
    {{- /* The serviceName is prefixed with the deployment name. */ -}}
    {{- else if and (eq $topicKey "deadLetterQueueRetry") $.Values.serviceNameConsumer }}
    {{- $topicValue := list $topicValue.topic.value "-" (include "ghga-common.serviceNameConsumer" $) -}}
    {{- $kafkaUser = merge $kafkaUser (dict "resource" (dict "name" (join "" $topicValue))) -}}
    {{- else if and (eq $topicKey "deadLetterQueueRetry") $.Values.serviceName }}
    {{- $topicValue := list $topicValue.topic.value "-" (include "ghga-common.serviceName" $) -}}
    {{- $kafkaUser = merge $kafkaUser (dict "resource" (dict "name" (join "" $topicValue))) -}}
    {{- else if and (eq $topicKey "deadLetterQueueRetries") $.Values.serviceName }}
    {{- $topicValue := list $topicValue.topic.value -}}
    {{- $kafkaUser = merge $kafkaUser (dict "resource" (dict "name" (join "" $topicValue))) -}}
    {{- else }}
    {{- $topicValue := $.Values.topicPrefix | empty | ternary (list $topicValue.topic.value) (list $.Values.topicPrefix "-" $topicValue.topic.value) -}}
    {{- $kafkaUser = merge $kafkaUser (dict "resource" (dict "name" (join "" $topicValue))) -}}
    {{- end }}
    {{- $topicsACL = append $topicsACL $kafkaUser -}}
    {{- end }}
    {{- include "common.tplvalues.render" (dict "value" $topicsACL "context" $) | nindent 4 }}
    {{- end }}
    {{- with .Values._consumerGroup -}}
    {{- $consumerGroupACL := list -}}
    {{- $aclEntry := hasKey . "operations" | ternary . (dict "operations" (list "Read")) -}}
    {{- $aclEntry = hasKey . "resource" | ternary (merge $aclEntry .) (merge $aclEntry (dict "resource" (dict "patternType" "literal" "type" "group" "name" (include "ghga-common.serviceName" $)))) -}}
    {{- $consumerGroupACL = append $consumerGroupACL $aclEntry -}}
    {{- include "common.tplvalues.render" (dict "value" $consumerGroupACL "context" $) | nindent 4 }}
    {{- end }}
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
