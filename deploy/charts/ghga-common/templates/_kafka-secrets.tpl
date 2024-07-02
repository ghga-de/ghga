{{- define "ghga-common.kafka-secrets-volume" -}}
{{- if .Values.kafkaSecrets.enabled -}}
- name: kafka-secret
  secret:
    secretName: {{ required "A valid .Values.kafkaSecrets.kafkaUserCert.name is required!" .Values.kafkaSecrets.kafkaUserCert.name }}
    optional: false
- name: cluster-ca-cert
  secret:
    secretName: {{ .Values.kafkaSecrets.clusterCACert.name | default "kafka-cluster-ca-cert" }}
    optional: false
{{- end -}}
{{- end -}}
{{- define "ghga-common.kafka-secrets-volume-mount" -}}
{{- if .Values.kafkaSecrets.enabled -}}
- mountPath: {{ .Values.kafkaSecrets.kafkaUserCert.mountPath | default "/kafka-secrets/" }}
  name: kafka-secret
  readOnly: true
- mountPath: {{ .Values.kafkaSecrets.clusterCACert.mountPath | default "/cluster-ca-cert/" }}
  name: cluster-ca-cert
  readOnly: true
{{- end -}}
{{- end -}}
