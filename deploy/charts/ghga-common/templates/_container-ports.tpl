{{/*
ghga-common.container-ports normalizes containerPorts (a name -> port map, where
port is either a bare number or {port, protocol}) into a plain list of
{name, containerPort, protocol} objects - the shape the container spec, Service,
and NetworkPolicy templates all build their own `ports:` from, so there's one
place that understands both forms of the map instead of three.

@param Root context
*/}}
{{- define "ghga-common.container-ports" -}}
{{- range $name, $port := .Values.containerPorts }}
{{- if kindIs "map" $port }}
- name: {{ $name }}
  containerPort: {{ $port.port }}
  protocol: {{ $port.protocol | default "TCP" }}
{{- else }}
- name: {{ $name }}
  containerPort: {{ $port }}
  protocol: TCP
{{- end }}
{{- end }}
{{- end -}}
