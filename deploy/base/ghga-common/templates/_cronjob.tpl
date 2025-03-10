{{- define "ghga-common.cronjob" -}}
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: {{ include "common.names.fullname" . }}
  namespace: {{ include "common.names.namespace" . | quote }}
  labels: {{- include "common.labels.standard" . | nindent 4 }}
    app: {{ include "common.names.fullname" . }}
    {{- if .Values.labels }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.labels "context" $ ) | nindent 4 }}
    {{- end }}
    {{- if .Values.commonLabels }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonLabels "context" $ ) | nindent 4 }}
    {{- end }}
  annotations:
    {{- if .Values.annotations }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.annotations "context" $) | nindent 4 }}
    {{- end }}
    {{- if .Values.commonAnnotations }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonAnnotations "context" $ ) | nindent 4 }}
    {{- end }}
spec:
  schedule: {{ .Values.cronSchedule }}
  successfulJobsHistoryLimit: {{ .Values.successfulJobsHistoryLimit }}
  failedJobsHistoryLimit: 1
  jobTemplate:
    metadata:
      labels: {{- include "common.labels.standard" . | nindent 8 }}
    spec:
      template:
        metadata:
          annotations:
            {{- if .Values.podAnnotations }}
            {{- .Values.podAnnotations | toYaml | nindent 12}}
            {{- end }}
            {{- if .Values.vaultAgent.enabled }}
            {{- include "ghga-common.vaultAgentAnnotations" . | nindent 12 }}
            {{- end }}
          labels: {{- include "common.labels.standard" . | nindent 12 }}
            app: {{ include "common.names.fullname" . }}
            {{- if .Values.podLabels }}
            {{- include "common.tplvalues.render" (dict "value" .Values.podLabels "context" $) | nindent 12 }}
            {{- end }}
        spec:
          restartPolicy: "OnFailure"
          serviceAccountName: {{ include "common.names.fullname" . }}
          shareProcessNamespace: {{ .Values.shareProcessNamespace }}
          {{- if .Values.imagePullSecrets }}
          imagePullSecrets: {{- include "common.tplvalues.render" (dict "value" .Values.imagePullSecrets "context" $) | nindent 12 }}
          {{- end }}
          containers:
          {{- range $container := .Values.containers }}
          - image: {{ include "common.images.image" (dict "imageRoot" $.Values.image "global" $.Values.global "chart" $.Chart ) }}
            imagePullPolicy: {{ default (eq $.Values.image.tag "latest" | ternary "Always" "IfNotPresent") $.Values.image.pullPolicy }}
            {{- include "ghga-common.command-args" (list $ $container.cmd) | nindent 12 }}
            {{- if $.Values.args }}
            args: {{- include "common.tplvalues.render" (dict "value" $.Values.args "context" $) | nindent 14 }}
            {{- end }}
            {{- if $.Values.envVars }}
            env: {{ include "common.tplvalues.render" (dict "value" $.Values.envVars "context" $) | nindent 14 }}
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
            name: {{ $.Release.Name }}-{{ $container.name }}
            securityContext: {{- omit $.Values.containerSecurityContext "enabled" | toYaml | nindent 14 }}
            volumeMounts:
            - name: {{ $container.config.name | default "config" }}
              {{- if $container.config.fileName }}
              mountPath: /home/{{ $container.config.appuser | default "appuser" }}/{{ $container.config.fileName }}
              subPath: {{ $container.config.fileName }}
              {{- else }}
              mountPath: /home/{{ $container.config.appuser | default "appuser" }}/.{{ $.Values.configPrefix }}.yaml
              subPath: .{{ $.Values.configPrefix }}.yaml
              {{- end }}
              readOnly: true
            {{- if $.Values.extraVolumeMounts }}
            {{- include "common.tplvalues.render" (dict "value" $.Values.extraVolumeMounts "context" $) | nindent 12 }}
            {{- end }}
            {{- if $.Values.kafkaUser.enabled }}
            - mountPath: "/kafka-secrets/"
              name: kafka-secret
              readOnly: true
            - mountPath:  "/cluster-ca-cert/"
              name: cluster-ca-cert
              readOnly: true
            {{- end }}
            {{- end }}
          {{- end }}
          volumes:
          {{- range $container := .Values.containers }}
          - name: {{ $container.config.name | default "config" }}
            configMap:
              name: {{ include "common.names.fullname" $ }}
              items:
              - key: {{ $container.config.key | default "parameters" }}
                {{- if $container.config.fileName }}
                path: {{ $container.config.fileName }}
                {{- else }}
                path: .{{ $.Values.configPrefix }}.yaml
                {{- end }}
          {{- end }}
          {{- if .Values.extraVolumes }}
          {{- include "common.tplvalues.render" ( dict "value" .Values.extraVolumes "context" $) | nindent 8 }}
          {{- end }}
          {{- if .Values.kafkaUser.enabled }}
          - name: kafka-secret
            secret:
              secretName: {{ .Release.Namespace }}-{{ include "common.names.fullname" . }}
              optional: false
          - name: cluster-ca-cert
            secret:
              secretName: {{ .Values.kafkaUser.caCertSecretName }}
              optional: false
          {{- end }}
{{- end -}}