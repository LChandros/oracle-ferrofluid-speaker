#!/usr/bin/env node
/**
 * Oracle Calendar Watcher — Phase 3 proactive alerts
 *
 * Cron every 2 min. Looks at upcoming Google Calendar events; for any event
 * whose start time is within the 5-min or 15-min countdown window, dispatches
 * an Oracle alert (critical for 5-min, info for 15-min).
 *
 * Idempotent via state file at data/calendar-alerts.state.json:
 *   { fired: { "<eventId>-5min": <expiryTs>, ... } }
 *
 * Install (cron entry, every 2 min):
 *   star/2 star star star star cd /home/moneo/moneo && node scripts/oracle-calendar-watcher.js \
 *     >> data/logs/oracle-calendar-watcher.log 2>&1
 */

const path = require('path');
const fs = require('fs').promises;

require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const calendarManager = require('../core/modules/calendar-manager');
const { getDispatcher } = require('../core/modules/alert-dispatcher');

const STATE_FILE = path.join(__dirname, '..', 'data', 'calendar-alerts.state.json');

// Cron runs every 2 min, so each window must be ≥3 min wide to guarantee a hit.
// 15-min flash: fire when 12 ≤ minutesUntil ≤ 16.
// 5-min  speak: fire when  3 ≤ minutesUntil ≤  6.
const WINDOWS = [
  { kind: '15min', minLo: 12, minHi: 16, severity: 'info',
    speak: e => `Heads up — ${e.summary} starts in fifteen minutes.` },
  { kind: '5min',  minLo:  3, minHi:  6, severity: 'critical',
    speak: e => `Trevor — ${e.summary} starts in five minutes.` },
];

async function loadState() {
  try {
    return JSON.parse(await fs.readFile(STATE_FILE, 'utf8'));
  } catch {
    return { fired: {} };
  }
}

async function saveState(state) {
  // Garbage-collect entries past their expiry so the file doesn't grow forever
  const now = Date.now();
  for (const k of Object.keys(state.fired)) {
    if (state.fired[k] < now) delete state.fired[k];
  }
  await fs.mkdir(path.dirname(STATE_FILE), { recursive: true });
  await fs.writeFile(STATE_FILE, JSON.stringify(state, null, 2));
}

function ts() { return new Date().toISOString(); }

async function main() {
  await calendarManager.init();
  if (!calendarManager.calendar) {
    console.error(`${ts()} calendar not authenticated, aborting`);
    process.exit(1);
  }

  const events = await calendarManager.getUpcomingEvents(20, 1);
  const now = Date.now();
  const dispatcher = getDispatcher();
  const state = await loadState();

  let dispatched = 0;
  for (const ev of events) {
    if (!ev.start || ev.start.length === 10) continue; // skip all-day events (YYYY-MM-DD)
    const startMs = new Date(ev.start).getTime();
    if (isNaN(startMs) || startMs < now) continue;

    const minutesUntil = (startMs - now) / 60000;

    for (const w of WINDOWS) {
      if (minutesUntil < w.minLo || minutesUntil > w.minHi) continue;
      const alertId = `cal-${ev.id}-${w.kind}`;
      if (state.fired[alertId]) continue; // already fired

      await dispatcher.dispatch({
        severity: w.severity,
        source: 'calendar',
        title: `${ev.summary} in ${w.kind === '5min' ? 'five' : 'fifteen'} minutes`,
        message: `Starts at ${new Date(startMs).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' })} ET${ev.location ? ' — ' + ev.location : ''}`,
        spokenMessage: w.speak(ev),
        alertId,
      });
      state.fired[alertId] = startMs + 12 * 3600 * 1000; // keep marker 12h past event
      dispatched++;
      console.log(`${ts()} fired ${alertId} (${w.severity})`);
    }
  }

  await saveState(state);
  console.log(`${ts()} checked ${events.length} events, dispatched ${dispatched}`);
}

main().catch(e => {
  console.error(`${ts()} ERROR:`, e.message);
  process.exit(1);
});
