{{- define "ghga-common.authorizationpolicy" -}}
{{- if .Values.authorizationPolicy.enabled }}
{{- $ap := .Values.authorizationPolicy }}
{{- $namespace := include "common.names.namespace" . }}
{{- $callers := default dict $ap.callers }}
{{- $identities := default dict $ap.identities }}
{{- $operationKeys := list "methods" "paths" "ports" "allowAll" }}
{{- $identityKeys := list "serviceAccount" "namespace" "principals" }}
{{- $rules := list }}
{{- /* Fail closed throughout: anything that would allow more than it says, or that
cannot be matched to a caller, stops the render instead of opening the service.
callers (from the chart) say what each caller may do, identities (from the platform)
who it is. Both are maps, so Helm merges them key by key; an environment drops a
caller by setting both its callers and its identities entry to null.
denyAll skips all of it: the chart's callers can open nothing under it, and an
environment that turns a consumer instance off should not have to name them. */}}
{{- if not $ap.denyAll }}
{{- range $caller, $identity := $identities }}
{{- if and (not (kindIs "invalid" $identity)) (or (not (hasKey $callers $caller)) (kindIs "invalid" (get $callers $caller))) }}
{{- fail (printf "authorizationPolicy.identities.%s has no caller: check the key, or drop the identity together with the caller" $caller) }}
{{- end }}
{{- end }}
{{- range $caller, $operations := $callers }}
{{- if not (kindIs "invalid" $operations) }}
{{- if not (kindIs "slice" $operations) }}
{{- fail (printf "authorizationPolicy.callers.%s must be a list of operations" $caller) }}
{{- end }}
{{- if not $operations }}
{{- fail (printf "authorizationPolicy.callers.%s has no operation; list its methods and paths, or [{allowAll: true}]" $caller) }}
{{- end }}
{{- $to := list }}
{{- $allowAll := false }}
{{- range $op := $operations }}
{{- if not (kindIs "map" $op) }}
{{- fail (printf "authorizationPolicy.callers.%s: each operation must be a map" $caller) }}
{{- end }}
{{- range $key, $value := $op }}
{{- if not (has $key $operationKeys) }}
{{- fail (printf "authorizationPolicy.callers.%s: unknown operation key %q" $caller $key) }}
{{- end }}
{{- /* An empty list would drop the key and with it the restriction. */}}
{{- if and (ne $key "allowAll") (empty $value) }}
{{- fail (printf "authorizationPolicy.callers.%s: %s is empty, which would allow any; list values or remove the key" $caller $key) }}
{{- end }}
{{- end }}
{{- if hasKey $op "allowAll" }}
{{- if not (kindIs "bool" $op.allowAll) }}
{{- fail (printf "authorizationPolicy.callers.%s: allowAll must be true or false, not %q" $caller (toString $op.allowAll)) }}
{{- end }}
{{- if and $op.allowAll (or (gt (len $operations) 1) (gt (len $op) 1)) }}
{{- fail (printf "authorizationPolicy.callers.%s: allowAll must be the caller's only operation, with no other keys" $caller) }}
{{- end }}
{{- end }}
{{- if $op.allowAll }}
{{- $allowAll = true }}
{{- else }}
{{- $operation := dict }}
{{- /* allowAll: false is the same as leaving it out. */}}
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
{{- /* No default identity: workloads run under release-specific ServiceAccounts, so
a guessed one would only show up as 403s. */}}
{{- $identity := get $identities $caller }}
{{- if or (kindIs "invalid" $identity) (not $identity) }}
{{- fail (printf "authorizationPolicy.identities.%s is missing: set the caller's serviceAccount (and namespace if it differs) or principals" $caller) }}
{{- end }}
{{- if not (kindIs "map" $identity) }}
{{- fail (printf "authorizationPolicy.identities.%s must be a map, e.g. {serviceAccount: <name>}" $caller) }}
{{- end }}
{{- range $identityKey, $identityValue := $identity }}
{{- if not (has $identityKey $identityKeys) }}
{{- fail (printf "authorizationPolicy.identities.%s: unknown key %q" $caller $identityKey) }}
{{- end }}
{{- if empty $identityValue }}
{{- fail (printf "authorizationPolicy.identities.%s: %s is empty; set it or remove the key" $caller $identityKey) }}
{{- end }}
{{- end }}
{{- $principals := $identity.principals }}
{{- if $principals }}
{{- if or (hasKey $identity "serviceAccount") (hasKey $identity "namespace") }}
{{- fail (printf "authorizationPolicy.identities.%s: principals replaces serviceAccount and namespace, set either" $caller) }}
{{- end }}
{{- else }}
{{- if not $identity.serviceAccount }}
{{- fail (printf "authorizationPolicy.identities.%s needs serviceAccount or principals" $caller) }}
{{- end }}
{{- $principals = list (printf "%s/ns/%s/sa/%s" $ap.trustDomain (default $namespace $identity.namespace) $identity.serviceAccount) }}
{{- end }}
{{- $rule := dict "from" (list (dict "source" (dict "principals" $principals))) }}
{{- if not $allowAll }}
{{- $_ := set $rule "to" $to }}
{{- end }}
{{- $rules = append $rules $rule }}
{{- end }}
{{- end }}
{{- /* Raw Istio rules for what no chart knows, such as the ingress gateway. In an
ALLOW policy an empty rule matches every request and one without from matches
every source, so both need saying. */}}
{{- range $i, $rule := $ap.extraRules }}
{{- if or (not (kindIs "map" $rule)) (not (omit $rule "allowAnySource")) }}
{{- fail (printf "authorizationPolicy.extraRules[%d] is empty, which would allow every request" $i) }}
{{- end }}
{{- if and (hasKey $rule "allowAnySource") (not (kindIs "bool" $rule.allowAnySource)) }}
{{- fail (printf "authorizationPolicy.extraRules[%d]: allowAnySource must be true or false" $i) }}
{{- end }}
{{- range $j, $from := (default list $rule.from) }}
{{- if or (not (kindIs "map" $from)) (not (kindIs "map" $from.source)) (not $from.source) }}
{{- fail (printf "authorizationPolicy.extraRules[%d].from[%d] needs a source with at least one field; an empty source matches every caller" $i $j) }}
{{- end }}
{{- end }}
{{- if and (not $rule.from) (not $rule.allowAnySource) }}
{{- fail (printf "authorizationPolicy.extraRules[%d] has no from, which would allow any source; add from, or allowAnySource: true if that is intended" $i) }}
{{- end }}
{{- $rules = append $rules (omit $rule "allowAnySource") }}
{{- end }}
{{- if not $rules }}
{{- fail "authorizationPolicy.enabled with no callers or extraRules would deny all traffic to the workload: add them, or set authorizationPolicy.denyAll=true if that is intended" }}
{{- end }}
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
