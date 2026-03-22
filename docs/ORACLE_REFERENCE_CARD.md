# Oracle Ferrofluid - Quick Reference Card

**Status:** ✅ FULLY OPERATIONAL

## 🚀 ONE-COMMAND RESTART

```bash
~/oracle-restart.sh
```

## 📊 QUICK HEALTH CHECK

```bash
~/ORACLE_QUICK_CHECK.sh
```

## 🎵 HOW TO PLAY MUSIC

1. Open Spotify on phone
2. Play any song
3. Tap device icon → Select "Oracle"
4. LEDs automatically dance! 🎉

## 🎤 VOICE ASSISTANT

Say: "Hey Jarvis" (works even during music!)

## 🔧 QUICK COMMANDS

Restart both services:
```bash
sudo systemctl restart raspotify oracle-master
```

View logs:
```bash
tail -f /tmp/oracle_master.log
```

Check status:
```bash
systemctl status oracle-master raspotify
```

## 🎨 LED STATES

- **IDLE:** Gentle breathing
- **MUSIC:** Audio-reactive (Spotify)
- **LISTENING:** Blue pulse
- **THINKING:** Purple swirl
- **SPEAKING:** Green wave

## 📁 KEY FILES

```
~/oracle-restart.sh           # Quick restart
~/ORACLE_QUICK_CHECK.sh       # Health check
~/ORACLE_UNIFIED_SETUP.md     # Full docs
/tmp/oracle_master.log         # Logs
```

**For full documentation:** `/home/tyahn/ORACLE_UNIFIED_SETUP.md`
