{{- define "ghga-common.vaultAgentAnnotations" -}}
vault.hashicorp.com/tls-skip-verify: "false"
vault.hashicorp.com/agent-inject: "true"
vault.hashicorp.com/agent-init-first: "true"
vault.hashicorp.com/agent-cache-enable: "true"
vault.hashicorp.com/agent-pre-populate-only: "false"
vault.hashicorp.com/agent-run-as-same-user: "true"
vault.hashicorp.com/role: "{{ .Values.vaultAgent.role }}"
vault.hashicorp.com/auth-path: "{{ .Values.vaultAgent.authPath }}"
{{- if .Values.vaultAgent.secrets -}}
{{- if .Values.vaultAgent.secrets.mongodb }}
{{- $vaultSecretPath := .Values.vaultAgent.secrets.mongodb.secretPath }}
{{- $connectionString := .Values.vaultAgent.secrets.mongodb.connectionString }}
vault.hashicorp.com/agent-inject-command-mongodb-connection-string: |
  kill -TERM $(pgrep {{ .Values.vaultAgent.secrets.mongodb.pgrepPattern }})
vault.hashicorp.com/agent-inject-secret-mongodb-connection-string: {{ $vaultSecretPath }}
vault.hashicorp.com/agent-inject-template-mongodb-connection-string: |
  {{ print `{{- with secret "` $vaultSecretPath `" -}}` }}
  export {{ .Values.configPrefix | upper }}_DB_URL="{{ $connectionString }}"
  export {{ .Values.configPrefix | upper }}_DB_CONNECTION_STR=${{ .Values.configPrefix }}_DB_URL
  {{`{{- end -}}`}}
{{- end -}}
{{- if .Values.vaultAgent.secrets.service }}
{{- $vaultSecretPath := .Values.vaultAgent.secrets.service.secretPath }}
vault.hashicorp.com/agent-inject-command-service-secrets: |
  kill -TERM $(pgrep {{ .Values.vaultAgent.secrets.service.pgrepPattern }})
vault.hashicorp.com/agent-inject-secret-service-secrets: {{ $vaultSecretPath }}
vault.hashicorp.com/agent-inject-template-service-secrets: |
  {{ print `{{ with secret "` $vaultSecretPath `" -}}` }}
  {{`{{ if .Data.data }}{{- range $k, $v := .Data.data }}`}}
  export {{ .Values.configPrefix | upper }}_{{`{{ $k }}='{{ $v }}'`}}
  {{`{{- end }}{{- end }}{{- end }}`}}
{{- end -}}
{{- end -}}
{{- end -}}

