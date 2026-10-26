{{- define "sentinel.labels" -}}
app.kubernetes.io/name: {{ .component | default .name }}
app.kubernetes.io/part-of: sentinel
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .root.Chart.Name .root.Chart.Version }}
{{- end -}}

{{- define "sentinel.metadata" -}}
metadata:
  name: {{ .name }}
  {{- if not .cluster }}
  namespace: {{ .namespace | default .root.Release.Namespace }}
  {{- end }}
  labels:
    {{- include "sentinel.labels" . | nindent 4 }}
{{- end -}}

{{- define "sentinel.image" -}}
{{ .image.repository }}:{{ .image.tag | default .root.Chart.AppVersion }}
{{- end -}}

{{- define "sentinel.podSecurity" -}}
securityContext:
  runAsNonRoot: true
  runAsUser: 65532
  runAsGroup: 65532
  fsGroup: 65532
  seccompProfile: {type: RuntimeDefault}
{{- end -}}

{{- define "sentinel.containerSecurity" -}}
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: {drop: [ALL]}
{{- end -}}

{{- define "sentinel.secretEnv" -}}
{{- range $name, $key := .env }}
- name: {{ $name }}
  valueFrom: {secretKeyRef: {name: {{ $.root.Values.secret }}, key: {{ $key }}}}
{{- end }}
{{- end -}}

{{- define "sentinel.heartbeat" -}}
livenessProbe:
  exec:
    command: [python, -c, "import os, sys, time; sys.exit(time.time() - os.path.getmtime('{{ .file }}') > {{ .seconds }})"]
  initialDelaySeconds: 60
  periodSeconds: 60
  failureThreshold: 3
{{- end -}}

{{- define "sentinel.clusterIdentity" -}}
{{- $namespace := .root.Release.Namespace -}}
apiVersion: v1
kind: ServiceAccount
{{ include "sentinel.metadata" . }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
{{ include "sentinel.metadata" (merge (dict "cluster" true) .) }}
rules:
{{ toYaml .rules }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
{{ include "sentinel.metadata" (merge (dict "cluster" true) .) }}
roleRef: {apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: {{ .name }}}
subjects: [{kind: ServiceAccount, name: {{ .name }}, namespace: {{ $namespace }}}]
---
apiVersion: v1
kind: ConfigMap
{{ include "sentinel.metadata" (merge (dict "name" (printf "%s-kubeconfig" .name) "component" .name) .) }}
data:
  config: |
    apiVersion: v1
    kind: Config
    clusters:
    - name: in-cluster
      cluster:
        server: https://kubernetes.default.svc
        certificate-authority: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    users:
    - name: {{ .name }}
      user:
        tokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
    contexts:
    - name: {{ .name }}
      context: {cluster: in-cluster, user: {{ .name }}, namespace: {{ $namespace }}}
    current-context: {{ .name }}
{{- end -}}

{{- define "sentinel.deployment" -}}
{{- $root := .root -}}
apiVersion: apps/v1
kind: Deployment
{{ include "sentinel.metadata" . }}
spec:
  replicas: 1
  {{- with .strategy }}
  strategy: {type: {{ . }}}
  {{- end }}
  selector:
    matchLabels: {app.kubernetes.io/name: {{ .name }}}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $root.Template.BasePath "/config.yaml") $root | sha256sum }}
      labels:
        {{- include "sentinel.labels" . | nindent 8 }}
        {{- if .knowledgeClient }}
        shed/knowledge-client: "true"
        {{- end }}
    spec:
      serviceAccountName: {{ .name }}
      automountServiceAccountToken: {{ .kubeconfig | default false }}
      terminationGracePeriodSeconds: {{ .grace }}
      {{- include "sentinel.podSecurity" . | nindent 6 }}
      containers:
      - name: {{ .container }}
        image: {{ include "sentinel.image" (dict "root" $root "image" .image) }}
        imagePullPolicy: IfNotPresent
        command: [python, -m, {{ .module }}]
        {{- with .ports }}
        ports:
          {{- toYaml . | nindent 8 }}
        {{- end }}
        {{- include "sentinel.heartbeat" (dict "file" .heartbeat "seconds" .grace) | nindent 8 }}
        env:
        - {name: HOME, value: /home/sentinel}
        {{- if .kubeconfig }}
        - {name: KUBECONFIG, value: /home/sentinel/.kube/config}
        {{- end }}
        - {name: SENTINEL_KAFKA_USERNAME, value: {{ .kafkaUser | quote }}}
        {{- include "sentinel.secretEnv" (dict "root" $root "env" .secretEnv) | nindent 8 }}
        {{- include "sentinel.containerSecurity" . | nindent 8 }}
        resources:
          {{- toYaml .resources | nindent 10 }}
        volumeMounts:
        - {name: config, mountPath: /etc/sentinel, readOnly: true}
        - {name: home, mountPath: /home/sentinel}
        - {name: tmp, mountPath: /tmp}
        {{- if .kubeconfig }}
        - {name: kubeconfig, mountPath: /home/sentinel/.kube, readOnly: true}
        {{- end }}
        {{- range $volume, $path := .scratch }}
        - {name: {{ $volume }}, mountPath: {{ $path }}}
        {{- end }}
      volumes:
      - {name: config, configMap: {name: sentinel-config}}
      - {name: home, emptyDir: {}}
      - {name: tmp, emptyDir: {}}
      {{- if .kubeconfig }}
      - {name: kubeconfig, configMap: {name: {{ .name }}-kubeconfig, items: [{key: config, path: config}]}}
      {{- end }}
      {{- range $volume, $_ := .scratch }}
      - {name: {{ $volume }}, emptyDir: {}}
      {{- end }}
{{- end -}}
