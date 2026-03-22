#\!/bin/bash
# Oracle Quick Health Check & Restart Script

echo "=============================================="
echo "  ORACLE FERROFLUID - HEALTH CHECK"
echo "=============================================="
echo

# Check Oracle Master Service
echo "=== 1. Oracle Master Service ==="
if systemctl is-active --quiet oracle-master; then
    echo "OK RUNNING"
    systemctl status oracle-master --no-pager | grep "Active:"
else
    echo "NOT RUNNING"
    echo "   Fix: sudo systemctl start oracle-master"
fi
echo

# Check Raspotify
echo "=== 2. Raspotify ==="
if systemctl is-active --quiet raspotify; then
    echo "OK RUNNING"
    systemctl status raspotify --no-pager | grep "Active:"
else
    echo "NOT RUNNING"
    echo "   Fix: sudo systemctl start raspotify"
fi
echo

# Check volumes
echo "=== 3. Volume Levels ==="
amixer -c 3 get Headphone | grep "Front Left:" | head -1
echo

# Check logs for recent activity
echo "=== 4. Recent Activity ==="
tail -5 /tmp/oracle_master.log 2>/dev/null || echo "No logs available"
echo

echo "=============================================="
echo "  QUICK RESTART COMMANDS"
echo "=============================================="
echo "Restart Oracle Master:"
echo "  sudo systemctl restart oracle-master"
echo
echo "Restart Raspotify:"
echo "  sudo systemctl restart raspotify"
echo
echo "Restart Both:"
echo "  sudo systemctl restart raspotify oracle-master"
echo
echo "View Live Logs:"
echo "  tail -f /tmp/oracle_master.log"
echo "=============================================="
