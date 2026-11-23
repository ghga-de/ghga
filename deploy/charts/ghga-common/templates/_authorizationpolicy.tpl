{{- define "ghga-common.authorizationpolicy" -}}
{{- if .Values.authorizationPolicy.enabled }}
{{- $ap := .Values.authorizationPolicy }}
{{- $namespace := include "common.names.namespace" . }}
{{- $rules := list }}
{{- /* A map, not a list: Helm merges maps key by key, so the platform layer can add,
override or (with null) drop one caller without restating the others. */}}
{{- range $caller, $c := $ap.callers }}
{{- if not (kindIs "invalid" $c) }}
{{- if $c.rule }}
{{- $rules = append $rules $c.rule }}
{{- else }}
{{- $principals := $c.principals }}
{{- if not $principals }}
{{- /* The ServiceAccount defaults to the caller's key, its chart name. */}}
{{- $principals = list (printf "%s/ns/%s/sa/%s" $ap.trustDomain (default $namespace $c.namespace) (default $caller $c.serviceAccount)) }}
{{- end }}
{{- $rule := dict "from" (list (dict "source" (dict "principals" $principals))) }}
{{- /* operations lists several method/path sets; paths/methods/ports on the caller
are the shorthand for one. */}}
{{- $to := list }}
{{- range $op := (default (list (pick $c "paths" "methods" "ports")) $c.operations) }}
{{- $operation := dict }}
{{- range $key := list "paths" "methods" "ports" }}
{{- with (get $op $key) }}
{{- $_ := set $operation $key (ternary (toStrings .) . (eq $key "ports")) }}
{{- end }}
{{- end }}
{{- if $operation }}
{{- $to = append $to (dict "operation" $operation) }}
{{- end }}
{{- end }}
{{- if $to }}
{{- $_ := set $rule "to" $to }}
{{- end }}
{{- $rules = append $rules $rule }}
{{- end }}
{{- end }}
{{- end }}
{{- if and (not $rules) (not $ap.denyAll) }}
{{- fail "authorizationPolicy.enabled with no callers would deny all traffic to the workload: set authorizationPolicy.callers, or authorizationPolicy.denyAll=true if that is intended" }}
{{- end }}
{{- /* denyAll overrides the callers: they come from the chart, denyAll from the
environment, e.g. for a consumer instance that takes no calls at all. */}}
{{- if $ap.denyAll }}
{{- $rules = list }}
{{- end }}
{{- if and $rules (not .Values.service.enabled) }}
{{- fail "authorizationPolicy.callers need the chart's Service, which the waypoint enforces the policy on: enable service, or set authorizationPolicy.denyAll=true" }}
{{- end }}
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: {{ include "common.names.fullname" . }}
  namespace: {{ $namespace | quote }}
  labels: {{- include "common.labels.standard" . | nindent 4 }}
    {{- if .Values.commonLabels }}
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonLabels "context" $ ) | nindent 4 }}
    {{- end }}
  {{- if .Values.commonAnnotations }}
  annotations:
    {{- include "common.tplvalues.render" ( dict "value" .Values.commonAnnotations "context" $ ) | nindent 4 }}
  {{- end }}
spec:
  {{- /* Ambient mode: rules with paths or methods need the waypoint, which enforces
  policies bound to the Service; ztunnel would deny them. A policy without rules is
  plain L4, so ztunnel enforces it on the pods, also for traffic to the pod IP. Both
  refer to the workload through the same helpers as the Service and the Deployment. */}}
  {{- if $rules }}
  targetRefs:
    - kind: Service
      group: ""
      name: {{ include "common.names.fullname" . }}
  {{- else }}
  selector:
    matchLabels: {{- include "common.labels.matchLabels" . | nindent 6 }}
  {{- end }}
  action: ALLOW
  {{- if $rules }}
  rules:
    {{- include "common.tplvalues.render" (dict "value" $rules "context" $) | nindent 4 }}
  {{- end }}
{{- end }}
{{- end }}
