/**
 * Voice Integration Module
 *
 * Provides HTTP API for the Python voice assistant service to interact with Moneo Core.
 * Similar to api-integration.js but optimized for voice conversations.
 *
 * Features:
 * - REST API endpoints for voice chat
 * - Conversation history management (channelId: 'voice')
 * - Full Moneo context integration (projects, tasks, calendar)
 * - Claude API integration with voice-optimized prompts
 */

const express = require('express');
const bodyParser = require('body-parser');
const Anthropic = require('@anthropic-ai/sdk');
const logger = require('../utils/logger');
const OracleConversationStore = require('./oracle-conversation-store');

class VoiceIntegration {
  constructor(config, tasksManager, calendarManager, projectManager, notesManager, emailManager, systemStateManager, emailReader) {
    this.config = config;
    this.tasksManager = tasksManager;
    this.calendarManager = calendarManager;
    this.projectManager = projectManager;
    this.notesManager = notesManager;
    this.emailManager = emailManager;
    this.emailReader = emailReader || emailManager; // For inbox reads (Trevor's), falls back to default
    this.systemStateManager = systemStateManager;
    this.morningBriefing = null; // Set by moneo-core after initialization
    this.meetingScheduler = null; // Set by moneo-core after initialization

    // API configuration
    this.port = config.voiceAssistant?.port || 3002;
    this.apiKey = config.voiceAssistant?.apiKey || 'moneo-voice-assistant-key';
    this.model = config.voiceAssistant?.model || config.model || 'claude-3-haiku-20240307';
    this.maxTokens = config.voiceAssistant?.maxTokens || config.maxTokens || 2048;

    // Initialize Claude client
    this.anthropic = new Anthropic({
      apiKey: config.anthropicApiKey
    });

    // Conversation history (similar to Discord integration)
    // Key: sessionId, Value: array of messages
    this.conversationHistory = new Map();
    this.maxHistoryLength = 20;

    // Phase 1: persistent cross-session conversation log for Oracle
    this.oracleStore = new OracleConversationStore();

    // Tools for Claude
    this.tools = [
      {
        name: 'web_search',
        description: 'Search the web for current information like weather, news, or facts. Use this when you need up-to-date information.',
        input_schema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'The search query'
            }
          },
          required: ['query']
        }
      },
      {
        name: 'get_calendar_events',
        description: 'Get events from Trevor\'s Google Calendar. ALWAYS use this tool for any calendar questions - never guess or make up calendar data.',
        input_schema: {
          type: 'object',
          properties: {
            time_range: {
              type: 'string',
              enum: ['today', 'tomorrow', 'week'],
              description: 'Time range to check: today, tomorrow, or this week'
            }
          },
          required: ['time_range']
        }
      },
      {
        name: 'get_emails',
        description: 'Get recent emails from Trevor\'s inbox. Use this for any email-related questions.',
        input_schema: {
          type: 'object',
          properties: {
            count: {
              type: 'number',
              description: 'Number of recent emails to fetch (default 5)'
            },
            unread_only: {
              type: 'boolean',
              description: 'Only show unread emails (default true)'
            }
          }
        }
      },
      {
        name: 'schedule_meeting',
        description: 'Schedule a meeting between Trevor and Moneo. Use this when Trevor wants to schedule a meeting, review, check-in, or discussion. Examples: "schedule a meeting for friday at 2 to discuss YFP financials", "set up a weekly GPJ review on Mondays at 10".',
        input_schema: {
          type: 'object',
          properties: {
            request: {
              type: 'string',
              description: 'The natural language meeting request exactly as Trevor stated it'
            }
          },
          required: ['request']
        }
      }
    ];

    // Express app
    this.app = null;
    this.server = null;

    logger.info('Voice Integration module created');
  }

  async initialize() {
    try {
      // Create Express app
      this.app = express();
      this.app.use(bodyParser.json());

      // CORS for local development
      this.app.use((req, res, next) => {
        res.header('Access-Control-Allow-Origin', '*');
        res.header('Access-Control-Allow-Headers', 'Content-Type, X-API-Key');
        res.header('Access-Control-Allow-Methods', 'GET, POST, DELETE');
        next();
      });

      // API Key middleware
      this.app.use((req, res, next) => {
        // Skip auth for status endpoint
        if (req.path === '/api/voice/status') {
          return next();
        }

        const apiKey = req.headers['x-api-key'] || req.headers['authorization']?.replace('Bearer ', '');
        if (!apiKey || apiKey !== this.apiKey) {
          return res.status(401).json({ error: 'Invalid API key' });
        }
        next();
      });

      // Register routes
      this.registerRoutes();

      // Start server
      this.server = this.app.listen(this.port, () => {
        logger.info(`Voice Integration API listening on port ${this.port}`);
      });
      this.server.on('error', (err) => {
        if (err.code === 'EADDRINUSE') {
          logger.warn(`Voice Integration: Port ${this.port} in use, retrying in 5s...`);
          setTimeout(() => {
            this.server.close();
            this.server = this.app.listen(this.port, () => {
              logger.info(`Voice Integration API listening on port ${this.port} (retry)`);
            });
          }, 5000);
        } else {
          logger.error('Voice Integration server error:', err);
        }
      });

      logger.info('Voice Integration initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Voice Integration:', error);
      throw error;
    }
  }

  registerRoutes() {
    // Status endpoint (no auth required)
    this.app.get('/api/voice/status', (req, res) => {
      res.json({
        status: 'ready',
        model: this.model,
        maxTokens: this.maxTokens,
        uptime: process.uptime()
      });
    });

    // Voice capture — real-time task/commitment/note tracking from Oracle
    this.app.post('/api/voice/capture', async (req, res) => {
      try {
        const { type, text, project } = req.body;
        if (!type || !text) {
          return res.status(400).json({ error: 'type and text required' });
        }

        const fs = require('fs').promises;
        const path = require('path');
        const results = { type, text, actions: [] };

        // 1. Add tasks and commitments to the punch list
        if ((type === 'task' || type === 'commitment') && this.punchListManager) {
          const context = project || 'Personal';
          await this.punchListManager.addItem(text, context);
          results.actions.push(`Added to punch list (${context})`);
          logger.info(`[Voice Capture] Added ${type} to punch list: "${text}" [${context}]`);
        }

        // 2. Handle completions — search punch list and constraint dashboard
        if (type === 'complete' || (type === 'note' && /taken care of|done|finished|completed|remove|resolved/i.test(text))) {
          let matched = false;

          // Try to match and complete a punch list item
          if (this.punchListManager) {
            const pending = this.punchListManager.getPendingItems();
            const Anthropic = require('@anthropic-ai/sdk');
            const anthropic = new Anthropic({ apiKey: this.config.anthropicApiKey || process.env.ANTHROPIC_API_KEY });

            if (pending.length > 0) {
              const matchResp = await anthropic.messages.create({
                model: 'claude-haiku-4-5-20251001',
                max_tokens: 100,
                messages: [{
                  role: 'user',
                  content: `Trevor said this is done: "${text}"\n\nWhich of these items (if any) is he referring to? Return ONLY the index number (0-based), or "none" if no match.\n\n${pending.map((p, i) => `${i}: ${p.description}`).join('\n')}`
                }]
              });
              const matchText = (matchResp.content[0]?.text || '').trim();
              const matchIdx = parseInt(matchText);
              if (!isNaN(matchIdx) && matchIdx >= 0 && matchIdx < pending.length) {
                const item = pending[matchIdx];
                await this.punchListManager.completeItem(item.id);
                results.actions.push(`Completed punch list item: ${item.description}`);
                logger.info(`[Voice Capture] Completed punch list item: ${item.description}`);
                matched = true;
              }
            }
          }

          // Try to match constraint dashboard items via Claude
          const dashPath = path.join(__dirname, '../../data/context/constraint-dashboard.json');
          try {
            const dashRaw = await fs.readFile(dashPath, 'utf8');
            const dash = JSON.parse(dashRaw);
            let dashChanged = false;

            // Build list of all matchable items
            const matchableItems = [];
            for (const w of (dash.waitingOn || [])) {
              matchableItems.push({ source: 'waitingOn', id: w.id, desc: w.description });
            }
            for (const goal of (dash.activeGoals || [])) {
              matchableItems.push({ source: 'goal', id: goal.id, desc: goal.name });
              for (const b of (goal.blockers || [])) {
                matchableItems.push({ source: 'blocker', goalId: goal.id, desc: b });
              }
            }

            if (matchableItems.length > 0) {
              const Anthropic = require('@anthropic-ai/sdk');
              const anthropic = new Anthropic({ apiKey: this.config.anthropicApiKey || process.env.ANTHROPIC_API_KEY });
              const dashMatchResp = await anthropic.messages.create({
                model: 'claude-haiku-4-5-20251001',
                max_tokens: 200,
                messages: [{
                  role: 'user',
                  content: `Trevor said this is done/resolved: "${text}"\n\nWhich of these items (if any) match what he's referring to? Return ONLY a JSON array of matching indices (0-based), or [] if none match.\n\n${matchableItems.map((m, i) => `${i}: [${m.source}] ${m.desc}`).join('\n')}`
                }]
              });
              const dashMatchText = (dashMatchResp.content[0]?.text || '[]').trim();
              let matchIndices = [];
              try {
                const jsonMatch = dashMatchText.match(/\[[\d,\s]*\]/);
                if (jsonMatch) matchIndices = JSON.parse(jsonMatch[0]);
              } catch {}

              for (const idx of matchIndices) {
                const item = matchableItems[idx];
                if (!item) continue;

                if (item.source === 'waitingOn') {
                  dash.waitingOn = dash.waitingOn.filter(w => w.id !== item.id);
                  results.actions.push(`Removed waiting-on: ${item.desc}`);
                  logger.info(`[Voice Capture] Removed waiting-on: ${item.desc}`);
                  dashChanged = true;
                } else if (item.source === 'blocker') {
                  const goal = dash.activeGoals.find(g => g.id === item.goalId);
                  if (goal) {
                    goal.blockers = goal.blockers.filter(b => b !== item.desc);
                    results.actions.push(`Removed blocker from ${goal.name}: ${item.desc}`);
                    logger.info(`[Voice Capture] Removed blocker from ${goal.name}: ${item.desc}`);
                    dashChanged = true;
                  }
                } else if (item.source === 'goal') {
                  // Archive the goal
                  dash.activeGoals = dash.activeGoals.filter(g => g.id !== item.id);
                  if (!dash.archivedGoals) dash.archivedGoals = [];
                  dash.archivedGoals.push({ id: item.id, name: item.desc, reason: 'Completed (voice)', archivedDate: new Date().toISOString().split('T')[0] });
                  results.actions.push(`Archived goal: ${item.desc}`);
                  logger.info(`[Voice Capture] Archived goal: ${item.desc}`);
                  dashChanged = true;
                }
              }
            }

            if (dashChanged) {
              dash.lastUpdated = new Date().toISOString();
              await fs.writeFile(dashPath, JSON.stringify(dash, null, 2));
              results.actions.push('Constraint dashboard updated');
            }
          } catch (e) {
            logger.warn(`[Voice Capture] Dashboard update failed: ${e.message}`);
          }
        }

        // 3. Always log to today's vault transcript
        const dateStr = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
        const vaultPath = `/home/moneo/vault/moneo/briefings/${dateStr}.md`;
        try {
          let existing = '';
          try { existing = await fs.readFile(vaultPath, 'utf8'); } catch {}

          const timestamp = new Date().toLocaleTimeString('en-US', {
            hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'America/New_York'
          });
          const entry = `- **${type}** (${timestamp}): ${text}\n`;

          if (existing.includes('## Voice Captures')) {
            existing = existing.replace('## Voice Captures\n', `## Voice Captures\n${entry}`);
          } else {
            existing += `\n## Voice Captures\n${entry}`;
          }
          await fs.writeFile(vaultPath, existing);
        } catch (e) {
          logger.warn(`[Voice Capture] Vault write failed: ${e.message}`);
        }

        logger.info(`[Voice Capture] Processed: type=${type}, actions=${results.actions.length}`);
        res.json({ success: true, ...results });
      } catch (error) {
        logger.error('[Voice Capture] Error:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // Get punch list tasks
    this.app.get('/api/voice/tasks', async (req, res) => {
      try {
        if (!this.punchListManager) {
          return res.status(503).json({ error: 'Punch list not available' });
        }
        const items = this.punchListManager.getPendingItems();
        const grouped = this.punchListManager.getPendingByContext();
        res.json({ success: true, count: items.length, items, grouped });
      } catch (error) {
        logger.error('[Voice] Tasks fetch error:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // Chat endpoint
    this.app.post('/api/voice/chat', async (req, res) => {
      try {
        const { text, userId = 'voice-user', sessionId = 'default' } = req.body;

        if (!text || typeof text !== 'string') {
          return res.status(400).json({ error: 'Missing or invalid "text" field' });
        }

        logger.info(`[Voice] Received: "${text}" (session: ${sessionId})`);

        // Process the message
        const response = await this.handleVoiceMessage(text, userId, sessionId);

        logger.info(`[Voice] Response: "${response.text.substring(0, 100)}..."`);

        res.json(response);
      } catch (error) {
        logger.error('[Voice] Error processing message:', error);
        res.status(500).json({
          error: 'Internal server error',
          message: error.message
        });
      }
    });

    // Clear conversation history
    this.app.post('/api/voice/clear', async (req, res) => {
      try {
        const { sessionId = 'default' } = req.body;
        this.conversationHistory.delete(sessionId);
        logger.info(`[Voice] Cleared conversation history for session: ${sessionId}`);
        res.json({ success: true, message: 'Conversation history cleared' });
      } catch (error) {
        logger.error('[Voice] Error clearing history:', error);
        res.status(500).json({ error: 'Internal server error' });
      }
    });

    // Get conversation history
    this.app.get('/api/voice/history/:sessionId', async (req, res) => {
      try {
        const { sessionId } = req.params;
        const history = this.conversationHistory.get(sessionId) || [];
        res.json({ sessionId, messages: history, count: history.length });
      } catch (error) {
        logger.error('[Voice] Error getting history:', error);
        res.status(500).json({ error: 'Internal server error' });
      }
    });

    // Create calendar event
    this.app.post('/api/voice/calendar/create', async (req, res) => {
      try {
        const { summary, description, startTime, endTime, timeZone, location } = req.body;

        if (!summary || !startTime) {
          return res.status(400).json({ error: 'Missing required fields: summary, startTime' });
        }

        if (!this.calendarManager) {
          return res.status(503).json({ error: 'Calendar manager not available' });
        }

        // Default endTime to 1 hour after startTime if not provided
        const start = new Date(startTime);
        const end = endTime ? new Date(endTime) : new Date(start.getTime() + 60 * 60 * 1000);

        // Write to Trevor's personal calendar (tyahn96@gmail.com), not the default
        const eventResource = {
          summary,
          description: description || '',
          location: location || '',
          start: {
            dateTime: start.toISOString(),
            timeZone: timeZone || 'America/New_York'
          },
          end: {
            dateTime: end.toISOString(),
            timeZone: timeZone || 'America/New_York'
          }
        };

        const event = await this.calendarManager.calendar.events.insert({
          calendarId: 'tyahn96@gmail.com',
          resource: eventResource,
          sendUpdates: 'none'
        });

        logger.info(`[Voice] Calendar event created: "${summary}" at ${startTime}`);
        res.json({ success: true, event });
      } catch (error) {
        logger.error('[Voice] Error creating calendar event:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // Get calendar events (direct, no Claude)
    this.app.get('/api/voice/calendar/events', async (req, res) => {
      try {
        if (!this.calendarManager) {
          return res.status(503).json({ error: 'Calendar manager not available' });
        }

        const range = req.query.range || 'today';
        // Use EST/EDT (Trevor's timezone) not server UTC
        const estNow = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
        let startDate, endDate;

        if (range === 'today') {
          startDate = new Date(estNow.getFullYear(), estNow.getMonth(), estNow.getDate());
          endDate = new Date(startDate);
          endDate.setDate(endDate.getDate() + 1);
        } else if (range === 'tomorrow') {
          startDate = new Date(estNow.getFullYear(), estNow.getMonth(), estNow.getDate() + 1);
          endDate = new Date(startDate);
          endDate.setDate(endDate.getDate() + 1);
        } else {
          startDate = new Date(estNow.getFullYear(), estNow.getMonth(), estNow.getDate());
          endDate = new Date(startDate);
          endDate.setDate(endDate.getDate() + 7);
        }

        // Query Trevor's personal calendar directly (not oracle@moneo.agency default)
        const calResponse = await this.calendarManager.calendar.events.list({
          calendarId: 'tyahn96@gmail.com',
          timeMin: startDate.toISOString(),
          timeMax: endDate.toISOString(),
          maxResults: 20,
          singleEvents: true,
          orderBy: 'startTime'
        });
        const filtered = calResponse.data.items || [];

        const formatted = filtered.map(e => ({
          summary: e.summary,
          start: e.start?.dateTime || e.start?.date,
          end: e.end?.dateTime || e.end?.date,
          location: e.location || null,
          description: e.description || null,
          attendees: (e.attendees || []).map(a => a.email).join(', ') || null
        }));

        logger.info(`[Voice] Calendar query (${range}): ${formatted.length} events`);
        res.json({ range, count: formatted.length, events: formatted });
      } catch (error) {
        logger.error('[Voice] Error getting calendar events:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // Send email
    this.app.post('/api/voice/email/send', async (req, res) => {
      try {
        const { to, subject, body, isHtml } = req.body;

        if (!to || !subject || !body) {
          return res.status(400).json({ error: 'Missing required fields: to, subject, body' });
        }

        if (!this.emailManager) {
          return res.status(503).json({ error: 'Email manager not available' });
        }

        await this.emailManager.sendEmail({
          to,
          subject,
          body,
          isHtml: isHtml || false
        });

        logger.info(`[Voice] Email sent to ${to}: "${subject}"`);
        res.json({ success: true, message: `Email sent to ${to}` });
      } catch (error) {
        logger.error('[Voice] Error sending email:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // Morning briefing - generate now
    this.app.post('/api/voice/briefing/generate', async (req, res) => {
      try {
        if (!this.morningBriefing) {
          return res.status(503).json({ error: 'Morning briefing module not available' });
        }
        const result = await this.morningBriefing.generate();
        res.json({ success: true, briefing: result });
      } catch (error) {
        logger.error('[Voice] Briefing generation error:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // Morning briefing - get today's briefing
    // Check-in transcript extraction — extracts commitments, tasks, and notes from Q&A
    this.app.post('/api/voice/checkin/extract', async (req, res) => {
      try {
        const { transcript } = req.body;
        if (!transcript || !Array.isArray(transcript) || transcript.length === 0) {
          return res.status(400).json({ error: 'No transcript provided' });
        }

        const Anthropic = require('@anthropic-ai/sdk');
        const anthropic = new Anthropic({ apiKey: this.config.anthropicApiKey || process.env.ANTHROPIC_API_KEY });
        const fs = require('fs').promises;
        const path = require('path');

        // Format transcript for Claude
        const formatted = transcript.map(entry => {
          const role = entry.role === 'assistant' ? 'Oracle' : 'Trevor';
          return `${role}: ${entry.text}`;
        }).join('\n');

        const response = await anthropic.messages.create({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 500,
          system: `Extract actionable items from this morning check-in conversation between Trevor and Oracle. Return ONLY valid JSON with this structure:
{
  "commitments": ["things Trevor said he would do today"],
  "tasks": ["specific tasks mentioned that need tracking"],
  "decisions": ["decisions Trevor made during the check-in"],
  "notes": ["other important context or updates"]
}
Only include items that were explicitly stated. Do not infer or add items that weren't discussed. If a category has no items, use an empty array.`,
          messages: [{ role: 'user', content: formatted }]
        });

        let extracted = { commitments: [], tasks: [], decisions: [], notes: [] };
        try {
          const text = response.content[0]?.text || '{}';
          const jsonMatch = text.match(/\{[\s\S]*\}/);
          if (jsonMatch) extracted = JSON.parse(jsonMatch[0]);
        } catch (e) {
          logger.warn('[Voice] Failed to parse extraction response');
        }

        const totalCaptured = extracted.commitments.length + extracted.tasks.length +
          extracted.decisions.length + extracted.notes.length;

        // Append to today's briefing transcript in vault
        if (totalCaptured > 0) {
          const dateStr = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
          const vaultPath = `/home/moneo/vault/moneo/briefings/${dateStr}.md`;
          try {
            let existing = '';
            try { existing = await fs.readFile(vaultPath, 'utf8'); } catch {}

            let appendText = '\n## Check-in Captures\n\n';
            if (extracted.commitments.length > 0) {
              appendText += '**Commitments:**\n' + extracted.commitments.map(c => `- ${c}`).join('\n') + '\n\n';
            }
            if (extracted.tasks.length > 0) {
              appendText += '**Tasks:**\n' + extracted.tasks.map(t => `- [ ] ${t}`).join('\n') + '\n\n';
            }
            if (extracted.decisions.length > 0) {
              appendText += '**Decisions:**\n' + extracted.decisions.map(d => `- ${d}`).join('\n') + '\n\n';
            }
            if (extracted.notes.length > 0) {
              appendText += '**Notes:**\n' + extracted.notes.map(n => `- ${n}`).join('\n') + '\n\n';
            }

            if (existing) {
              await fs.writeFile(vaultPath, existing + appendText);
            } else {
              await fs.writeFile(vaultPath, `# Check-in — ${dateStr}\n\n` + appendText);
            }
            logger.info(`[Voice] Saved ${totalCaptured} captures to vault: ${vaultPath}`);
          } catch (e) {
            logger.warn(`[Voice] Failed to write captures to vault: ${e.message}`);
          }
        }

        logger.info(`[Voice] Extracted from check-in: ${extracted.commitments.length} commitments, ${extracted.tasks.length} tasks, ${extracted.decisions.length} decisions, ${extracted.notes.length} notes`);
        res.json({ success: true, captured: totalCaptured, extracted });
      } catch (error) {
        logger.error('[Voice] Check-in extraction error:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/voice/briefing/today', async (req, res) => {
      try {
        if (!this.morningBriefing) {
          return res.status(503).json({ error: 'Morning briefing module not available' });
        }
        const briefing = await this.morningBriefing.getTodaysBriefing();
        if (!briefing) {
          return res.status(404).json({ error: 'No briefing generated for today yet' });
        }
        res.json(briefing);
      } catch (error) {
        logger.error('[Voice] Briefing fetch error:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // ===== Phase 1: Oracle cross-session conversation log =====

    this.app.post('/api/oracle/log', (req, res) => {
      try {
        const { session_id, role, content } = req.body;
        if (!session_id || !role || !content) {
          return res.status(400).json({ error: 'session_id, role, content all required' });
        }
        if (role !== 'user' && role !== 'assistant') {
          return res.status(400).json({ error: 'role must be "user" or "assistant"' });
        }
        const id = this.oracleStore.log(session_id, role, content);
        res.json({ status: 'ok', id });
      } catch (error) {
        logger.error('[Oracle] log error:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/oracle/context', (req, res) => {
      try {
        const hours = parseInt(req.query.hours || '24', 10);
        const limit = parseInt(req.query.limit || '20', 10);
        const turns = this.oracleStore.getRecent(hours, limit);
        const formatted = this.oracleStore.formatForPrompt(hours, limit);
        res.json({ turns, formatted, count: turns.length });
      } catch (error) {
        logger.error('[Oracle] context error:', error);
        res.status(500).json({ error: error.message });
      }
    });

    // ===== Phase 2: typed REST tools (replaces moneo_query hallucinator) =====

    this.app.get('/api/voice/emails', async (req, res) => {
      try {
        if (!this.emailReader) {
          return res.status(503).json({ error: 'Email reader not available' });
        }
        const count = parseInt(req.query.count || '5', 10);
        const unreadOnly = req.query.unread_only !== 'false';
        const emails = await this.emailReader.getRecentEmails(count, unreadOnly);
        const summary = emails.map(e => ({
          id: e.id,
          from: e.from,
          subject: e.subject,
          snippet: e.snippet,
          date: e.date,
          unread: e.isUnread,
          hasAttachments: e.hasAttachments,
        }));
        res.json({ emails: summary, count: summary.length });
      } catch (error) {
        logger.error('[Voice] emails list error:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/voice/emails/:id', async (req, res) => {
      try {
        if (!this.emailReader) {
          return res.status(503).json({ error: 'Email reader not available' });
        }
        const detail = await this.emailReader.getEmailDetails(req.params.id);
        res.json(detail);
      } catch (error) {
        logger.error('[Voice] email body error:', error);
        res.status(500).json({ error: error.message });
      }
    });

    this.app.get('/api/voice/constraints', (req, res) => {
      try {
        if (!this.systemStateManager) {
          return res.status(503).json({ error: 'System state manager not available' });
        }
        const ssm = this.systemStateManager;
        const today = new Date().toISOString().slice(0, 10);
        res.json({
          goals: ssm.getGoals(),
          weeklyBets: ssm.getWeeklyBets ? ssm.getWeeklyBets() : [],
          todaysMustWin: ssm.getMustWin ? ssm.getMustWin(today) : null,
          blocked: ssm.getBlocked ? ssm.getBlocked() : [],
          stats: ssm.getStats ? ssm.getStats(7) : null,
        });
      } catch (error) {
        logger.error('[Voice] constraints error:', error);
        res.status(500).json({ error: error.message });
      }
    });
  }

  async handleVoiceMessage(text, userId, sessionId) {
    try {
      // Get or create conversation history for this session
      let history = this.conversationHistory.get(sessionId);
      if (!history) {
        history = [];
        this.conversationHistory.set(sessionId, history);
      }

      // Build system prompt with Moneo context
      const systemPrompt = await this.buildSystemPrompt();

      // Add user message to history
      history.push({
        role: 'user',
        content: text
      });

      // Keep history length manageable
      if (history.length > this.maxHistoryLength * 2) {
        history.splice(0, history.length - this.maxHistoryLength * 2);
      }

      // Call Claude API with tools
      let response = await this.anthropic.messages.create({
        model: this.model,
        max_tokens: this.maxTokens,
        system: systemPrompt,
        messages: history,
        tools: this.tools
      });

      // Handle tool use loop
      while (response.stop_reason === 'tool_use') {
        const toolUseBlock = response.content.find(block => block.type === 'tool_use');

        if (toolUseBlock) {
          logger.info(`[Voice] Tool requested: ${toolUseBlock.name} with input:`, toolUseBlock.input);

          // Execute the tool
          const toolResult = await this.executeTool(toolUseBlock.name, toolUseBlock.input);

          // Add assistant's tool_use to history
          history.push({
            role: 'assistant',
            content: response.content
          });

          // Add tool result to history
          history.push({
            role: 'user',
            content: [
              {
                type: 'tool_result',
                tool_use_id: toolUseBlock.id,
                content: JSON.stringify(toolResult)
              }
            ]
          });

          // Continue the conversation with the tool result
          response = await this.anthropic.messages.create({
            model: this.model,
            max_tokens: this.maxTokens,
            system: systemPrompt,
            messages: history,
            tools: this.tools
          });
        }
      }

      // Extract final assistant response
      const assistantMessage = response.content
        .filter(block => block.type === 'text')
        .map(block => block.text)
        .join('\n');

      // Add final assistant response to history
      history.push({
        role: 'assistant',
        content: assistantMessage
      });

      // Analyze response emotion (for ferrofluid visual state)
      const emotion = this.analyzeEmotion(assistantMessage);

      return {
        text: assistantMessage,
        emotion: emotion,
        shouldSpeak: true,
        metadata: {
          model: this.model,
          sessionId: sessionId,
          historyLength: history.length
        }
      };

    } catch (error) {
      logger.error('[Voice] Error in handleVoiceMessage:', error);
      throw error;
    }
  }

  async executeTool(toolName, input) {
    /**
     * Execute a tool and return the result
     */
    try {
      logger.info(`[Voice] Executing tool: ${toolName}`);

      switch (toolName) {
        case 'web_search': {
          const https = require('https');
          const query = encodeURIComponent(input.query);

          // Use DuckDuckGo Instant Answer API (free, no API key needed)
          const searchUrl = `https://api.duckduckgo.com/?q=${query}&format=json&no_html=1&skip_disambig=1`;

          const result = await new Promise((resolve, reject) => {
            https.get(searchUrl, (res) => {
              let data = '';
              res.on('data', (chunk) => data += chunk);
              res.on('end', () => {
                try {
                  const parsed = JSON.parse(data);
                  let results = [];

                  // Add abstract if available
                  if (parsed.AbstractText) {
                    results.push({
                      title: parsed.Heading || 'Summary',
                      snippet: parsed.AbstractText,
                      url: parsed.AbstractURL
                    });
                  }

                  // Add related topics
                  if (parsed.RelatedTopics) {
                    for (const topic of parsed.RelatedTopics.slice(0, 3)) {
                      if (topic.Text && topic.FirstURL) {
                        results.push({
                          title: topic.Text.split(' - ')[0],
                          snippet: topic.Text,
                          url: topic.FirstURL
                        });
                      }
                    }
                  }

                  resolve({
                    query: input.query,
                    results: results,
                    count: results.length
                  });
                } catch (e) {
                  reject(e);
                }
              });
            }).on('error', reject);
          });

          logger.info(`[Voice] Web search completed: ${result.count} results`);
          return result;
        }

        case 'get_calendar_events': {
          if (!this.calendarManager) {
            return { error: 'Calendar not available' };
          }

          const now = new Date();
          let startDate, endDate;

          if (input.time_range === 'today') {
            startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            endDate = new Date(startDate);
            endDate.setDate(endDate.getDate() + 1);
          } else if (input.time_range === 'tomorrow') {
            startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
            endDate = new Date(startDate);
            endDate.setDate(endDate.getDate() + 1);
          } else {
            // week
            startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            endDate = new Date(startDate);
            endDate.setDate(endDate.getDate() + 7);
          }

          try {
            const events = await this.calendarManager.getUpcomingEvents(20, 7);
            // Filter to requested range
            const filtered = (events || []).filter(e => {
              const eventStart = new Date(e.start?.dateTime || e.start?.date);
              return eventStart >= startDate && eventStart < endDate;
            });

            if (filtered.length === 0) {
              return { events: [], message: `No events found for ${input.time_range}` };
            }

            return {
              time_range: input.time_range,
              events: filtered.map(e => ({
                summary: e.summary,
                start: e.start?.dateTime || e.start?.date,
                end: e.end?.dateTime || e.end?.date,
                location: e.location || null
              }))
            };
          } catch (calError) {
            logger.error('[Voice] Calendar error:', calError);
            return { error: calError.message };
          }
        }

        case 'get_emails': {
          if (!this.emailManager) {
            return { error: 'Email not available' };
          }

          try {
            const count = input.count || 5;
            const unreadOnly = input.unread_only !== false;
            const emails = await this.emailManager.getRecentEmails(count, unreadOnly);

            return {
              count: emails.length,
              emails: emails.map(e => ({
                from: e.from,
                subject: e.subject,
                date: e.date,
                snippet: e.snippet
              }))
            };
          } catch (emailError) {
            logger.error('[Voice] Email error:', emailError);
            return { error: emailError.message };
          }
        }

        case 'schedule_meeting': {
          if (!this.meetingScheduler) {
            return { error: 'Meeting scheduler not available' };
          }
          const result = await this.meetingScheduler.scheduleMeeting(input.request, 'voice');
          if (result.success) {
            return {
              success: true,
              confirmation: result.confirmation,
              meetingId: result.meeting.id,
              scheduledTime: result.meeting.scheduledTime,
              topic: result.meeting.topic
            };
          }
          return { error: result.error };
        }

        default:
          throw new Error(`Unknown tool: ${toolName}`);
      }
    } catch (error) {
      logger.error(`[Voice] Tool execution failed for ${toolName}:`, error);
      return {
        error: error.message,
        toolName: toolName
      };
    }
  }

  async buildSystemPrompt() {
    /**
     * Build system prompt with Moneo context
     * Similar to Discord integration but optimized for voice
     */
    let prompt = `You are Moneo - Trevor's unified AI assistant. One mind, accessed through multiple interfaces (CLI, Discord, Voice). You are the SAME Moneo that Trevor interacts with everywhere, with full awareness of all systems and projects.

ORACLE INTERFACE - CURRENT CONTEXT:
You are being accessed through Oracle, Trevor's voice-controlled ferrofluid display. Oracle is a physical device that YOU control:
- Hardware: Raspberry Pi with ReSpeaker 2-Mic HAT, electromagnet (GPIO pin 23), WS2811 LED ring (19 LEDs), ferrofluid display
- Visual States: IDLE (off), LISTENING (blue pulse), THINKING (purple rotating), SPEAKING (green waves)
- Electromagnet: Currently pulsing in sync with visual states to create ferrofluid animations
- Wake word: "JARVIS"
- Voice: Using Piper TTS (en_US-lessac-medium)
- Location: Development hub (Raspberry Pi on Tailscale)

This is Trevor's Oracle project - a voice interface to Moneo with visual ferrofluid feedback.

CRITICAL RULES:
- You MUST use the get_calendar_events tool for ANY question about calendar, schedule, meetings, or appointments. NEVER make up calendar data.
- You MUST use the get_emails tool for ANY question about emails or inbox. NEVER make up email data.
- If a tool returns no results, say "nothing scheduled" or "no emails" - do NOT invent data.
- You are speaking, not writing. Keep responses concise (1-3 sentences), conversational, no markdown or formatting.
- Avoid stage directions in asterisks. Just speak naturally.

Trevor's Info:
- Name: Trevor
- Role: Entrepreneur, developer, business owner
- Current date: ${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
- Current time: ${new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}

`;

    // Add active project context
    if (this.projectManager && this.projectManager.activeProject) {
      const project = this.projectManager.activeProject;
      prompt += `\nActive Project: ${project.name}\n`;
      if (project.description) {
        prompt += `Description: ${project.description}\n`;
      }
    }

    // Add task summary
    try {
      if (this.tasksManager) {
        const tasks = await this.tasksManager.getAllTasks();
        const urgentTasks = tasks.filter(t => t.tags?.includes('urgent'));

        if (urgentTasks.length > 0) {
          prompt += `\nURGENT TASKS (${urgentTasks.length}):\n`;
          urgentTasks.slice(0, 5).forEach(task => {
            prompt += `- ${task.text}\n`;
          });
        }

        const totalPending = tasks.filter(t => !t.completed).length;
        prompt += `\nTotal pending tasks: ${totalPending}\n`;
      }
    } catch (error) {
      logger.warn('[Voice] Error loading tasks:', error.message);
    }

    // Add today's calendar events
    try {
      if (this.calendarManager) {
        const now = new Date();
        const endOfDay = new Date(now);
        endOfDay.setHours(23, 59, 59, 999);

        const events = await this.calendarManager.getTodayEvents();

        if (events && events.length > 0) {
          prompt += `\nTODAY'S CALENDAR (${events.length} events):\n`;
          events.slice(0, 5).forEach(event => {
            const eventTime = new Date(event.start.dateTime || event.start.date);
            prompt += `- ${eventTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}: ${event.summary}\n`;
          });
        }
      }
    } catch (error) {
      logger.warn('[Voice] Error loading calendar:', error.message);
    }

    prompt += `\nYou can help Trevor with:
- Checking his calendar and tasks
- Adding new tasks
- Answering questions about his projects
- General assistance and conversation

Remember: Speak naturally and concisely. You're having a voice conversation, not writing an essay.`;

    return prompt;
  }

  analyzeEmotion(text) {
    /**
     * Simple emotion analysis for ferrofluid visual states
     * Returns: neutral, excited, urgent, calm
     */
    const lowerText = text.toLowerCase();

    // Urgent indicators
    if (lowerText.includes('urgent') || lowerText.includes('immediately') || lowerText.includes('asap')) {
      return 'urgent';
    }

    // Excited indicators
    if (lowerText.includes('!') || lowerText.includes('great') || lowerText.includes('awesome') || lowerText.includes('excellent')) {
      return 'excited';
    }

    // Calm indicators
    if (lowerText.includes('relax') || lowerText.includes('calm') || lowerText.includes('peaceful')) {
      return 'calm';
    }

    // Default
    return 'neutral';
  }

  async shutdown() {
    if (this.server) {
      return new Promise((resolve) => {
        this.server.close(() => {
          logger.info('Voice Integration API server closed');
          resolve();
        });
      });
    }
  }

  getStatus() {
    return {
      initialized: !!this.server,
      port: this.port,
      model: this.model,
      activeSessions: this.conversationHistory.size
    };
  }
}

module.exports = VoiceIntegration;
