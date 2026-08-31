{{- define "ghga-common.networkpolicy" -}}
{{- if and .Values.service.enabled .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "common.names.fullname" . }}
  namespace: {{ include "common.names.namespace" . | quote }}
spec:
  podSelector:
    matchLabels: {{- include "common.labels.matchLabels" . | nindent 6 }}
  policyTypes:
  - Ingress
  ingress:
    {{- include "common.tplvalues.render" (dict "value" .Values.networkPolicy.ingress "context" $) | nindent 2 }}
    {{- if .Values.containerPorts }}
    ports:
    {{- range (include "ghga-common.container-ports" . | fromYamlArray) }}
    - port: {{ .containerPort }}
      protocol: {{ .protocol }}
    {{- end }}
    {{- end }}
{{- end }}
{{- end }}
