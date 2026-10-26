{{- define "shed.configFiles" -}}
{{- $values := .Values -}}
{{- $site := dict
  "agents.yaml" (dict "agents" $values.agents)
  "kafka.yaml" (dict "kafka" (dict "bootstrap_servers" $values.kafka.bootstrapServers "consumer_group" $values.kafka.consumerGroup "topics" $values.kafka.topics))
  "database.yaml" (dict "database" (dict "host" $values.postgres.host "name" $values.postgres.database "user" $values.postgres.user))
-}}
{{- $files := dict "domains.json" (dict "domains" $values.domains | toJson) -}}
{{- range $name := list "logging.yaml" "agents.yaml" "repositories.yaml" "kafka.yaml" "database.yaml" -}}
{{- $config := $.Files.Get (printf "config/%s" $name) | fromYaml | default dict -}}
{{- $config = mergeOverwrite $config (index $site $name | default dict) -}}
{{- $_ := set $files $name ($config | toYaml) -}}
{{- end -}}
{{- toYaml $files -}}
{{- end -}}
