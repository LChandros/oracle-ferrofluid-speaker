#!/bin/bash
# Oracle Ferrofluid Speaker — dead-mans-switch
# Phase 0: pages Discord print-farm channel if Pi heartbeats stop for >STALE_THRESHOLD_SEC.
#
# Run via cron every 5 min:
#   */5 * * * * /home/moneo/moneo/scripts/oracle-heartbeat-watcher.sh >> /home/moneo/moneo/data/logs/oracle-watchdog.log 2>&1

set -euo pipefail

cd /home/moneo/moneo
set -a; source .env; set +a

NTFY_URL="${NTFY_URL:-http://100.68.141.121:2586}"
USER="${NTFY_WATCHDOG_USER:-oracle-watchdog}"
PASS="${NTFY_WATCHDOG_PASSWORD:?missing}"
TOPIC="moneo-oracle-heartbeat"
STALE_THRESHOLD_SEC=900   # 15 min (heartbeat interval is 5 min, so allow 3 misses)
STATE_FILE="/tmp/oracle-watchdog.state"

now=$(date +%s)
log() { echo "$(date -Iseconds) $*"; }

# Pull most-recent message
latest_json=$(curl -fsS -u "${USER}:${PASS}" \
  "${NTFY_URL}/${TOPIC}/json?poll=1&since=1h" 2>/dev/null \
  | tail -1 || echo '')

if [[ -z "$latest_json" ]]; then
  last_seen=0
else
  last_seen=$(echo "$latest_json" | grep -oE '"time":[0-9]+' | head -1 | cut -d: -f2)
fi

age=$(( now - last_seen ))
log "last heartbeat ${age}s ago (threshold ${STALE_THRESHOLD_SEC}s)"

if (( age > STALE_THRESHOLD_SEC )); then
  # Don't spam — only alert once per stale window
  last_alert_at=0
  [[ -f "$STATE_FILE" ]] && last_alert_at=$(cat "$STATE_FILE")
  if (( now - last_alert_at > 1800 )); then  # 30 min between alerts
    log "ALERTING (last alert ${last_alert_at})"
    node -e "
      require('dotenv').config();
      const { notify } = require('./core/utils/notify');
      notify('oracle-alerts', {
        title: 'Oracle DOWN',
        message: 'Pi heartbeat stale for $(( age / 60 )) min. Check ssh tyahn@100.82.131.122',
        severity: 'critical'
      }).then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
    "
    echo "$now" > "$STATE_FILE"
  else
    log "stale but recently alerted, skipping"
  fi
else
  # Clear state when healthy
  rm -f "$STATE_FILE"
fi
