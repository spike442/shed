{{- define "knowledge.labels" -}}
app.kubernetes.io/name: knowledge
app.kubernetes.io/part-of: knowledge
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "knowledge.metadata" -}}
metadata:
  name: {{ .name }}
  namespace: {{ .root.Release.Namespace }}
  labels:
    {{- include "knowledge.labels" .root | nindent 4 }}
{{- end -}}

{{- define "knowledge.domains" -}}
{{- (.Files.Get "config/knowledge.yaml" | fromYaml).domains | toYaml -}}
{{- end -}}
