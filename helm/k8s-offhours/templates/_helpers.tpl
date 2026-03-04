{{- define "k8s-offhours.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "k8s-offhours.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "k8s-offhours.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "k8s-offhours.serviceAccountName" -}}
{{- if .Values.serviceAccount.name -}}
{{- .Values.serviceAccount.name -}}
{{- else -}}
{{- printf "%s-sa" (include "k8s-offhours.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "k8s-offhours.labels" -}}
app.kubernetes.io/name: {{ include "k8s-offhours.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "k8s-offhours.argocdSecretName" -}}
{{- if .Values.argocd.enabled -}}
{{- required "argocd.existingSecret is required when argocd.enabled=true" .Values.argocd.existingSecret -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end -}}
