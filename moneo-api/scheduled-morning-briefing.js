/**
 * Scheduled Morning Briefing
 *
 * Pre-generates a natural spoken briefing using data from all Moneo sources,
 * then delivers it through the Oracle speaker at 10 AM ET via the Realtime API.
 *
 * Schedule:
 * - 9:30 AM ET: Gather data + world news, compose natural script via Claude
 * - 10:00 AM ET: Oracle Pi fetches script and speaks it
 *
 * Manual triggers via API:
 * - POST /api/voice/briefing/generate - generate now
 * - GET /api/voice/briefing/today - get today's briefing text
 */

const cron = require('node-cron');
const path = require('path');
const fs = require('fs').promises;
const Anthropic = require('@anthropic-ai/sdk');
const logger = require('../utils/logger');
const MorningMeetingData = require('./morning-meeting-data');

const BRIEFINGS_DIR = path.join(__dirname, '../../data/morning-meetings');

class ScheduledMorningBriefing {
  constructor(config, calendarManager, tasksManager, emailManager, msgraphEmailManager, emailDatabaseClient) {
    this.config = config;
    this.anthropic = new Anthropic({ apiKey: config.anthropicApiKey });

    this.dataProvider = new MorningMeetingData(
      calendarManager, tasksManager, emailManager,
      msgraphEmailManager, emailDatabaseClient
    );

    this.todaysBriefing = null; // Cached briefing text
    this.lastGeneratedDate = null;

    logger.info('[MorningBriefing] Module created');
  }

  async initialize() {
    // Ensure data directory exists
    try {
      await fs.mkdir(BRIEFINGS_DIR, { recursive: true });
    } catch (e) {}

    // Schedule pre-generation at 9:30 AM ET weekdays
    cron.schedule('30 9 * * 1-5', async () => {
      logger.info('[MorningBriefing] Scheduled generation triggered (9:30 AM ET)');
      try {
        await this.generate();
      } catch (error) {
        logger.error('[MorningBriefing] Scheduled generation failed:', error.message);
      }
    }, { timezone: 'America/New_York' });

    logger.info('[MorningBriefing] Initialized - scheduled for 9:30 AM ET weekdays');
  }

  async generate() {
    logger.info('[MorningBriefing] Starting briefing generation...');
    const startTime = Date.now();

    // 1. Gather all data from existing sources
    logger.info('[MorningBriefing] Gathering data...');
    const data = await this.dataProvider.gatherBriefingData();

    // 2. Fetch world news
    logger.info('[MorningBriefing] Fetching world news...');
    const news = await this._fetchWorldNews();
    data.news = news;

    // 3. Compose natural script via Claude
    logger.info('[MorningBriefing] Composing briefing script...');
    const script = await this._composeBriefingScript(data);

    // 4. Cache and save
    const dateStr = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' }); // YYYY-MM-DD
    this.todaysBriefing = {
      date: dateStr,
      generatedAt: new Date().toISOString(),
      script: script,
      dataSummary: {
        calendarEvents: data.calendar.events?.length || 0,
        tasks: data.tasks.total || 0,
        unreadEmails: data.email.unreadCount || 0,
        weather: data.weather.summary ? true : false,
        newsIncluded: !!news.summary
      }
    };
    this.lastGeneratedDate = dateStr;

    // Save to file
    const filePath = path.join(BRIEFINGS_DIR, `briefing-${dateStr}.json`);
    await fs.writeFile(filePath, JSON.stringify(this.todaysBriefing, null, 2));

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    logger.info(`[MorningBriefing] Generated in ${elapsed}s (${script.length} chars)`);

    return this.todaysBriefing;
  }

  async getTodaysBriefing() {
    const dateStr = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });

    // Return cached if available
    if (this.todaysBriefing && this.lastGeneratedDate === dateStr) {
      return this.todaysBriefing;
    }

    // Try loading from file
    try {
      const filePath = path.join(BRIEFINGS_DIR, `briefing-${dateStr}.json`);
      const content = await fs.readFile(filePath, 'utf8');
      this.todaysBriefing = JSON.parse(content);
      this.lastGeneratedDate = dateStr;
      return this.todaysBriefing;
    } catch (e) {
      return null;
    }
  }

  async _fetchWorldNews() {
    try {
      const response = await this.anthropic.messages.create({
        model: 'claude-3-haiku-20240307',
        max_tokens: 300,
        messages: [{
          role: 'user',
          content: `Give me 2-3 sentences summarizing today's most relevant news for a small manufacturing business owner in Pittsburgh, PA who sells plumbing products wholesale. Focus on: economy, manufacturing, trade policy, supply chain, or any major headlines. Be specific with facts, not vague. Today is ${new Date().toLocaleDateString('en-US', { timeZone: 'America/New_York' })}.`
        }]
      });

      const summary = response.content[0]?.text || null;
      logger.info(`[MorningBriefing] News fetched: ${summary?.substring(0, 80)}...`);
      return { summary, error: null };
    } catch (error) {
      logger.warn(`[MorningBriefing] News fetch failed: ${error.message}`);
      return { summary: null, error: error.message };
    }
  }

  async _composeBriefingScript(data) {
    const systemPrompt = `You are Moneo, Trevor Yahn's personal AI assistant, delivering a morning briefing through the Oracle ferrofluid speaker.

VOICE AND TONE:
- Speak like JARVIS from Iron Man: dry, competent, occasionally witty
- Natural conversational flow — NOT a list of bullet points
- Direct and efficient — respect Trevor's time
- You're speaking out loud, not writing. No markdown, no formatting, no asterisks.
- Spell out numbers and abbreviations naturally

STRUCTURE (flow naturally between these, don't announce sections):
1. Open with weather and calendar overview for the day
2. Business status: Clam orders, inbox, any urgent items
3. World news that affects the business (if available)
4. Goals, blockers, or things waiting on Trevor
5. Close with the single most important thing to focus on today

CONSTRAINTS:
- Keep total script under 250 words (about 90 seconds spoken)
- If data is missing or empty, skip that topic gracefully
- Don't make up data — only report what's provided
- End with something actionable, not a generic sign-off

Trevor's business: GPJ Industries LLC, manufactures The Clam (toilet flange repair ring), sells wholesale to plumbing distributors.`;

    const userContent = `Here is today's data. Compose the morning briefing script:\n\n${JSON.stringify(data, null, 2)}`;

    const response = await this.anthropic.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 500,
      system: systemPrompt,
      messages: [{ role: 'user', content: userContent }]
    });

    return response.content[0]?.text || 'Good morning Trevor. I was unable to compose today\'s briefing due to a system error.';
  }
}

module.exports = ScheduledMorningBriefing;
