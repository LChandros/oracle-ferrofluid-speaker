/**
 * Alert Dispatcher — Phase 3 proactive alerts
 *
 * Publishes alerts to ntfy topic moneo-oracle-alerts. The Pi long-polls
 * that topic and speaks/flashes based on severity:
 *   - critical → spoken immediately via Piper TTS (interrupts music)
 *   - info     → LED flash + queued for next wake-word session
 *
 * Idempotency is the caller's job: pass a stable alertId for any alert
 * that could fire repeatedly (e.g. calendar event countdowns).
 */

const logger = require('../utils/logger');
const { getStore } = require('./oracle-pending-store');

const NTFY_URL = process.env.NTFY_URL || 'http://100.68.141.121:2586';
const NTFY_TOPIC = process.env.NTFY_ALERTS_TOPIC || 'moneo-oracle-alerts';
const NTFY_USER = process.env.NTFY_MONEO_USER || 'moneo';
const NTFY_PASS = process.env.NTFY_MONEO_PASSWORD;

class AlertDispatcher {
  constructor() {
    this.url = `${NTFY_URL.replace(/\/$/, '')}/${NTFY_TOPIC}`;
    this.auth = NTFY_USER && NTFY_PASS
      ? 'Basic ' + Buffer.from(`${NTFY_USER}:${NTFY_PASS}`).toString('base64')
      : null;
  }

  /**
   * Dispatch an alert to the Pi.
   * @param {object} alert
   * @param {'critical'|'info'} alert.severity
   * @param {string} alert.source           e.g. 'calendar', 'clam-po'
   * @param {string} alert.title            short label
   * @param {string} alert.message          what triggered (for log)
   * @param {string} [alert.spokenMessage]  what Oracle should say (defaults to title + message)
   * @param {string} [alert.alertId]        idempotency key (one ntfy msg per id)
   */
  async dispatch({ severity, source, title, message, spokenMessage, alertId }) {
    if (!severity || !source || !title) {
      throw new Error('severity, source, title required');
    }
    if (!['critical', 'info'].includes(severity)) {
      throw new Error(`severity must be 'critical' or 'info', got '${severity}'`);
    }

    const payload = {
      severity,
      source,
      title,
      message: message || '',
      spoken_message: spokenMessage || `${title}. ${message || ''}`.trim(),
      alert_id: alertId || `${source}-${Date.now()}`,
      ts: Date.now(),
    };

    const headers = {
      'Content-Type': 'application/json',
      'Title': `Oracle: ${title}`,
      // ntfy priority — critical = 5 (max), info = 3 (default)
      'Priority': severity === 'critical' ? '5' : '3',
      'Tags': severity === 'critical' ? 'rotating_light' : 'speech_balloon',
    };
    if (this.auth) headers['Authorization'] = this.auth;

    try {
      const r = await fetch(this.url, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      if (!r.ok) {
        const text = await r.text();
        logger.error(`[AlertDispatcher] ntfy HTTP ${r.status}: ${text.slice(0, 200)}`);
        return false;
      }
      // Info alerts persist in the pending store until acknowledged (voice or midnight sweep).
      // Critical alerts are spoken immediately and don't live in the store.
      if (severity === 'info') {
        try {
          getStore().add({ source, title, message: message || '', alert_id: payload.alert_id, severity });
        } catch (e) {
          logger.warn(`[AlertDispatcher] pending-store add failed (non-fatal): ${e.message}`);
        }
      }
      logger.info(`[AlertDispatcher] ${severity} alert dispatched: ${source} — ${title}`);
      return true;
    } catch (err) {
      logger.error(`[AlertDispatcher] dispatch failed: ${err.message}`);
      return false;
    }
  }
}

// Singleton — there's only one Pi listening
let _instance = null;
function getDispatcher() {
  if (!_instance) _instance = new AlertDispatcher();
  return _instance;
}

module.exports = { AlertDispatcher, getDispatcher };
