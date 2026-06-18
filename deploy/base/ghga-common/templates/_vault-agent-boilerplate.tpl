{{- define "ghga-common.vaultAgentBoilerplate" -}}
{{/* Vault agent boilerplate */}}
{{- with .Values.vaultAgent }}
{{- .annotations | toYaml }}
{{- if .role }}
vault.hashicorp.com/role: "{{ .role }}"
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
