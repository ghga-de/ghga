{{/*
ghga-common.command-args will take the original run command and
prepends it with a failsafe routine that injects all existing secrets from vault.

@param The original command to run the microservice
*/}}
{{- define "ghga-common.ingress" -}}
{{ if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Release.Name }}
  annotations:
{{ toYaml .Values.ingress.annotations | indent 4 }}
spec:
  ingressClassName: nginx
  {{ if .Values.ingress.tls.enabled }}
  tls:
    - hosts:
        - {{ .Values.ingress.hostname }}
      secretName: {{ .Values.ingress.tls.secretName }}
  {{ end }}
  rules:
    - host: {{ .Values.ingress.hostname }}
      http:
        paths:
          - path: {{ .Values.ingress.path }}
            pathType: ImplementationSpecific
            backend:
              service:
                name: {{ .Release.Name }}-svc
                port:
                  number: {{ .Values.port }}
{{ end }}
{{- end -}}
