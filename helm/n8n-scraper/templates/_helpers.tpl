{{/*
Expand the name of the chart.
*/}}
{{- define "n8n-scraper.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "n8n-scraper.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "n8n-scraper.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "n8n-scraper.labels" -}}
helm.sh/chart: {{ include "n8n-scraper.chart" . }}
{{ include "n8n-scraper.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "n8n-scraper.selectorLabels" -}}
app.kubernetes.io/name: {{ include "n8n-scraper.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "n8n-scraper.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "n8n-scraper.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the API service account to use
*/}}
{{- define "n8n-scraper.apiServiceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- printf "%s-api" (include "n8n-scraper.fullname" .) }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the worker service account to use
*/}}
{{- define "n8n-scraper.workerServiceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- printf "%s-worker" (include "n8n-scraper.fullname" .) }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the monitoring service account to use
*/}}
{{- define "n8n-scraper.monitoringServiceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- printf "%s-monitoring" (include "n8n-scraper.fullname" .) }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate the database URL
*/}}
{{- define "n8n-scraper.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "postgresql://%s:%s@%s:%d/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password (include "postgresql.primary.fullname" .Subcharts.postgresql) (.Values.postgresql.primary.service.ports.postgresql | int) .Values.postgresql.auth.database }}
{{- else }}
{{- .Values.secrets.databaseUrl }}
{{- end }}
{{- end }}

{{/*
Generate the Redis URL
*/}}
{{- define "n8n-scraper.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- if .Values.redis.auth.enabled }}
{{- printf "redis://:%s@%s:%d" .Values.redis.auth.password (include "redis.fullname" .Subcharts.redis) (.Values.redis.master.service.ports.redis | int) }}
{{- else }}
{{- printf "redis://%s:%d" (include "redis.fullname" .Subcharts.redis) (.Values.redis.master.service.ports.redis | int) }}
{{- end }}
{{- else }}
{{- .Values.secrets.redisUrl }}
{{- end }}
{{- end }}

{{/*
Generate the ChromaDB URL
*/}}
{{- define "n8n-scraper.chromadbUrl" -}}
{{- if .Values.chromadb.enabled }}
{{- printf "http://%s:%d" (printf "%s-chromadb" (include "n8n-scraper.fullname" .)) (.Values.chromadb.service.port | int) }}
{{- else }}
{{- .Values.secrets.chromadbUrl }}
{{- end }}
{{- end }}

{{/*
Generate resource limits
*/}}
{{- define "n8n-scraper.resources" -}}
{{- if .resources }}
resources:
  {{- if .resources.limits }}
  limits:
    {{- if .resources.limits.cpu }}
    cpu: {{ .resources.limits.cpu }}
    {{- end }}
    {{- if .resources.limits.memory }}
    memory: {{ .resources.limits.memory }}
    {{- end }}
  {{- end }}
  {{- if .resources.requests }}
  requests:
    {{- if .resources.requests.cpu }}
    cpu: {{ .resources.requests.cpu }}
    {{- end }}
    {{- if .resources.requests.memory }}
    memory: {{ .resources.requests.memory }}
    {{- end }}
  {{- end }}
{{- end }}
{{- end }}

{{/*
Generate security context
*/}}
{{- define "n8n-scraper.securityContext" -}}
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop:
    - ALL
{{- end }}

{{/*
Generate pod security context
*/}}
{{- define "n8n-scraper.podSecurityContext" -}}
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
{{- end }}

{{/*
Generate common environment variables
*/}}
{{- define "n8n-scraper.commonEnv" -}}
- name: ENVIRONMENT
  value: {{ .Values.config.app.environment | quote }}
- name: LOG_LEVEL
  value: {{ .Values.config.logging.level | quote }}
- name: METRICS_ENABLED
  value: {{ .Values.config.monitoring.metricsEnabled | quote }}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "n8n-scraper.fullname" . }}-secrets
      key: database-url
- name: REDIS_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "n8n-scraper.fullname" . }}-secrets
      key: redis-url
- name: CHROMADB_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "n8n-scraper.fullname" . }}-secrets
      key: chromadb-url
{{- end }}

{{/*
Generate common volume mounts
*/}}
{{- define "n8n-scraper.commonVolumeMounts" -}}
- name: data-storage
  mountPath: /app/data
- name: config-volume
  mountPath: /app/config
  readOnly: true
- name: tmp-volume
  mountPath: /tmp
{{- end }}

{{/*
Generate common volumes
*/}}
{{- define "n8n-scraper.commonVolumes" -}}
- name: data-storage
  {{- if .Values.persistence.enabled }}
  persistentVolumeClaim:
    claimName: {{ include "n8n-scraper.fullname" . }}-data
  {{- else }}
  emptyDir: {}
  {{- end }}
- name: config-volume
  configMap:
    name: {{ include "n8n-scraper.fullname" . }}-config
- name: tmp-volume
  emptyDir: {}
{{- end }}