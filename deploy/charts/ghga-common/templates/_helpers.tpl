{{- define "ghga-common.apiBasePath" -}}
    api_root_path: {{ .Values.apiBasePathPrefix | empty | ternary .Values.apiBasePath (cat .Values.apiBasePathPrefix .Values.apiBasePath ) | nospace }}
{{- end -}}
{{- define "ghga-common.dbName" -}}
    db_name: {{ .Values.dbNamePrefix | empty | ternary .Values.dbName (cat .Values.dbNamePrefix "-" .Values.dbName ) | nospace }}
{{- end -}}
{{- define "ghga-common.serviceName" -}}
    service_name: {{ .Values.serviceNamePrefix | empty | ternary .Values.serviceName (cat .Values.serviceNamePrefix "-" .Values.serviceName ) | nospace }}
{{- end -}}
{{- define "ghga-common.serviceInstanceId" -}}
    service_instance_id: {{ .Values.serviceInstanceIdPrefix | empty | ternary .Values.serviceInstanceId (cat .Values.serviceInstanceIdPrefix "-" .Values.serviceInstanceId ) | nospace }}
{{- end -}}
{{- define "ghga-common.serviceNameConsumer" -}}
    service_name: {{ .Values.serviceNamePrefix | empty | ternary .Values.serviceNameConsumer (cat .Values.serviceNamePrefix "-" .Values.serviceNameConsumer ) | nospace }}
{{- end -}}
{{- define "ghga-common.serviceInstanceIdConsumer" -}}
    service_instance_id: {{ .Values.serviceInstanceIdPrefix | empty | ternary .Values.serviceInstanceIdConsumer (cat .Values.serviceInstanceIdPrefix "-" .Values.serviceInstanceIdConsumer ) | nospace }}
{{- end -}}