{{- define "ghga-common.default-rule" -}}
{{- if .Values.httpRoute.enabled -}}
matches:
- path:
    type: PathPrefix
    value: {{ include "ghga-common.apiFullBasePath" . | default "/" }}
filters:
- type: URLRewrite
  urlRewrite:
    path:
      type: ReplacePrefixMatch
      replacePrefixMatch: /
backendRefs:
- name:  {{ include "common.names.fullname" . }}
  port: {{ .Values.httpRoute.port }}
  weight: 100
{{- end -}}
{{- end -}}
{{- define "ghga-common.http-route" -}}
{{- if .Values.httpRoute.enabled -}}
---
apiVersion: {{ include "ghga-common.capabilities.httpRoute.apiVersion" . }}
kind: HTTPRoute
metadata:
  name: {{ include "common.names.fullname" . }}
  namespace: {{ include "common.names.namespace" . | quote }}
  labels: {{- include "common.labels.standard" . | nindent 4 }}
    app: {{ include "common.names.fullname" . }}
    {{- if .Values.labels }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.labels "context" $ ) | nindent 4 }}
    {{- end }}
    {{- if .Values.commonLabels }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonLabels "context" $ ) | nindent 4 }}
    {{- end }}
  annotations:
    {{- if .Values.annotations }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.annotations "context" $) | nindent 4 }}
    {{- end }}
    {{- if .Values.commonAnnotations }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonAnnotations "context" $ ) | nindent 4 }}
    {{- end }}
spec:
  rules: {{- include "common.tplvalues.render" ( dict "value" (append .Values.httpRoute.rules (include "ghga-common.default-rule" $ | fromYaml) | uniq) "context" $ ) | nindent 2 }}
{{- $extraSpec := omit .Values.httpRoute "enabled" "rules" "port" }}
{{- if $extraSpec }}
{{- include "common.tplvalues.render" ( dict "value" $extraSpec "context" $ ) | nindent 2 }}
{{- end }}
{{- end -}}
{{- end -}}
