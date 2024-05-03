{{- define "ghga-common.kafka-secrets-volume" -}}
{{- if .Values.kafkaSecrets.enabled -}}
- name: kafka-secret
  secret:
    secretName: {{ required "A valid .Values.kafkaSecrets.name is required!" .Values.kafkaSecrets.name }}
    optional: false
{{- end -}}
{{- end -}}
{{- define "ghga-common.kafka-secrets-volume-mount" -}}
{{- if .Values.kafkaSecrets.enabled -}}
- mountPath: {{ .Values.kafkaSecrets.mountPath | default "/kafka-secrets/" }}
  name: kafka-secret
  readOnly: true
{{- end -}}
{{- end -}}
