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
        [ -f "$f" ] && . "$f";
      done
    fi;
    {{ first . }};
{{- end -}}
