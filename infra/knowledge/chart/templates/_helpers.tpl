{{- define "knowledge.standardLabels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name (.Chart.Version | replace "+" "_") | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/part-of: knowledge
{{- end -}}

{{- define "knowledge.domains" -}}
{{- (.Files.Get "config/knowledge.yaml" | fromYaml).domains | toYaml -}}
{{- end -}}
