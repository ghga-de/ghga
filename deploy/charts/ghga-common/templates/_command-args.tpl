{{/*
ghga-common.command-args will take the executable and executableArgs
and prepends it with a failsafe routine that injects all existing secrets from vault.

@param Root context
@param executable - the executable name (e.g., "pcs")
@param executableArgs - list of arguments for the executable (e.g., ["run-rest"])
*/}}
{{- define "ghga-common.command-args" -}}
{{- if index . 1 }}
{{- $executable := index . 1 }}
{{- $executableArgs := index . 2 | default list }}
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

{{- /* Exec-style rendering: no shell wrapper. Used by vaultAgent.singleTemplate
     (secrets are rendered to files, nothing needs sourcing) and by
     commandStyle=exec (shell-less hardened runtime images). */ -}}
{{- $execStyle := eq ((index . 0).Values.commandStyle | default "shell") "exec" }}
{{- if and $execStyle (index . 0).Values.vaultAgent.enabled (not (index . 0).Values.vaultAgent.singleTemplate) }}
{{- fail "commandStyle=exec cannot source vault agent env files (no shell in the image); use vaultAgent.singleTemplate or commandStyle=shell" }}
{{- end }}
{{- if or (index . 0).Values.vaultAgent.singleTemplate $execStyle }}
{{- /* Command is the prefixed executable, args are passed as a real argv list */ -}}
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

{{- /* Shell style: sh -c wraps the built command string, with a vault secret
     injection prefix spliced in ahead of it when enabled. Nothing has ever
     needed a shell other than sh here, so this isn't a values.yaml knob. */ -}}
command: ["sh", "-c"]
{{- $args := list $cmdString }}
{{- if (index . 0).Values.vaultAgent.enabled }}
{{- $vaultWrapper := "if [ -d \"/vault/secrets\" ]; then for f in /vault/secrets/*; do if [ -f \"$f\" ]; then . \"$f\"; fi; done; fi; " }}
{{- $args = list (print $vaultWrapper $cmdString ";") }}
{{- end }}
args: {{ $args | toJson }}
{{- end }}
{{- end -}}
{{- end -}}
