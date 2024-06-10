{{- define "ghga-common.pod-extra-labels" -}}
{{- if .Values.podExtraLabels -}}
{{- toYaml .Values.podExtraLabels -}}
{{- end -}}
{{- end -}}
