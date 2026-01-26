{{- define "ghga-common.networkpolicy" -}}
{{- if .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "common.names.fullname" . }}
  namespace: {{ include "common.names.namespace" . | quote }}
spec:
  podSelector:
    matchLabels:
      role: {{ include "common.names.fullname" . }}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          project: {{ include "common.names.namespace" . | quote }}
    - namespaceSelector:
        matchLabels:
          project: {{ .Values.networkPolicy.ingressNamespace | quote }}
    {{- if .Values.ports.enabled }}
    ports:
    {{- range .Values.service.ports }}
    - {{ include "common.tplvalues.render" (dict "value" (omit . "name") "context" $) | nindent 6 | trim}}
    {{- end }}
    {{- end }}
{{- end }}
{{- end }}
