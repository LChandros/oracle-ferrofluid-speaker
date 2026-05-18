/**
 * Oracle Pending Notification Store — Phase 3 pending-state model
 *
 * SQLite-backed list of info-severity alerts that have been delivered but
 * not yet acknowledged. The Pi polls this every 10 min and pulses the
 * LEDs while anything is pending. Cleared via voice command or nightly sweep.
 *
 * Same pattern as oracle-conversation-store.js.
 */

const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

class OraclePendingStore {
  constructor(dbPath) {
    this.dbPath = dbPath || path.join(__dirname, '..', '..', 'data', 'oracle-pending.db');
    fs.mkdirSync(path.dirname(this.dbPath), { recursive: true });
    this.db = new Database(this.dbPath);
    this.db.pragma('journal_mode = WAL');
    this._initSchema();

    this.insertStmt = this.db.prepare(
      'INSERT INTO pending_notifications (ts, source, title, message, alert_id, severity) VALUES (?, ?, ?, ?, ?, ?)'
    );
    this.activeStmt = this.db.prepare(
      'SELECT id, ts, source, title, message, alert_id, severity FROM pending_notifications WHERE cleared_at IS NULL ORDER BY ts ASC'
    );
    this.clearAllStmt = this.db.prepare(
      'UPDATE pending_notifications SET cleared_at = ? WHERE cleared_at IS NULL'
    );
    this.clearByIdStmt = this.db.prepare(
      'UPDATE pending_notifications SET cleared_at = ? WHERE id = ? AND cleared_at IS NULL'
    );
    this.clearByAlertIdStmt = this.db.prepare(
      'UPDATE pending_notifications SET cleared_at = ? WHERE alert_id = ? AND cleared_at IS NULL'
    );
    this.clearStaleStmt = this.db.prepare(
      'UPDATE pending_notifications SET cleared_at = ? WHERE cleared_at IS NULL AND ts < ?'
    );
  }

  _initSchema() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS pending_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER NOT NULL,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT,
        alert_id TEXT,
        severity TEXT NOT NULL,
        cleared_at INTEGER
      );
      CREATE INDEX IF NOT EXISTS idx_pending_active ON pending_notifications(cleared_at, ts);
      CREATE INDEX IF NOT EXISTS idx_pending_alert_id ON pending_notifications(alert_id);
    `);
  }

  /**
   * Add a pending notification. Idempotent on alert_id —
   * if an alert with the same alert_id is already pending, do nothing.
   */
  add({ source, title, message = '', alert_id = null, severity = 'info' }) {
    if (!source || !title) throw new Error('source and title required');
    if (alert_id) {
      const existing = this.db
        .prepare('SELECT id FROM pending_notifications WHERE alert_id = ? AND cleared_at IS NULL')
        .get(alert_id);
      if (existing) return existing.id;
    }
    const r = this.insertStmt.run(Date.now(), source, title, message, alert_id, severity);
    return r.lastInsertRowid;
  }

  getPending() {
    return this.activeStmt.all();
  }

  clearAll() {
    const r = this.clearAllStmt.run(Date.now());
    return r.changes;
  }

  clearById(id) {
    const r = this.clearByIdStmt.run(Date.now(), id);
    return r.changes;
  }

  clearByAlertId(alertId) {
    const r = this.clearByAlertIdStmt.run(Date.now(), alertId);
    return r.changes;
  }

  /** Clear anything older than `olderThanMs` (used by midnight sweep). */
  clearStale(olderThanMs) {
    const cutoff = Date.now() - olderThanMs;
    const r = this.clearStaleStmt.run(Date.now(), cutoff);
    return r.changes;
  }

  close() {
    this.db.close();
  }
}

let _instance = null;
function getStore() {
  if (!_instance) _instance = new OraclePendingStore();
  return _instance;
}

module.exports = { OraclePendingStore, getStore };
