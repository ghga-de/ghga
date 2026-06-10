{{/*
ghga-common.command-args will take the original run command and
prepends it with a failsafe routine that injects all existing secrets from vault.

@param The original command to run the microservice
*/}}
{{- define "ghga-common.command-args" -}}
{{- if and (index . 1) (index . 2) }}
{{- $argsList := (kindOf (index . 1) | eq "string") | ternary (list (index . 1)) (index . 1) }}
{{- $prefix := (index . 0).Values.commandPrefix | default "" }}
{{- if (index . 0).Values.vaultAgent.singleTemplate }}
{{- $command := $argsList }}
{{- if $prefix }}
{{- $command = prepend (rest $command) (printf "%s%s" $prefix (first $command)) }}
{{- end }}
{{- dict "command" $command | toYaml }}
{{- else }}
{{- $command := index . 2 }}
{{- if $prefix }}
{{- $command = prepend (rest $command) (printf "%s%s" $prefix (first $command)) }}
{{- end }}
{{- dict "command" $command | toYaml }}
{{- if (index . 0).Values.vaultAgent.enabled -}}
{{- $prependedArg := (print "if [ -d \"/vault/secrets\" ]; then for f in /vault/secrets/*; do if [ -f \"$f\" ]; then . \"$f\"; fi; done; fi; " (first $argsList) ";") }}
{{- if (rest $argsList) -}}
{{ $argsList = append (list $prependedArg) (rest $argsList) }}
{{- else }}
{{ $argsList = list $prependedArg }}
{{- end }}
{{- end }}
{{ dict "args" $argsList | toYaml }}
{{- end }}
{{- end -}}
{{- end -}}
