{{- define "ghga-common.networkpolicy" -}}
{{- if and .Values.service.enabled .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "common.names.fullname" . }}
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
    {{- include "common.tplvalues.render" (dict "value" .Values.networkPolicy.ingress "context" $) | nindent 2 }}
    {{- /* metrics is excluded: governed only by the separate metricsNetworkPolicy */ -}}
    {{- $ports := list }}
    {{- range (include "ghga-common.container-ports" . | fromYamlArray) }}
    {{- if ne .name "metrics" }}
    {{- $ports = append $ports . }}
    {{- end }}
    {{- end }}
    {{- if $ports }}
    ports:
    {{- range $ports }}
    - port: {{ .containerPort }}
      protocol: {{ .protocol }}
    {{- end }}
    {{- end }}
{{- end }}
{{- end }}
