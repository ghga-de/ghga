{{- define "ghga-common.cronjob" -}}
{{- range $key, $job := .Values.cronjobs }}
{{- if $job.enabled }}
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: {{ include "common.names.fullname" $ }}{{- if ne $key "default" }}-{{ $key }}{{- end }}
  namespace: {{ include "common.names.namespace" $ | quote }}
  labels: {{- include "common.labels.standard" $ | nindent 4 }}
    app: {{ include "common.names.fullname" $ }}
    {{- if $.Values.commonLabels }}
    {{- include "common.tplvalues.render" ( dict "value" $.Values.commonLabels "context" $ ) | nindent 4 }}
    {{- end }}
  {{- if $.Values.commonAnnotations }}
  annotations:
    {{- include "common.tplvalues.render" ( dict "value" $.Values.commonAnnotations "context" $ ) | nindent 4 }}
  {{- end }}
spec:
  schedule: {{ $job.schedule | default $.Values.cronSchedule }}
  successfulJobsHistoryLimit: {{ $job.successfulJobsHistoryLimit | default $.Values.successfulJobsHistoryLimit }}
  failedJobsHistoryLimit: 1
  jobTemplate:
    metadata:
      labels: {{- include "common.labels.standard" $ | nindent 8 }}
    spec:
      template:
        metadata:
          {{- /* Merge (rather than concatenate) annotation sources so a per-cronjob
                 podAnnotations override can actually replace a same-named vaultAgent
                 or top-level annotation instead of emitting a duplicate YAML key. */}}
          {{- $annotations := dict }}
          {{- if $.Values.podAnnotations }}
          {{- $annotations = mergeOverwrite $annotations $.Values.podAnnotations }}
          {{- end }}
          {{- if $.Values.vaultAgent.enabled }}
          {{- $vaultAnnotationsRaw := include "ghga-common.vaultAgentAnnotations" $ }}
          {{- if $.Values.vaultAgent.singleTemplate }}
          {{- $vaultAnnotationsRaw = include "ghga-common.vaultAgentAnnotationsSingleTemplate" $ }}
          {{- end }}
          {{- $annotations = mergeOverwrite $annotations ($vaultAnnotationsRaw | fromYaml) }}
          {{- end }}
          {{- if $job.podAnnotations }}
          {{- $annotations = mergeOverwrite $annotations $job.podAnnotations }}
          {{- end }}
          annotations:
            {{- if $annotations }}
            {{- toYaml $annotations | nindent 12 }}
            {{- end }}
          labels: {{- include "common.labels.standard" $ | nindent 12 }}
            app: {{ include "common.names.fullname" $ }}
            {{- if $.Values.podLabels }}
            {{- include "common.tplvalues.render" (dict "value" $.Values.podLabels "context" $) | nindent 12 }}
            {{- end }}
        spec:
          securityContext: {{- include "common.tplvalues.render" (dict "value" $.Values.podSecurityContext "context" $) | nindent 12 }}
          restartPolicy: "OnFailure"
          serviceAccountName: {{ include "common.names.fullname" $ }}
          shareProcessNamespace: {{ $.Values.shareProcessNamespace }}
          {{- include "common.images.renderPullSecrets" (dict "images" (list $.Values.image) "context" $) | nindent 10 }}
          containers:
          - image: {{ include "common.images.image" (dict "imageRoot" $.Values.image "global" $.Values.global "chart" $.Chart ) }}
            imagePullPolicy: {{ default (eq $.Values.image.tag "latest" | ternary "Always" "IfNotPresent") $.Values.image.pullPolicy }}
            {{- $executable := $job.executable | default $.Values.executable }}
            {{- $executableArgs := $job.executableArgs | default $.Values.executableArgs }}
            {{- include "ghga-common.command-args" (list $ $executable $executableArgs)  | nindent 12 }}
            {{- $envVars := include "ghga-common.env-vars" $ | fromYaml | dig "envVars" list -}}
            {{- if $envVars }}
            env: {{- include "common.tplvalues.render" (dict "value" $envVars "context" $) | nindent 12 }}
            {{- end }}
            {{- if or $.Values.envVarsConfigMap $.Values.envVarsSecret }}
            envFrom:
              {{- if $.Values.envVarsConfigMap }}
              - configMapRef:
                  name: {{ include "common.tplvalues.render" (dict "value" $.Values.envVarsConfigMap "context" $) }}
              {{- end }}
              {{- if $.Values.envVarsSecret }}
              - secretRef:
                  name: {{ include "common.tplvalues.render" (dict "value" $.Values.envVarsSecret "context" $) }}
              {{- end }}
            {{- end }}
            {{- if $.Values.containerSecurityContext.enabled }}
            securityContext: {{- omit $.Values.containerSecurityContext "enabled" | toYaml | nindent 14 }}
            {{- end }}
            name: {{ $.Release.Name }}{{- if ne $key "default" }}-{{ $key }}{{- end }}
            {{- $resources := $job.resources | default $.Values.resources }}
            {{- if $resources }}
            resources: {{- toYaml $resources | nindent 14 }}
            {{- end }}
            volumeMounts: {{- include "ghga-common.volumemounts" $ | nindent 14 }}
          volumes: {{- include "ghga-common.volumes" $ | nindent 12 }}
{{- end }}
{{- end }}
{{- end -}}
