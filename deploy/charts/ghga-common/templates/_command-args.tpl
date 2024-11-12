{{/*
ghga-common.command-args will take the original run command and
prepends it with a failsafe routine that injects all existing secrets from vault.

@param The original command to run the microservice
*/}}
{{- define "ghga-common.command-args" -}}
command: ["sh", "-c"]
args:
  - if [ -d "/vault/secrets" ]; then
      for f in /vault/secrets/*; do
        [ -f "$f" ] &&  sed s/{{ (first .).Values.configPrefixPlaceholder }}/{{ (first .).Values.configPrefix | upper }}/g "$f" > "$f"_ && . "$f"_;
      done
    fi;
    {{ index . 1 }};
{{- end -}}
