#!/bin/bash
# Quick Oracle Restart Script

echo 'Restarting Oracle services...'
sudo systemctl restart raspotify
sleep 2
sudo systemctl restart oracle-master
sleep 3

echo
echo '=== Status ==='
systemctl is-active raspotify && echo 'Raspotify: RUNNING' || echo 'Raspotify: FAILED'
systemctl is-active oracle-master && echo 'Oracle Master: RUNNING' || echo 'Oracle Master: FAILED'
echo
echo 'Oracle is ready!'
echo 'Open Spotify on your phone and select "Oracle" device'
