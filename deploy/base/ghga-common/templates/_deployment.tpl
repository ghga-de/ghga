{{- define "ghga-common.deployment" -}}
{{- if .Values.deployment.enabled -}}
---
apiVersion: {{ include "common.capabilities.deployment.apiVersion" . }}
kind: Deployment
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
    configmap-hash: {{ include (print $.Template.BasePath "/configmap.yml") . | sha256sum }}
    {{- if .Values.annotations }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.annotations "context" $) | nindent 4 }}
    {{- end }}
    {{- if .Values.commonAnnotations }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonAnnotations "context" $ ) | nindent 4 }}
    {{- end }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  revisionHistoryLimit: {{ .Values.revisionHistoryLimit }}
  selector:
    matchLabels: {{- include "common.labels.matchLabels" . | nindent 6 }}
  {{- if .Values.updateStrategy }}
  strategy: {{- toYaml .Values.updateStrategy | nindent 4 }}
  {{- end }}
  template:
    metadata:
      annotations:
        configmap-hash: {{ include (print $.Template.BasePath "/configmap.yml") . | sha256sum }}
        {{- if .Values.podAnnotations }}
        {{- .Values.podAnnotations | toYaml | nindent 8 }}
        {{- end }}
        {{- if .Values.vaultAgent.enabled }}
        {{- include "ghga-common.vaultAgentAnnotations" . | nindent 8 }}
        {{- end }}
        helm.sh/revision: {{ .Release.Revision | quote }}
      labels: {{- include "common.labels.standard" . | nindent 8 }}
        app: {{ include "common.names.fullname" . }}
        {{- if .Values.podLabels }}
        {{- include "common.tplvalues.render" (dict "value" .Values.podLabels "context" $) | nindent 8 }}
        {{- end }}
    spec:
      securityContext: {{- include "common.tplvalues.render" (dict "value" .Values.podSecurityContext "context" $) | nindent 8 }}
      serviceAccountName: {{ include "common.names.fullname" . }}
      {{/* allows Vault Agent to send (term) signals to the application process (namespace) */}}
      shareProcessNamespace: {{ ternary true .Values.shareProcessNamespace .Values.vaultAgent.enabled }}
      {{- if .Values.imagePullSecrets }}
      imagePullSecrets: {{- include "common.tplvalues.render" (dict "value" .Values.imagePullSecrets "context" $) | nindent 8 }}
      {{- end }}
      {{- if .Values.initContainers }}
      initContainers: {{- include "common.tplvalues.render" (dict "value" .Values.initContainers "context" $) | nindent 8 }}
      {{- end }}
      {{- if .Values.podRestartPolicy }}
      restartPolicy: {{ .Values.podRestartPolicy }}
      {{- end }}
      enableServiceLinks: {{ .Values.enableServiceLinks }}
      containers:
        - image: {{ include "common.images.image" (dict "imageRoot" .Values.image "global" .Values.global "chart" .Chart ) }}
          imagePullPolicy: {{ default (eq .Values.image.tag "latest" | ternary "Always" "IfNotPresent") .Values.image.pullPolicy }}
          {{- include "ghga-common.command-args" (list $ .Values.cmd)  | nindent 10 }}
          {{- if .Values.args }}
          args: {{- include "common.tplvalues.render" (dict "value" .Values.args "context" $) | nindent 12 }}
          {{- end }}
          {{- $envVars := include "ghga-common.env-vars" $ | fromYaml | dig "envVars" list -}}
          {{- if $envVars -}}
          env: {{- include "common.tplvalues.render" (dict "value" $envVars "context" $) | nindent 12 }}
          {{- end }}
          {{- if or .Values.envVarsConfigMap .Values.envVarsSecret }}
          envFrom:
            {{- if .Values.envVarsConfigMap }}
            - configMapRef:
                name: {{ include "common.tplvalues.render" (dict "value" .Values.envVarsConfigMap "context" $) }}
            {{- end }}
            {{- if .Values.envVarsSecret }}
            - secretRef:
                name: {{ include "common.tplvalues.render" (dict "value" .Values.envVarsSecret "context" $) }}
            {{- end }}
          {{- end }}
          name: {{ .Release.Name }}
          {{- if .Values.containerSecurityContext.enabled }}
          securityContext: {{- omit .Values.containerSecurityContext "enabled" | toYaml | nindent 12 }}
          {{- end }}
          {{- if and .Values.ports.enabled (omit .Values.ports "enabled") }}
          ports: {{- include "common.tplvalues.render" (dict "value" .Values.ports.ports "context" $) | nindent 12 }}
          {{- end }}
          {{- if and .Values.readinessProbe.enabled (omit .Values.readinessProbe "enabled") }}
          readinessProbe: {{- include "common.tplvalues.render" (dict "value" (omit .Values.readinessProbe "enabled") "context" $) | nindent 12 }}
          {{- end }}
          {{- if and .Values.livenessProbe.enabled (omit .Values.livenessProbe "enabled") }}
          livenessProbe: {{- include "common.tplvalues.render" (dict "value" (omit .Values.livenessProbe "enabled") "context" $) | nindent 12 }}
          {{- end }}
          {{- if and .Values.startupProbe.enabled (omit .Values.startupProbe "enabled") }}
          startupProbe: {{- include "common.tplvalues.render" (dict "value" (omit .Values.startupProbe "enabled") "context" $) | nindent 12 }}
          {{- end }}
          {{- if .Values.resources }}
          resources: {{- toYaml .Values.resources | nindent 12 }}
          {{- end }}
          {{- if .Values.lifecycleHooks }}
          lifecycle: {{- include "common.tplvalues.render" (dict "value" .Values.lifecycleHooks "context" $) | nindent 12 }}
          {{- end }}
          volumeMounts:
            {{- include "common.tplvalues.render" (dict "value" (include "ghga-common.configVolumeMount" $ | fromYaml | list) "context" $) | nindent 12 }}
            {{- if .Values.extraVolumeMounts }}
            {{- include "common.tplvalues.render" (dict "value" .Values.extraVolumeMounts "context" $) | nindent 12 }}
            {{- end }}
            {{- if .Values.kafkaUser.enabled }}
            - mountPath: "/kafka-secrets/"
              name: kafka-secret
              readOnly: true
            - mountPath:  "/cluster-ca-cert/"
              name: cluster-ca-cert
              readOnly: true
            {{- end }}
        {{- if .Values.sidecars }}
        {{- include "common.tplvalues.render" (dict "value" $.Values.sidecars "context" $) | nindent 8 }}
        {{- end }}
      volumes:
        {{- include "common.tplvalues.render" ( dict "value" (include "ghga-common.configVolume" $ | fromYaml | list) "context" $) | nindent 8 }}
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
      {{- include "common.images.renderPullSecrets" (dict "images" (list .Values.image) "context" $) | indent 6 }}
      {{- if .Values.hostAliases }}
      hostAliases: {{- include "common.tplvalues.render" (dict "value" .Values.hostAliases "context" $) | nindent 8 }}
      {{- end }}
      {{- if .Values.affinity }}
      affinity: {{- include "common.tplvalues.render" ( dict "value" .Values.affinity "context" $) | nindent 8 }}
      {{- else if or .Values.podAffinityPreset .Values.podAntiAffinityPreset .Values.nodeAffinityPreset.type }}
      affinity:
        {{- if not (empty .Values.podAffinityPreset) }}
        podAffinity: {{- include "common.affinities.pods" (dict "type" .Values.podAffinityPreset "context" $) | nindent 10 }}
        {{- end }}
        {{- if not (empty .Values.podAntiAffinityPreset) }}
        podAntiAffinity: {{- include "common.affinities.pods" (dict "type" .Values.podAntiAffinityPreset "context" $) | nindent 10 }}
        {{- end }}
        {{- if not (empty .Values.nodeAffinityPreset.type) }}
        nodeAffinity: {{- include "common.affinities.nodes" (dict "type" .Values.nodeAffinityPreset.type "key" .Values.nodeAffinityPreset.key "values" .Values.nodeAffinityPreset.values) | nindent 10 }}
        {{- end }}
      {{- end }}
      {{- if .Values.nodeSelector }}
      nodeSelector: {{- include "common.tplvalues.render" (dict "value" .Values.nodeSelector "context" $) | nindent 8 }}
      {{- end }}
      {{- if .Values.tolerations }}
      tolerations: {{- include "common.tplvalues.render" (dict "value" .Values.tolerations "context" $) | nindent 8 }}
      {{- end }}
      {{- if .Values.priorityClassName }}
      priorityClassName: {{ .Values.priorityClassName | quote }}
      {{- end }}
      {{- if .Values.topologySpreadConstraints }}
      topologySpreadConstraints: {{- include "common.tplvalues.render" (dict "value" .Values.topologySpreadConstraints "context" $) | nindent 8 }}
      {{- end }}
      {{- if .Values.schedulerName }}
      schedulerName: {{ .Values.schedulerName | quote }}
      {{- end }}
      {{- if .Values.podSecurityContext.enabled }}
      securityContext: {{- omit .Values.podSecurityContext "enabled" | toYaml | nindent 8 }}
      {{- end }}
      {{- if .Values.terminationGracePeriodSeconds }}
      terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds }}
      {{- end }}
{{- end -}}
{{- end -}}
