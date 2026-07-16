{{- define "ghga-common.vaultAgentBoilerplate" -}}
{{/* Vault agent boilerplate */}}
{{- with .Values.vaultAgent }}
{{- with .annotations }}
{{ toYaml . }}
{{- end }}
{{- if .role }}
{{- $role := .role }}
{{- range .roleTrimSuffixes | default (list "-consumer" "-clean-up-job") }}
{{- $role = trimSuffix . $role }}
{{- end }}
vault.hashicorp.com/role: "{{ $role }}"
{{- else if .rolePrefix }}
vault.hashicorp.com/role: "{{ .rolePrefix }}-{{ $.Release.Name }}"
{{- else }}
vault.hashicorp.com/role: "{{ $.Release.Name }}"
{{- end }}
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