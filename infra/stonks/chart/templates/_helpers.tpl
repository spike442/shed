{{- define "stonks.labels" -}}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/part-of: stonks
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .root.Chart.Name .root.Chart.Version }}
{{- end -}}

{{- define "stonks.metadata" -}}
metadata:
  name: {{ .name }}
  namespace: {{ .root.Release.Namespace }}
  labels:
    {{- include "stonks.labels" (dict "root" .root "component" (.component | default .name)) | nindent 4 }}
{{- end -}}

{{- define "stonks.role" -}}
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
{{ include "stonks.metadata" . }}
rules:
{{ toYaml .rules }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
{{ include "stonks.metadata" . }}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: Role, name: {{ .name }}}
subjects: [{kind: ServiceAccount, name: {{ .account }}, namespace: {{ .accountNamespace | default .root.Release.Namespace }}}]
{{- end -}}
