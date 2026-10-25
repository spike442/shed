{{- define "knowledge.configFiles" -}}
{{- $values := .Values -}}
{{- $site := dict
  "clickhouse.yaml" (dict "clickhouse" $values.clickhouse)
  "s3.yaml" (dict "s3" $values.s3)
-}}
{{- $files := dict -}}
{{- range $name := list "logging.yaml" "knowledge.yaml" "clickhouse.yaml" "s3.yaml" -}}
{{- $config := $.Files.Get (printf "config/%s" $name) | fromYaml | default dict -}}
{{- $config = mergeOverwrite $config (index $site $name | default dict) -}}
{{- $_ := set $files $name ($config | toYaml) -}}
{{- end -}}
{{- toYaml $files -}}
{{- end -}}
