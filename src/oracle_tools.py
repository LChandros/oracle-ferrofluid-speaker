"""
Oracle Tools Module
All tool handlers for the Realtime API. Routes through Moneo API where possible.

Tools removed in consolidation:
- run_command (security risk — use SSH for debugging)
- debug_system (use SSH for debugging)
"""

import json
import os
import time
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger('OracleMaster')

REMINDERS_FILE = "/home/tyahn/oracle_reminders.json"


class ToolHandler:
    """Dispatches and executes tool calls from the Realtime API."""

    def __init__(self, moneo_api_url, moneo_api_key, spotify, session_id):
        self.moneo_api_url = moneo_api_url
        self.moneo_api_key = moneo_api_key
        self.spotify = spotify
        self.session_id = session_id

    def handle(self, name, args):
        """Main dispatch — called by the Realtime API session."""
        logger.info(f"[Tool] Executing: {name}")

        if name == "spotify_play":
            return self.spotify.tool_play(args.get("query", ""))
        elif name == "spotify_control":
            return self.spotify.tool_control(args.get("action", ""))
        elif name == "get_emails":
            return self._get_emails(args.get("count", 5))
        elif name == "read_email":
            return self._read_email(args.get("email_id", ""))
        elif name == "get_constraints":
            return self._get_constraints()
        elif name == "set_reminder":
            return self._set_reminder(
                args.get("message", ""),
                args.get("time", ""),
                args.get("date", "today"),
                args.get("priority", "medium")
            )
        elif name == "morning_briefing":
            return self._morning_briefing()
        elif name == "get_calendar":
            return self._get_calendar(args.get("time_range", "today"))
        elif name == "create_calendar_event":
            return self._create_calendar_event(args)
        elif name == "send_email":
            return self._send_email(args)
        elif name == "dismiss_reminder":
            return self._dismiss_reminder(args.get("reminder_index", -1))
        elif name == "list_reminders":
            return self._list_reminders()
        elif name == "snooze_reminder":
            return self._snooze_reminder(
                args.get("reminder_index", -1),
                args.get("minutes", 10)
            )
        elif name == "get_tasks":
            return self._get_tasks()
        elif name == "capture":
            return self._capture(
                args.get("type", "note"),
                args.get("text", ""),
                args.get("project", "")
            )
        else:
            return {"error": f"Unknown tool: {name}"}

    # ==================== TASKS ====================

    def _get_tasks(self):
        """Get Trevor's current to-do list from the Moneo punch list."""
        try:
            api_base = self.moneo_api_url.rsplit('/api/', 1)[0]
            response = requests.get(
                f'{api_base}/api/voice/tasks',
                headers={'X-API-Key': self.moneo_api_key},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                if not items:
                    return {'tasks': [], 'message': 'Your to-do list is empty.'}
                
                task_list = []
                for item in items:
                    entry = item.get('description', '')
                    ctx = item.get('context', '')
                    if ctx:
                        entry = f'[{ctx}] {entry}'
                    rolls = item.get('rollCount', 0)
                    if rolls >= 3:
                        entry += f' (rolled {rolls} times)'
                    task_list.append(entry)
                
                return {'tasks': task_list, 'count': len(task_list)}
            else:
                return {'error': f'Tasks API returned {response.status_code}'}
        except Exception as e:
            return {'error': str(e)}

    # ==================== CAPTURE ====================

    def _capture(self, capture_type, text, project=""):
        """Capture a task, note, or commitment to the Moneo system."""
        try:
            api_base = self.moneo_api_url.rsplit("/api/", 1)[0]
            response = requests.post(
                f"{api_base}/api/voice/capture",
                headers={"X-API-Key": self.moneo_api_key, "Content-Type": "application/json"},
                json={"type": capture_type, "text": text, "project": project or "Personal"},
                timeout=10
            )
            if response.status_code == 200:
                logger.info(f"[Tool] Captured {capture_type}: {text}")
                return {"success": True, "type": capture_type, "text": text}
            else:
                return {"error": f"Capture failed: {response.status_code}"}
        except Exception as e:
            logger.error(f"[Tool] Capture error: {e}")
            return {"error": str(e)}

    # ==================== EMAILS (Phase 2: direct REST, no hallucination) ====================

    def _get_emails(self, count=5):
        """List recent unread emails from Trevor's inbox (subject + sender)."""
        try:
            api_base = self.moneo_api_url.rsplit('/api/', 1)[0]
            response = requests.get(
                f"{api_base}/api/voice/emails?count={int(count)}",
                headers={"X-API-Key": self.moneo_api_key},
                timeout=15
            )
            if response.status_code != 200:
                return {"error": f"Emails API returned {response.status_code}"}
            data = response.json()
            emails = data.get("emails", [])
            if not emails:
                return {"emails": [], "message": "No unread emails."}
            # Speak-friendly summary: from + subject + snippet head, plus id for read_email
            summary = []
            for e in emails:
                sender = e.get("from", "").split("<")[0].strip().strip('"') or "Unknown"
                summary.append({
                    "id": e.get("id"),
                    "from": sender,
                    "subject": e.get("subject", "(no subject)"),
                    "preview": (e.get("snippet") or "")[:120],
                })
            return {"emails": summary, "count": len(summary)}
        except Exception as e:
            return {"error": str(e)}

    def _read_email(self, email_id):
        """Read the full body of one email by id."""
        if not email_id:
            return {"error": "email_id required"}
        try:
            api_base = self.moneo_api_url.rsplit('/api/', 1)[0]
            response = requests.get(
                f"{api_base}/api/voice/emails/{email_id}",
                headers={"X-API-Key": self.moneo_api_key},
                timeout=15
            )
            if response.status_code != 200:
                return {"error": f"Email body API returned {response.status_code}"}
            d = response.json()
            sender = d.get("from", "").split("<")[0].strip().strip('"') or "Unknown"
            body = d.get("body", "")
            return {
                "from": sender,
                "subject": d.get("subject", "(no subject)"),
                "date": d.get("date", ""),
                "body": body[:1500],  # Cap to keep TTS reasonable
                "has_attachments": d.get("hasAttachments", False),
            }
        except Exception as e:
            return {"error": str(e)}

    # ==================== CONSTRAINTS (Phase 2) ====================

    def _get_constraints(self):
        """Get Trevor's active goals, weekly bets, today's must-win, and blockers."""
        try:
            api_base = self.moneo_api_url.rsplit('/api/', 1)[0]
            response = requests.get(
                f"{api_base}/api/voice/constraints",
                headers={"X-API-Key": self.moneo_api_key},
                timeout=10
            )
            if response.status_code != 200:
                return {"error": f"Constraints API returned {response.status_code}"}
            d = response.json()
            goals = d.get("goals", []) or []
            bets = d.get("weeklyBets", []) or []
            must_win = d.get("todaysMustWin")
            blocked = d.get("blocked", []) or []
            stats = d.get("stats") or {}
            return {
                "active_goals": [{"name": g.get("name"), "pillar": g.get("pillar"),
                                  "next_action": g.get("nextAction")} for g in goals],
                "weekly_bets": [b if isinstance(b, str) else b.get("text", b.get("name", str(b))) for b in bets],
                "todays_must_win": (must_win or {}).get("text") if isinstance(must_win, dict) else must_win,
                "blocked": [b if isinstance(b, str) else b.get("text", b.get("name", str(b))) for b in blocked],
                "at_capacity": stats.get("activeGoals", 0) >= 5,
                "pending_task_count": stats.get("pendingTasks", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def _morning_briefing(self):
        """Signal master service to switch to dedicated briefing session."""
        self._briefing_requested = True
        return {"response": "Starting your morning check-in now. One moment."}

    def _get_calendar(self, time_range):
        """Get calendar events via Moneo API."""
        try:
            api_base = self.moneo_api_url.rsplit('/api/', 1)[0]
            response = requests.get(
                f"{api_base}/api/voice/calendar/events?range={time_range}",
                headers={"X-API-Key": self.moneo_api_key},
                timeout=10
            )
            if response.status_code == 200:
                events = response.json().get("events", [])
                if not events:
                    return {"events": "none", "message": f"No events on calendar for {time_range}"}

                event_list = []
                for e in events:
                    start = e.get("start", "")
                    if "T" in start:
                        t = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        time_str = t.strftime("%I:%M %p")
                    else:
                        time_str = start
                    entry = f"{time_str}: {e.get('summary', 'Untitled')}"
                    if e.get("description"):
                        entry += f" (Notes: {e['description']})"
                    if e.get("attendees"):
                        entry += f" (Attendees: {e['attendees']})"
                    event_list.append(entry)

                return {"events": event_list, "count": len(event_list)}
            else:
                return {"error": f"Calendar API returned {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def _create_calendar_event(self, args):
        """Create a calendar event via Moneo API."""
        try:
            api_base = self.moneo_api_url.rsplit('/api/', 1)[0]
            payload = {"summary": args.get("summary", ""), "startTime": args.get("start_time", "")}
            if args.get("end_time"):
                payload["endTime"] = args["end_time"]
            if args.get("description"):
                payload["description"] = args["description"]
            if args.get("location"):
                payload["location"] = args["location"]

            response = requests.post(
                f"{api_base}/api/voice/calendar/create",
                headers={"X-API-Key": self.moneo_api_key, "Content-Type": "application/json"},
                json=payload, timeout=10
            )
            if response.status_code == 200:
                logger.info(f"[Calendar] Event created: {args.get('summary')}")
                return {"status": "created", "summary": args.get("summary"), "start_time": args.get("start_time")}
            else:
                return {"error": f"Calendar API returned {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    def _send_email(self, args):
        """Send email via Moneo API."""
        try:
            to, subject, body = args.get("to", ""), args.get("subject", ""), args.get("body", "")
            if not to or not subject or not body:
                return {"error": "Missing required fields: to, subject, body"}

            api_base = self.moneo_api_url.rsplit('/api/', 1)[0]
            response = requests.post(
                f"{api_base}/api/voice/email/send",
                headers={"X-API-Key": self.moneo_api_key, "Content-Type": "application/json"},
                json={"to": to, "subject": subject, "body": body}, timeout=10
            )
            if response.status_code == 200:
                logger.info(f"[Email] Sent to {to}: {subject}")
                return {"status": "sent", "to": to, "subject": subject}
            else:
                return {"error": f"Email API returned {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    # ==================== REMINDERS ====================

    def _load_reminders(self):
        try:
            with open(REMINDERS_FILE, "r") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_reminders(self, reminders):
        with open(REMINDERS_FILE, "w") as f:
            json.dump(reminders, f, indent=2)

    def _set_reminder(self, message, reminder_time, date="today", priority="medium"):
        """Schedule a spoken reminder."""
        try:
            hour, minute = map(int, reminder_time.split(":"))
            now = datetime.now()

            if not date or date.lower() == "today":
                target_date = now.date()
            elif date.lower() == "tomorrow":
                target_date = (now + timedelta(days=1)).date()
            else:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()

            target_dt = datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))

            if target_dt < now:
                return {"error": f"Cannot set reminder in the past ({target_dt.strftime('%I:%M %p')})"}

            reminder = {
                "message": message,
                "time": target_dt.strftime("%Y-%m-%d %H:%M"),
                "priority": priority,
                "created": now.strftime("%Y-%m-%d %H:%M:%S")
            }

            reminders = self._load_reminders()
            reminders.append(reminder)
            self._save_reminders(reminders)

            friendly_time = target_dt.strftime("%I:%M %p on %B %d")
            logger.info(f"[Reminder] Set for {friendly_time}: {message}")
            return {"status": "set", "delivery_time": friendly_time, "message": message, "priority": priority}

        except ValueError as e:
            return {"error": f"Could not parse time/date: {e}"}
        except Exception as e:
            return {"error": str(e)}

    def _dismiss_reminder(self, reminder_index=-1):
        """Dismiss a reminder so it stops re-alerting."""
        try:
            reminders = self._load_reminders()
            if not reminders:
                return {"error": "No reminders found."}

            if reminder_index == -1:
                fired = [(i, r) for i, r in enumerate(reminders) if r.get('status') == 'fired']
                if not fired:
                    now = datetime.now()
                    fired = [(i, r) for i, r in enumerate(reminders)
                             if r.get('status', 'pending') == 'pending'
                             and datetime.strptime(r['time'], '%Y-%m-%d %H:%M') <= now]
                if not fired:
                    return {"error": "No active reminders to dismiss."}
                reminder_index = fired[-1][0]

            if reminder_index < 0 or reminder_index >= len(reminders):
                return {"error": f"Invalid reminder index: {reminder_index}"}

            reminder = reminders[reminder_index]
            message = reminder.get('message', 'unknown')
            reminder['status'] = 'dismissed'
            reminder['dismissed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_reminders(reminders)

            logger.info(f"[Reminder] Dismissed: {message}")
            return {"status": "dismissed", "message": message}
        except Exception as e:
            return {"error": str(e)}

    def _list_reminders(self):
        """List all active reminders."""
        try:
            reminders = self._load_reminders()
            if not reminders:
                return {"reminders": [], "message": "No reminders set."}

            active = []
            for i, r in enumerate(reminders):
                status = r.get('status', 'pending')
                if status == 'dismissed':
                    continue
                active.append({
                    "index": i, "message": r.get('message', ''),
                    "time": r.get('time', ''), "status": status,
                    "priority": r.get('priority', 'medium'),
                    "fire_count": r.get('fire_count', 0)
                })

            if not active:
                return {"reminders": [], "message": "No active reminders."}
            return {"reminders": active, "count": len(active)}
        except Exception as e:
            return {"error": str(e)}

    def _snooze_reminder(self, reminder_index=-1, minutes=10):
        """Snooze a fired reminder for N minutes."""
        try:
            reminders = self._load_reminders()
            if not reminders:
                return {"error": "No reminders found."}

            if reminder_index == -1:
                fired = [(i, r) for i, r in enumerate(reminders) if r.get('status') == 'fired']
                if not fired:
                    return {"error": "No fired reminders to snooze."}
                reminder_index = fired[-1][0]

            if reminder_index < 0 or reminder_index >= len(reminders):
                return {"error": f"Invalid reminder index: {reminder_index}"}

            reminder = reminders[reminder_index]
            message = reminder.get('message', 'unknown')
            new_time = (datetime.now() + timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M')
            reminder['time'] = new_time
            reminder['status'] = 'pending'
            reminder['fire_count'] = 0
            reminder['last_fired_at'] = None
            self._save_reminders(reminders)

            logger.info(f"[Reminder] Snoozed '{message}' for {minutes} min -> {new_time}")
            return {"status": "snoozed", "message": message, "new_time": new_time}
        except Exception as e:
            return {"error": str(e)}
