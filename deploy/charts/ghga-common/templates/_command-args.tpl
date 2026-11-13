{{/*
ghga-common.command-args will take the executable and executableArgs
and, when secretEnvFiles.enabled, prepends a routine that sources every file in
secretEnvFiles.dir, so secrets written there by a sidecar reach the environment.

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

{{- /* Exec-style rendering: no shell wrapper, for shell-less hardened runtime
     images and for secrets the service reads from files itself. */ -}}
{{- $execStyle := eq ((index . 0).Values.commandStyle | default "shell") "exec" }}
{{- $secretEnvFiles := (index . 0).Values.secretEnvFiles | default dict }}
{{- if and $execStyle $secretEnvFiles.enabled }}
{{- fail "commandStyle=exec cannot source secretEnvFiles (no shell in the image); disable secretEnvFiles or use commandStyle=shell" }}
{{- end }}
{{- if $execStyle }}
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

{{- /* Shell style: sh -c wraps the built command string, with the secret
     sourcing prefix spliced in ahead of it when enabled. Nothing has ever
     needed a shell other than sh here, so this isn't a values.yaml knob. */ -}}
command: ["sh", "-c"]
{{- $args := list $cmdString }}
{{- if $secretEnvFiles.enabled }}
{{- $dir := $secretEnvFiles.dir }}
{{- $wrapper := printf "if [ -d \"%s\" ]; then for f in %s/*; do if [ -f \"$f\" ]; then . \"$f\"; fi; done; fi; " $dir $dir }}
{{- $args = list (print $wrapper $cmdString ";") }}
{{- end }}
args: {{ $args | toJson }}
{{- end }}
{{- end -}}
{{- end -}}
