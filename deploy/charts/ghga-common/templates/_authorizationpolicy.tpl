{{- define "ghga-common.authorizationpolicy" -}}
{{- if .Values.authorizationPolicy.enabled }}
{{- $ap := .Values.authorizationPolicy }}
{{- $namespace := include "common.names.namespace" . }}
{{- $operationKeys := list "methods" "paths" "ports" "allowAll" }}
{{- $identityKeys := list "serviceAccount" "namespace" "principals" }}
{{- $rules := list }}
{{- /* callers (from the chart) say what each caller may do, identities (from the
platform) who the caller is. Both are maps, so Helm merges them key by key and an
environment can override or (with null) drop a single entry. */}}
{{- range $caller, $operations := $ap.callers }}
{{- if not (kindIs "invalid" $operations) }}
{{- if not (kindIs "slice" $operations) }}
{{- fail (printf "authorizationPolicy.callers.%s must be a list of operations" $caller) }}
{{- end }}
{{- /* Fail closed: a caller that restricts nothing must say so with allowAll, so a
typo or an empty list stops the render instead of opening the service. */}}
{{- if not $operations }}
{{- fail (printf "authorizationPolicy.callers.%s has no operation; list its methods and paths, or [{allowAll: true}]" $caller) }}
{{- end }}
{{- $to := list }}
{{- $allowAll := false }}
{{- range $op := $operations }}
{{- if not (kindIs "map" $op) }}
{{- fail (printf "authorizationPolicy.callers.%s: each operation must be a map" $caller) }}
{{- end }}
{{- range $key, $_ := $op }}
{{- if not (has $key $operationKeys) }}
{{- fail (printf "authorizationPolicy.callers.%s: unknown operation key %q" $caller $key) }}
{{- end }}
{{- end }}
{{- if $op.allowAll }}
{{- if or (gt (len $operations) 1) (gt (len $op) 1) }}
{{- fail (printf "authorizationPolicy.callers.%s: allowAll must be the caller's only operation, with no other keys" $caller) }}
{{- end }}
{{- $allowAll = true }}
{{- else }}
{{- $operation := dict }}
{{- range $key := list "paths" "methods" "ports" }}
{{- with (get $op $key) }}
{{- $_ := set $operation $key (ternary (toStrings .) . (eq $key "ports")) }}
{{- end }}
{{- end }}
{{- if not $operation }}
{{- fail (printf "authorizationPolicy.callers.%s has an operation that restricts nothing; give it methods or paths, or use [{allowAll: true}]" $caller) }}
{{- end }}
{{- $to = append $to (dict "operation" $operation) }}
{{- end }}
{{- end }}
{{- $identity := default dict (get (default dict $ap.identities) $caller) }}
{{- range $key, $_ := $identity }}
{{- if not (has $key $identityKeys) }}
{{- fail (printf "authorizationPolicy.identities.%s: unknown key %q" $caller $key) }}
{{- end }}
{{- end }}
{{- $principals := $identity.principals }}
{{- if not $principals }}
{{- /* The ServiceAccount defaults to the caller's key, its chart name. */}}
{{- $principals = list (printf "%s/ns/%s/sa/%s" $ap.trustDomain (default $namespace $identity.namespace) (default $caller $identity.serviceAccount)) }}
{{- end }}
{{- $rule := dict "from" (list (dict "source" (dict "principals" $principals))) }}
{{- if not $allowAll }}
{{- $_ := set $rule "to" $to }}
{{- end }}
{{- $rules = append $rules $rule }}
{{- end }}
{{- end }}
{{- /* Raw Istio rules for what no chart knows, such as the ingress gateway. */}}
{{- range $rule := $ap.extraRules }}
{{- $rules = append $rules $rule }}
{{- end }}
{{- /* denyAll overrides the rules: they come from the chart, denyAll from the
environment, e.g. for a consumer instance that takes no calls at all. */}}
{{- if $ap.denyAll }}
{{- $rules = list }}
{{- else if not $rules }}
{{- fail "authorizationPolicy.enabled with no callers or extraRules would deny all traffic to the workload: add them, or set authorizationPolicy.denyAll=true if that is intended" }}
{{- end }}
{{- if and $rules (not .Values.service.enabled) }}
{{- fail "authorizationPolicy rules need the chart's Service, which the waypoint enforces the policy on: enable service, or set authorizationPolicy.denyAll=true" }}
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
