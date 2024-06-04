{{- define "ghga-common.image-pull-secrets" -}}
{{- if .Values.imagePullSecretName -}}
imagePullSecrets:
  {{- toYaml .Values.imagePullSecretName | nindent 6 }}
{{- end -}}
{{- end -}}
