{{- define "shed.labels" -}}
app.kubernetes.io/name: shed
app.kubernetes.io/part-of: shed
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "shed.metadata" -}}
metadata:
  name: {{ .name }}
  namespace: {{ .root.Release.Namespace }}
  labels:
    {{- include "shed.labels" .root | nindent 4 }}
{{- end -}}
