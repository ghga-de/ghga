{{- define "ghga-common.vaultAgentAnnotationsSingleTemplate" -}}
{{- $envPrefix := eq .Values.configPrefix "" | ternary "" (print .Values.configPrefix "_" | upper) }}
{{- include "ghga-common.vaultAgentBoilerplate" . }}
{{- if .Values.vaultAgent.secrets }}
{{- $secrets := .Values.vaultAgent.secrets -}}
{{- $stanzas := list -}}
{{- $primaryPath := "" -}}
{{- /* MongoDB connection string (env-var: folded into the single file).
       Single prefixed MONGO_DSN with the connection string inline -- the .env file is
       read as dotenv (not shell-sourced), so $VAR cross-references are NOT expanded. */ -}}
{{- with $secrets.mongodb }}
{{- if .enabled }}
{{- $path := .secretPath -}}
{{- if eq $path "" -}}
{{-   with $.Values.mongodb.service -}}
{{-     $path = list (list $.Values.cluster.name .namespace .name | join "-") "creds" $.Release.Name | join "/" -}}
{{-   end -}}
{{- end -}}
{{- $primaryPath = $path -}}
{{- $stanzas = append $stanzas (printf "{{- with secret %q -}}\n%sMONGO_DSN=%q\n{{- end }}" $path $envPrefix .connectionString) -}}
{{- end }}
{{- end }}
{{- /* Service KV pairs (env-var: folded into the single file) */ -}}
{{- with $secrets.service }}
{{- if .enabled }}
{{- $path := .secretPath -}}
{{- if eq $path "" -}}
{{-   with .pathPrefix -}}
{{-     $path = list . $.Values.environment.name ($.Values.vaultAgent.releaseNameOverwrite | default $.Release.Name) | join "/" -}}
{{-   end -}}
{{- end -}}
{{- if eq $primaryPath "" }}{{- $primaryPath = $path -}}{{- end -}}
{{- $stanzas = append $stanzas (printf "{{ with secret %q -}}\n{{ if .Data.data }}{{- range $k, $v := .Data.data }}\n%s{{ $k }}='{{ $v }}'\n{{- end }}{{- end }}{{- end }}" $path $envPrefix) -}}
{{- end }}
{{- end }}
{{- /* crypt4gh key pairs: renderToFile true -> own file+template key; false -> folded into the single file */ -}}
{{- range $name := (list "crypt4ghInternalPub" "crypt4ghInternalPriv" "crypt4ghExternalPriv") }}
{{- if dig $name "enabled" false $secrets }}
{{- $secretPath := dig $name "secretPath" "" $secrets }}
{{- $dataKey := dig $name "dataKey" "" $secrets }}
{{- $mountPath := dig $name "mountPath" "" $secrets }}
{{- $parameterName := dig $name "parameterName" "" $secrets }}
{{- if dig $name "renderToFile" false $secrets }}
vault.hashicorp.com/agent-inject-command-{{ $name }}: |
  kill -TERM $(pgrep {{ $.Values.vaultAgent.pgrepPattern }})
vault.hashicorp.com/agent-inject-file-{{ $name }}: {{ $mountPath }}
vault.hashicorp.com/agent-inject-template-{{ $name }}: |
  {{ print `{{ with secret ` ($secretPath | quote) ` -}}` }}
  {{ print `{{ index .Data.data ` ($dataKey | quote) ` }}` }}
  {{ `{{- end }}` }}
{{- else }}
{{- $stanzas = append $stanzas (printf "{{ with secret %q -}}\n%s%s='{{ index .Data.data %q }}'\n{{- end }}" $secretPath $envPrefix (upper $parameterName) $dataKey) -}}
{{- end }}
{{- end }}
{{- end }}
{{- /* generic secrets (env-var: folded into the single file) */ -}}
{{- with $secrets.generic }}
{{- range $name, $g := . }}
{{- $dk := hasKey $g "dataKey" | ternary $g.dataKey $g.parameterName -}}
{{- $stanzas = append $stanzas (printf "{{ with secret %q -}}\n%s%s='{{ index .Data.data %q }}'\n{{- end }}" $g.path $envPrefix (upper $g.parameterName) $dk) -}}
{{- end }}
{{- end }}
{{- /* optional: append arbitrary consul-template content to the combined file (raw, not tpl-processed) */ -}}
{{- with .Values.vaultAgent.singleTemplateAppend }}
{{- $stanzas = append $stanzas . -}}
{{- end }}
{{- /* emit the single combined template once, after every stanza is collected */ -}}
{{- if $stanzas }}
vault.hashicorp.com/agent-inject-command-service-secrets: |
  kill -TERM $(pgrep {{ .Values.vaultAgent.pgrepPattern }})
vault.hashicorp.com/agent-inject-secret-service-secrets: {{ $primaryPath }}
vault.hashicorp.com/agent-inject-template-service-secrets: |
{{ join "\n" $stanzas | indent 2 }}
{{- end }}
{{- end }}
{{- end -}}
