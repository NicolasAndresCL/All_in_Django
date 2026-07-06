{{/* Nombre base del release */}}
{{- define "aid.fullname" -}}
{{- default .Release.Name .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Etiquetas comunes */}}
{{- define "aid.labels" -}}
app.kubernetes.io/name: all-in-django
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{/* Repos de imágenes */}}
{{- define "aid.apiImage" -}}
{{ .Values.image.registry }}/{{ .Values.image.owner }}/all-in-django-api:{{ .Values.image.tag }}
{{- end -}}
{{- define "aid.uiImage" -}}
{{ .Values.image.registry }}/{{ .Values.image.owner }}/all-in-django-ui:{{ .Values.image.tag }}
{{- end -}}

{{/* DATABASE_URL: calculada desde el Postgres embebido, o la provista en secret.databaseUrl */}}
{{- define "aid.databaseUrl" -}}
{{- if .Values.postgres.enabled -}}
postgres://{{ .Values.postgres.user }}:{{ .Values.postgres.password }}@{{ include "aid.fullname" . }}-postgres:5432/{{ .Values.postgres.database }}
{{- else -}}
{{ required "secret.databaseUrl es obligatorio cuando postgres.enabled=false" .Values.secret.databaseUrl }}
{{- end -}}
{{- end -}}
