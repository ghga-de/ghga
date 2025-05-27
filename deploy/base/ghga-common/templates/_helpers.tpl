{{- define "ghga-common.apiFullBasePath" -}}
{{ .Values.apiBasePathPrefix | empty | ternary .Values.apiBasePath (cat .Values.apiBasePathPrefix .Values.apiBasePath ) | nospace }}
{{- end -}}
{{- define "ghga-common.apiBasePath" -}}
{{- if .Values.apiBasePath -}}
    api_root_path: {{ include "ghga-common.apiFullBasePath" . }}
{{- end -}}
{{- end -}}
{{- define "ghga-common.dbName" -}}
{{- if .Values.dbName -}}
    db_name: {{ .Values.dbNamePrefix | empty | ternary .Values.dbName (cat .Values.dbNamePrefix "-" .Values.dbName ) | nospace }}
{{- end -}}
{{- if .Values.mongodb.dbName -}}
    db_name: {{ .Values.dbNamePrefix | empty | ternary .Values.mongodb.dbName (cat .Values.dbNamePrefix "-" .Values.mongodb.dbName ) | nospace }}
{{- end -}}
{{- end -}}
{{- define "ghga-common.serviceName" -}}
{{- if .Values.serviceName -}}
    {{- .Values.serviceNamePrefix | empty | ternary .Values.serviceName (cat .Values.serviceNamePrefix "-" .Values.serviceName ) | nospace -}}
{{- end -}}
{{- end -}}
{{- define "ghga-common.serviceInstanceId" -}}
{{- if .Values.serviceInstanceId -}}
    service_instance_id: {{ .Values.serviceInstanceIdPrefix | empty | ternary .Values.serviceInstanceId (cat .Values.serviceInstanceIdPrefix "-" .Values.serviceInstanceId ) | nospace }}
{{- end -}}
{{- end -}}
{{- define "ghga-common.serviceNameConsumer" -}}
{{- if .Values.serviceNameConsumer -}}
    service_name: {{ .Values.serviceNamePrefix | empty | ternary .Values.serviceNameConsumer (cat .Values.serviceNamePrefix "-" .Values.serviceNameConsumer ) | nospace }}
{{- end -}}
{{- end -}}
{{- define "ghga-common.serviceInstanceIdConsumer" -}}
{{- if .Values.serviceInstanceIdConsumer -}}
    service_instance_id: {{ .Values.serviceInstanceIdPrefix | empty | ternary .Values.serviceInstanceIdConsumer (cat .Values.serviceInstanceIdPrefix "-" .Values.serviceInstanceIdConsumer ) | nospace }}
{{- end -}}
{{- end -}}
