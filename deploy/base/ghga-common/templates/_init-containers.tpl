{{- define "ghga-common.initContainers" -}}
{{- $initContainers := .Values.initContainers -}}
{{- if .Values.migrationInitContainer.enabled -}}
{{- $defaultImage := include "common.images.image" (dict "imageRoot" $.Values.image "global" $.Values.global "chart" $.Chart) -}}
{{- $defaultPullPolicy := eq $.Values.image.tag "latest" | ternary "Always" "IfNotPresent" -}}
{{- $migrationContainer := dict
  "name" "migration"
  "image" (or .Values.migrationInitContainer.image $defaultImage)
  "imagePullPolicy" (or .Values.migrationInitContainer.imagePullPolicy $defaultPullPolicy)
  "cmd" .Values.migrationInitContainer.cmd
  "args" .Values.migrationInitContainer.args
  "env" .Values.migrationInitContainer.env
  "resources" .Values.migrationInitContainer.resources
  "volumeMounts" .Values.migrationInitContainer.volumeMounts
-}}
{{- $initContainers = prepend $initContainers $migrationContainer -}}
{{- end -}}
{{- if $initContainers -}}
{{- range $index, $container := $initContainers }}
- name: {{ $container.name | default (printf "init-%d" $index) }}
  image: {{ $container.image | default (include "common.images.image" (dict "imageRoot" $.Values.image "global" $.Values.global "chart" $.Chart)) }}
  imagePullPolicy: {{ $container.imagePullPolicy | default (eq $.Values.image.tag "latest" | ternary "Always" "IfNotPresent") $.Values.image.pullPolicy }} 
  {{- include "ghga-common.command-args" (list $ $container.args $.Values.command) | nindent 2 }}
  {{- if $container.env }}
  env: {{- toYaml $container.env | nindent 4 }}
  {{- end }}
  {{- $envVars := include "ghga-common.env-vars" $ | fromYaml | dig "envVars" list -}}
  {{- if and (not $container.env) $envVars }}
  env: {{- include "common.tplvalues.render" (dict "value" $envVars "context" $) | nindent 4 }}
  {{- end }}
  {{- if $.Values.containerSecurityContext.enabled }}
  securityContext: {{- omit $.Values.containerSecurityContext "enabled" | toYaml | nindent 4 }}
  {{- end }}
  {{- if $container.resources }}
  resources: {{- toYaml $container.resources | nindent 4 }}
  {{- end }}
  volumeMounts:
    {{- include "common.tplvalues.render" (dict "value" (include "ghga-common.configVolumeMount" $ | fromYaml | list) "context" $) | nindent 4 }}
    {{- if $.Values.extraVolumeMounts }}
    {{- include "common.tplvalues.render" (dict "value" $.Values.extraVolumeMounts "context" $) | nindent 4 }}
    {{- end }}
    {{- if $container.volumeMounts }}
    {{- include "common.tplvalues.render" (dict "value" $container.volumeMounts "context" $) | nindent 4 }}
    {{- end }}
{{- end -}}
{{- end -}}
{{- end -}}
