#!/usr/bin/env bash
# Create or update the Tilthwave folder, the four alert rules and the operations dashboard in a
# Grafana (Cloud or self-hosted) through its HTTP API, so the alerting setup lives in git and is
# reproducible. Idempotent: rules are matched by title, the dashboard by uid.
#
#   GRAFANA_URL=https://<stack>.grafana.net GRAFANA_TOKEN=<service account token: Editor> \
#   ALERT_EMAIL=you@example.com deploy/grafana/push.sh
#
# ALERT_EMAIL is optional: with it, an email contact point is created and made the default
# notification policy (Grafana Cloud sends it from its own relay); without it, the rules exist and
# route to whatever the stack's default contact point is.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
: "${GRAFANA_URL:?GRAFANA_URL is required}"
: "${GRAFANA_TOKEN:?GRAFANA_TOKEN is required (service account token with the Editor role)}"

api() { # method path [json]
  local method=$1 path=$2 body=${3:-}
  curl -fsS -X "$method" "$GRAFANA_URL$path" \
    -H "Authorization: Bearer $GRAFANA_TOKEN" -H "Content-Type: application/json" -H "X-Disable-Provenance: true" \
    ${body:+--data "$body"}
}

folder_uid=$(api GET /api/folders | python3 -c 'import sys,json;print(next((f["uid"] for f in json.load(sys.stdin) if f["title"]=="Tilthwave"),""))')
if [ -z "$folder_uid" ]; then
  folder_uid=$(api POST /api/folders '{"title":"Tilthwave"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["uid"])')
  echo "folder created ($folder_uid)"
fi

if [ -n "${ALERT_EMAIL:-}" ]; then
  if ! api GET /api/v1/provisioning/contact-points | grep -q '"name":"tilthwave-email"'; then
    api POST /api/v1/provisioning/contact-points "{\"name\":\"tilthwave-email\",\"type\":\"email\",\"settings\":{\"addresses\":\"$ALERT_EMAIL\"}}" >/dev/null
    echo "contact point tilthwave-email created"
  fi
  api PUT /api/v1/provisioning/policies '{"receiver":"tilthwave-email","group_by":["alertname","site"],"group_wait":"30s","group_interval":"5m","repeat_interval":"4h"}' >/dev/null
  echo "default notification policy -> tilthwave-email"
fi

existing=$(api GET /api/v1/provisioning/alert-rules)
python3 - "$folder_uid" "$existing" "$here/alert-rules.json" <<'PY' | while IFS=$'\t' read -r method path body; do api "$method" "$path" "$body" >/dev/null; echo "$method $path"; done
import json, sys
folder, existing, rules_path = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
by_title = {r["title"]: r["uid"] for r in existing}
for rule in json.load(open(rules_path)):
    rule = {**rule, "folderUID": folder, "orgID": 1}
    uid = by_title.get(rule["title"])
    if uid:
        print("PUT", f"/api/v1/provisioning/alert-rules/{uid}", json.dumps({**rule, "uid": uid}), sep="\t")
    else:
        print("POST", "/api/v1/provisioning/alert-rules", json.dumps(rule), sep="\t")
PY

dashboard=$(python3 -c 'import json,sys;print(json.dumps({"dashboard": json.load(open(sys.argv[1])), "folderUid": sys.argv[2], "overwrite": True}))' "$here/dashboard.json" "$folder_uid")
api POST /api/dashboards/db "$dashboard" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("dashboard", d.get("status"), d.get("url"))'
