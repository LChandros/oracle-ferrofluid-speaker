# Oracle Ferrofluid Speaker — Development Plan to "Jarvis" Scope

**Created:** 2026-05-18
**Status:** Phase 0 ✓ (b6513d2). Phase 1 ✓ (da96965). Phase 2 ✓ (2cd1940). Phase 3 ✓ (84ffe77, verified 2026-05-18). Phase 4 next.

## Scope (per Trevor, 2026-05-18)

Oracle is the mouthpiece for Moneo. Visual + auditory nexus for:
- Morning briefings (auto): progress check, due dates, calendar
- EOD check-ins (auto): interview about the day
- Digital assistant: todos, calendar, read/send email, audio notes
- Spotify playback in the shop
- Proactive alerts (Clam orders, urgent email, print failures)
- Conversational memory across sessions
- Visually stunning ferrofluid + LED reactive

Wake word stays "computer" for now (revisit later).

## Phases

### Phase 0 — Stop the bleeding (~4 hrs) — COMPLETE 2026-05-18 (commit b6513d2)
Housekeeping so the next deploys sit on solid ground.
- Move `PORCUPINE_KEY` + `OPENAI_API_KEY` out of `oracle_master_service.py` into `/etc/oracle/oracle.env` (systemd `EnvironmentFile`)
- Mic watchdog: detect dead `arecord` pipe → respawn (known issue from March memory)
- Heartbeat: Oracle posts "alive" to Discord/ntfy every 5 min. Silent death pages Trevor.
- **Done when:** Pi reboot leaves no broken state, mic recovers from kill, silent death pages.

### Phase 1 — Conversation memory (~6 hrs) — COMPLETE 2026-05-18 (commit da96965)
- Every Realtime turn (user transcript + assistant text) POSTs to droplet `/api/oracle/log`
- Moneo stores in SQLite: `(timestamp, session_id, role, content)`
- New session pulls last ~24h as system-context prefix
- **Done when:** "What did I tell you yesterday?" works. ✓ Verified live with cross-session orange-filament-spool recall.

### Phase 2 — Kill `moneo_query`, add direct tools (~8 hrs) — COMPLETE 2026-05-18 (commit 2cd1940)
The "Pi thin, Moneo brain" refactor from April.
- Drop `moneo_query` (the Haiku middleman that hallucinates)
- Add direct tools, each backed by a typed REST endpoint: `get_tasks`, `get_emails`, `get_constraints`, `read_email_body(id)`
- Same pattern as `get_calendar` (already works correctly)
- **Done when:** "What's on my plate?" returns real data, not creative writing.

### Phase 3 — Proactive alerts (~6 hrs) — COMPLETE 2026-05-18 (commit 84ffe77)
Two-tier delivery: critical speaks immediately, info goes to a pending store
and pulses the LEDs softly every 10 min until acknowledged. Voice-cleared
via list_pending_notifications + clear_notifications tools. Midnight cron
auto-sweeps anything still pending. Sources wired: calendar countdowns
(T-15 info, T-5 critical) and Clam PO drafts (critical).
Single biggest thing separating "voice toy" from "Jarvis."
- Pi opens persistent WebSocket to droplet `/api/oracle/events`
- Droplet fans in: ntfy alerts, new Clam PO, urgent Gmail label, print-farm failures
- Pi speaks high-priority alerts via short Realtime session (no wake word needed)
- Ferrofluid pulses purple while alerts unacknowledged; clears on next interaction
- **Done when:** Clam PO arrives → Oracle speaks within 30s.

### Phase 4 — EOD interview + audio notes (~6 hrs)
Two scope bullets, shared infrastructure.
- 6 PM weekday auto-trigger (reuses scheduler)
- Structured prompt scaffold: "What shipped? What's blocked? Tomorrow's #1?"
- Transcript saved to Moneo, summarized into `/vault/daily-debriefs/YYYY-MM-DD.md`
- New `capture_note` tool: "Computer, take a note" → records → Whisper transcribes → saves to droplet
- **Done when:** 6 PM auto-fires interview, ad-hoc audio notes land in vault.

### Phase 5 — Spotify search/play + email reading (~4 hrs)
- Wire `spotify_play(query)` to existing `core/modules/spotify-manager.js`
- New `read_emails` tool: speaks sender + subject for unread, asks "read full?"
- **Done when:** "Play Bad Guy by Billie Eilish" works, "read my emails" works.

### Phase 6 — Decisions, not code (~30 min conversation)
- **Oracle vs Moneo Companion split.** Probably: shared conversation log + shared tool set, but Oracle = always-on ambient at home/shop, Companion = push-to-talk + notifications on the go. Both share one Moneo brain.
- **What stays on Pi vs droplet.** Target: Pi owns audio I/O + visualization only. Tools execute on droplet.

## Totals
- ~34 hrs across 6 phases
- Realistic: one phase per week = 6 weeks to scope-complete
