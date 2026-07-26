{{/*
Return the appropriate gateway apiVersion for HTTPRoute.
*/}}
{{- define "ghga-common.capabilities.httpRoute.apiVersion" -}}
{{- print "gateway.networking.k8s.io/v1" -}}
{{- end -}}
