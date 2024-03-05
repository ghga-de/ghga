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
