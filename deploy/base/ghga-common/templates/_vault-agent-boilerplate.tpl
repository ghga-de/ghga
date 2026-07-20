{{- define "ghga-common.vaultAgentBoilerplate" -}}
{{/* Vault agent boilerplate */}}
{{- with .Values.vaultAgent }}
{{- with .annotations }}
{{ toYaml . }}
{{- end }}
{{- $role := .role | default (.releaseNameOverwrite | default $.Release.Name) }}
{{- with .rolePrefix }}
{{- $role = printf "%s-%s" . $role }}
{{- end }}
vault.hashicorp.com/role: "{{ $role }}"
{{- if .caCert }}
vault.hashicorp.com/ca-cert: "{{ .caCert }}"
{{- end }}
{{- if .tlsSecret }}
vault.hashicorp.com/tls-secret: "{{ .tlsSecret }}"
{{- end }}
{{- if .service }}
vault.hashicorp.com/service: "{{ .service }}"
{{- end }}
{{- if .tlsServerName }}
vault.hashicorp.com/tls-server-name: "{{ .tlsServerName }}"
{{- end }}
{{- end }}
{{- end }}
