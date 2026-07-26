{{- define "ghga-common.probe" -}}
{{- if .Values.probe.enabled -}}
apiVersion: monitoring.coreos.com/v1
kind: Probe
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
  {{- 
    $defaults := dict 
      "jobName" (include "common.names.fullname" .) 
      "prober" (dict "url" "prometheus-blackbox-exporter.monitoring.svc.cluster.local:9115" )
      "module" "http_2xx" 
      "targets" (dict "staticConfig" (dict "static" (list (print "http://" .Values.probe.hostname (include "ghga-common.apiFullBasePath" .) .Values.healthEndpoint))))
  -}}
{{- include "common.tplvalues.render" ( dict "value" (omit (merge .Values.probe $defaults) "enabled" "hostname") "context" $ ) | nindent 2 }}
{{- end -}}
{{- end -}}
