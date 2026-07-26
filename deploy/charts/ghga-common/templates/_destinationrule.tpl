{{- define "ghga-common.destinationrule" -}}
{{- if .Values.destinationRule.enabled }}
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: {{ include "common.names.fullname" . }}
  namespace: {{ include "common.names.namespace" . | quote }}
  labels: {{- include "common.labels.standard" . | nindent 4 }}
    {{- if .Values.commonLabels }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonLabels "context" $ ) | nindent 4 }}
    {{- end }}
  {{- if or .Values.service.annotations .Values.commonAnnotations }}
  annotations:
    {{- if .Values.service.annotations }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.service.annotations "context" $ ) | nindent 4 }}
    {{- end }}
    {{- if .Values.commonAnnotations }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonAnnotations "context" $ ) | nindent 4 }}
    {{- end }}
  {{- end }}
spec:
  host: {{ include "common.names.fullname" . }}.{{ include "common.names.namespace" . }}.svc.cluster.local
  {{- include "common.tplvalues.render" (dict "value" (omit .Values.destinationRule.spec "host") "context" $) | nindent 2 }}
{{- end -}}
{{- end -}}
