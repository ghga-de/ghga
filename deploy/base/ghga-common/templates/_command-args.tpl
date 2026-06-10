{{/*
ghga-common.command-args will take the executable and executableArgs
and prepends it with a failsafe routine that injects all existing secrets from vault.

@param Root context
@param executable - the executable name (e.g., "pcs")
@param executableArgs - list of arguments for the executable (e.g., ["run-rest"])
@param command - the shell wrapper command (e.g., ["sh", "-c"])
*/}}
{{- define "ghga-common.command-args" -}}
{{- if and (index . 1) (index . 3) }}
{{- $executable := index . 1 }}
{{- $executableArgs := index . 2 | default list }}
{{- $command := index . 3 }}
{{- $prefix := (index . 0).Values.commandPrefix | default "" }}

{{- /* Build the full command string by explicitly concatenating parts */ -}}
{{- $cmdString := $executable }}
{{- range $executableArgs }}
{{- $cmdString = printf "%s %v" $cmdString . }}
{{- end }}

{{- /* Apply prefix if defined */ -}}
{{- if $prefix }}
{{- $cmdString = printf "%s%s" $prefix $cmdString }}
{{- end }}

{{- /* Handle singleTemplate mode: command includes everything */ -}}
{{- if (index . 0).Values.vaultAgent.singleTemplate }}
{{- /* In singleTemplate mode: command is prefixed executable, args are the arguments */ -}}
{{- $prefixedExec := $executable }}
{{- if $prefix }}
{{- $prefixedExec = printf "%s%s" $prefix $executable }}
{{- end }}
command:
- {{ $prefixedExec }}
args:
{{- range $executableArgs }}
- {{ . }}
{{- end }}
{{- else }}

{{- /* Add vault secret injection wrapper if enabled */ -}}
command: {{ $command | toJson }}
{{- $args := list $cmdString }}
{{- if (index . 0).Values.vaultAgent.enabled }}
{{- $vaultWrapper := "if [ -d \"/vault/secrets\" ]; then for f in /vault/secrets/*; do if [ -f \"$f\" ]; then . \"$f\"; fi; done; fi; " }}
{{- $args = list (print $vaultWrapper $cmdString ";") }}
{{- end }}
args: {{ $args | toJson }}
{{- end }}
{{- end -}}
{{- end -}}
