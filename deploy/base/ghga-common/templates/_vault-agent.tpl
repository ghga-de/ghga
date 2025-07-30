{{- define "ghga-common.vaultAgentAnnotations" -}}
{{/* Vault agent boilerplate */}}
{{- $envPrefix := eq .Values.configPrefix "" | ternary "" (print .Values.configPrefix "_" | upper) }}
{{- .Values.vaultAgent.annotations | toYaml }}
{{- if .Values.vaultAgent.role }}
vault.hashicorp.com/role: "{{ .Values.vaultAgent.role }}"
{{- else if .Values.vaultAgent.rolePrefix }}
vault.hashicorp.com/role: "{{ .Values.vaultAgent.rolePrefix }}-{{ .Release.Name }}"
{{- else }}
vault.hashicorp.com/role: "{{ .Release.Name }}"
{{- end }}
{{- if .Values.vaultAgent.authMethod }}
{{- end }}
{{- if .Values.vaultAgent.secrets -}}
{{/* Template to inject MongoDB connection string derived from Vault database engine */}}
{{- if .Values.vaultAgent.secrets.mongodb }}
{{- if .Values.vaultAgent.secrets.mongodb.enabled }}
{{- $vaultSecretPath := "" }}
{{- if ne .Values.vaultAgent.secrets.mongodb.secretPath "" }}
{{- $vaultSecretPath = .Values.vaultAgent.secrets.mongodb.secretPath }}
{{- else }}
{{- with .Values.mongodb.service }}
{{- $vaultSecretPath = list (list $.Values.cluster.name .namespace .name | join "-") "creds" $.Release.Name | join "/" }}
{{- end }}
{{- end }}
{{- $connectionString := .Values.vaultAgent.secrets.mongodb.connectionString }}
vault.hashicorp.com/agent-inject-command-mongodb-connection-string: |
  kill -TERM $(pgrep {{ .Values.vaultAgent.pgrepPattern }})
vault.hashicorp.com/agent-inject-secret-mongodb-connection-string: {{ $vaultSecretPath }}
vault.hashicorp.com/agent-inject-template-mongodb-connection-string: |
  {{ print `{{- with secret "` $vaultSecretPath `" -}}` }}
  export {{  $envPrefix }}{{ .Values.vaultAgent.secrets.mongodb.parameterName | default "DB_URL"}}="{{ $connectionString }}"
  export {{  $envPrefix }}DB_CONNECTION_STR=${{ $envPrefix }}{{ .Values.vaultAgent.secrets.mongodb.parameterName | default "DB_URL"}}
  export {{  $envPrefix }}MONGO_DSN=${{ $envPrefix }}{{ .Values.vaultAgent.secrets.mongodb.parameterName | default "DB_URL"}}
  {{`{{- end -}}`}}
{{- end -}}
{{- end -}}

{{/* Template which injects all KV pairs into the pod's environment */}}
{{- if .Values.vaultAgent.secrets.service }}
{{- if .Values.vaultAgent.secrets.service.enabled }}
{{- $vaultSecretPath := "" }}
{{- if ne .Values.vaultAgent.secrets.service.secretPath "" }}
{{- $vaultSecretPath = .Values.vaultAgent.secrets.service.secretPath }}
{{- else }}
{{- with .Values.vaultAgent.secrets.service.pathPrefix }}
{{- $vaultSecretPath = list . $.Values.environment.name ( $.Values.vaultAgent.releaseNameOverwrite | default $.Release.Name ) | join "/" }}
{{- end }}
{{- end }}
vault.hashicorp.com/agent-inject-command-service-secrets: |
  kill -TERM $(pgrep {{ .Values.vaultAgent.pgrepPattern }})
vault.hashicorp.com/agent-inject-secret-service-secrets: {{ $vaultSecretPath }}
vault.hashicorp.com/agent-inject-template-service-secrets: |
  {{ print `{{ with secret "` $vaultSecretPath `" -}}` }}
  {{`{{ if .Data.data }}{{- range $k, $v := .Data.data }}`}}
  export {{  $envPrefix }}{{`{{ $k }}='{{ $v }}'`}}
  {{`{{- end }}{{- end }}{{- end }}`}}
{{- end -}}
{{- end -}}

{{/* Templates for key pairs, can be either rendered to a file or an environment variable */}}
{{- $secrets := list "crypt4ghInternalPub" "crypt4ghInternalPriv" "crypt4ghExternalPriv" }}
{{- range $secretName := $secrets }}
  {{- $enabled := dig  $secretName "enabled" "" $.Values.vaultAgent.secrets}}
  {{- if $enabled }}
    {{- $vaultSecretPath := dig $secretName "secretPath" "" $.Values.vaultAgent.secrets }}
    {{- $mountPath := dig $secretName "mountPath" "" $.Values.vaultAgent.secrets }}
    {{- $dataKey := dig $secretName "dataKey" "" $.Values.vaultAgent.secrets }}
    {{- $renderToFile := dig $secretName "renderToFile" "" $.Values.vaultAgent.secrets }}
    {{- $parameterName := dig $secretName "parameterName" "" $.Values.vaultAgent.secrets }}
  {{- if $renderToFile }}
vault.hashicorp.com/agent-inject-file-{{ $secretName }}: {{ $mountPath }}
vault.hashicorp.com/agent-inject-template-{{ $secretName }}: |
  {{ print `{{ with secret ` ($vaultSecretPath | quote)  ` -}}` }}
  {{ print `{{ index .Data.data ` ($dataKey | quote) ` }}` }}
  {{ `{{- end }}` }}
  {{- else }}
vault.hashicorp.com/agent-inject-template-{{ $secretName }}: |
  {{ print `{{ with secret ` ($vaultSecretPath | quote)  ` -}}` }}
  export {{  $envPrefix }}{{ $parameterName | upper }}_='{{ print `{{ index .Data.data ` ($dataKey | quote) ` }}` }}'
  {{ `{{- end }}` }}
  {{- end }}
vault.hashicorp.com/agent-inject-command-{{ $secretName }}: |
  kill -TERM $(pgrep {{ $.Values.vaultAgent.pgrepPattern }})
vault.hashicorp.com/agent-inject-secret-{{ $secretName }}: {{ $vaultSecretPath }}
  {{- end }}
{{- end }}

{{- end -}}

{{/* Template which injects all KV pairs into the pod's environment */}}
{{- if .Values.vaultAgent.secrets.generic }}
{{- range $secretName, $secret := .Values.vaultAgent.secrets.generic }}
{{- $vaultSecretPath := $secret.path }}
{{- $mountPath := $secret.mountPath }}
{{- $dataKey := $secret.dataKey }}
{{- $parameterName := $secret.parameterName }}
vault.hashicorp.com/agent-inject-command-{{ $secretName }}: |
  kill -TERM $(pgrep {{ $.Values.vaultAgent.pgrepPattern }})
vault.hashicorp.com/agent-inject-secret-{{ $secretName }}: {{ $vaultSecretPath }}
vault.hashicorp.com/agent-inject-template-{{ $secretName }}: |
  {{ print `{{ with secret ` ($vaultSecretPath | quote)  ` -}}` }}
  export {{ $envPrefix }}{{ $parameterName | upper }}='{{ print `{{ index .Data.data ` (hasKey $secret "dataKey" | ternary $secret.dataKey $secret.parameterName | quote) ` }}` }}'
  {{ `{{- end }}` }}
{{- end -}}
{{- end -}}
{{- end -}}
