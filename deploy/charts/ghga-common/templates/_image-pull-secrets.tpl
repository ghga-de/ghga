{{- define "ghga-common.image-pull-secrets" -}}
{{- if .Values.imagePullSecretNames -}}
imagePullSecrets:
  {{ toYaml .Values.imagePullSecretNames }}
{{- end -}}
{{- end -}}
