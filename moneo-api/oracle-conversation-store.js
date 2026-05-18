/**
 * Oracle Conversation Store — Phase 1 cross-session memory
 *
 * SQLite-backed log of every Realtime API turn (user + assistant).
 * Used to inject recent context into new sessions so "what did I tell you
 * yesterday?" actually works.
 */

const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

class OracleConversationStore {
  constructor(dbPath) {
    this.dbPath = dbPath || path.join(__dirname, '..', '..', 'data', 'oracle-conversations.db');
    fs.mkdirSync(path.dirname(this.dbPath), { recursive: true });
    this.db = new Database(this.dbPath);
    this.db.pragma('journal_mode = WAL');
    this._initSchema();

    this.insertStmt = this.db.prepare(
      'INSERT INTO oracle_conversations (timestamp, session_id, role, content) VALUES (?, ?, ?, ?)'
    );
    this.recentStmt = this.db.prepare(
      'SELECT timestamp, session_id, role, content FROM oracle_conversations WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?'
    );
  }

  _initSchema() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS oracle_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_oracle_timestamp ON oracle_conversations(timestamp DESC);
      CREATE INDEX IF NOT EXISTS idx_oracle_session ON oracle_conversations(session_id, timestamp);
    `);
  }

  log(sessionId, role, content) {
    if (!sessionId || !role || !content) {
      throw new Error('sessionId, role, content all required');
    }
    const r = this.insertStmt.run(Date.now(), sessionId, role, content);
    return r.lastInsertRowid;
  }

  getRecent(hours = 24, limit = 40) {
    const cutoff = Date.now() - hours * 3600 * 1000;
    const rows = this.recentStmt.all(cutoff, limit);
    return rows.reverse(); // oldest first for context
  }

  formatForPrompt(hours = 24, limit = 20) {
    const turns = this.getRecent(hours, limit);
    if (turns.length === 0) return '';
    const lines = turns.map(t => {
      const ts = new Date(t.timestamp).toISOString().replace('T', ' ').slice(0, 16);
      const speaker = t.role === 'user' ? 'Trevor' : 'Oracle';
      const text = t.content.length > 300 ? t.content.slice(0, 300) + '…' : t.content;
      return `[${ts}] ${speaker}: ${text}`;
    });
    return `RECENT CONVERSATION (last ${hours}h, ${turns.length} turns):\n${lines.join('\n')}`;
  }

  close() {
    this.db.close();
  }
}

module.exports = OracleConversationStore;
