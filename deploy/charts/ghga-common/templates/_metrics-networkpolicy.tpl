{{- define "ghga-common.metrics-networkpolicy" -}}
{{- if and .Values.service.enabled .Values.metricsNetworkPolicy.enabled (hasKey .Values.containerPorts "metrics") }}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "common.names.fullname" . }}-metrics
  namespace: {{ include "common.names.namespace" . | quote }}
  labels: {{- include "common.labels.standard" . | nindent 4 }}
    {{- if .Values.commonLabels }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonLabels "context" $ ) | nindent 4 }}
    {{- end }}
  {{- if .Values.commonAnnotations }}
  annotations:
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonAnnotations "context" $ ) | nindent 4 }}
  {{- end }}
spec:
  podSelector:
    matchLabels: {{- include "common.labels.matchLabels" . | nindent 6 }}
  policyTypes:
  - Ingress
  ingress:
    {{- include "common.tplvalues.render" (dict "value" .Values.metricsNetworkPolicy.ingress "context" $) | nindent 2 }}
    ports:
    {{- range (include "ghga-common.container-ports" . | fromYamlArray) }}
    {{- if eq .name "metrics" }}
    - port: {{ .containerPort }}
      protocol: {{ .protocol }}
    {{- end }}
    {{- end }}
{{- end }}
{{- end -}}
