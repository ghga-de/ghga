{{/*
ghga-common.command-args will take the original run command and
prepends it with a failsafe routine that injects all existing secrets from vault.

@param The original command to run the microservice
*/}}
{{- define "ghga-common.command-args" -}}
{{- $argsList := (kindOf (index . 1) | eq "string") | ternary (list (index . 1)) (index . 1) }}
{{- dict "command" (index . 2) | toYaml }}
{{- if (index . 0).Values.vaultAgent.enabled -}}
{{- $prependedArg := (print "if [ -d \"/vault/secrets\" ]; then for f in /vault/secrets/*; do if [ -f \"$f\" ]; then . \"$f\"; fi; done; fi; " (first $argsList) ";") }}
{{- if (rest $argsList) -}}
{{ $argsList = append (list $prependedArg) (rest $argsList) }}
{{- else }}
{{ $argsList = list $prependedArg }}
{{- end }}
{{- end }}
{{ dict "args" $argsList | toYaml }}
{{- end -}}
