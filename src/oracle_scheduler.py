#!/usr/bin/env python3
"""
Oracle Scheduler Service
Monitors schedule.md for announcements and sends them to Oracle via FIFO
"""

import os
import sys
import time
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
import requests

# Configuration
SCHEDULE_FILE = '/root/moneo/data/obsidian/oracle/schedule.md'
FIFO_PATH = '/tmp/oracle_announce.fifo'
LOG_FILE = '/tmp/oracle_scheduler.log'
CHECK_INTERVAL = 60  # seconds
MONEO_API_BASE = 'http://localhost:3001'  # Moneo Core API

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('oracle_scheduler')


class OracleScheduler:
    def __init__(self):
        self.schedule = {}
        self.last_triggered = {}  # Track last trigger time for recurring events
        self.news_cache = {}  # Cache for news monitoring

    def load_schedule(self):
        """Parse schedule.md and return structured data"""
        try:
            if not os.path.exists(SCHEDULE_FILE):
                logger.warning(f'Schedule file not found: {SCHEDULE_FILE}')
                return {}

            with open(SCHEDULE_FILE, 'r') as f:
                content = f.read()

            schedule = {
                'daily_recurring': [],
                'news_monitors': [],
                'one_time': []
            }

            current_section = None

            for line in content.split('\n'):
                line = line.strip()

                # Section headers
                if '## Daily Recurring Events' in line:
                    current_section = 'daily_recurring'
                    continue
                elif '## News Monitors' in line:
                    current_section = 'news_monitors'
                    continue
                elif '## One-Time Reminders' in line:
                    current_section = 'one_time'
                    continue

                # Parse event lines (start with -)
                if not line.startswith('-') or not current_section:
                    continue

                line = line[1:].strip()  # Remove leading dash

                if current_section == 'daily_recurring':
                    # Format: HH:MM | text | priority
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        schedule['daily_recurring'].append({
                            'time': parts[0],
                            'text': parts[1],
                            'priority': parts[2]
                        })

                elif current_section == 'news_monitors':
                    # Format: source | interval: duration | priority: level | min_score: N
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 2:
                        monitor = {'source': parts[0]}
                        for part in parts[1:]:
                            if ':' in part:
                                key, val = part.split(':', 1)
                                monitor[key.strip()] = val.strip()
                        schedule['news_monitors'].append(monitor)

                elif current_section == 'one_time':
                    # Format: YYYY-MM-DD HH:MM | text | priority
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        schedule['one_time'].append({
                            'datetime': parts[0],
                            'text': parts[1],
                            'priority': parts[2]
                        })

            logger.info(f'Loaded schedule: {len(schedule["daily_recurring"])} daily, '
                       f'{len(schedule["news_monitors"])} monitors, '
                       f'{len(schedule["one_time"])} one-time')
            return schedule

        except Exception as e:
            logger.error(f'Error loading schedule: {e}')
            return {}

    def expand_template_vars(self, text):
        """Replace template variables like {date}, {weather_summary}, etc."""
        try:
            now = datetime.now()

            # Simple replacements
            text = text.replace('{date}', now.strftime('%B %d, %Y'))
            text = text.replace('{time}', now.strftime('%I:%M %p'))

            # API-based replacements
            if '{weather_summary}' in text:
                weather = self.get_weather()
                text = text.replace('{weather_summary}', weather)

            if '{task_count}' in text:
                count = self.get_task_count()
                text = text.replace('{task_count}', str(count))

            if '{fetch_poem}' in text:
                poem = self.get_daily_poem()
                text = text.replace('{fetch_poem}', poem)

            if '{hackernews_top}' in text:
                hn_story = self.get_hackernews_top()
                text = text.replace('{hackernews_top}', hn_story)

            return text

        except Exception as e:
            logger.error(f'Error expanding template vars: {e}')
            return text

    def get_weather(self):
        """Get weather summary from Moneo API"""
        try:
            response = requests.get(f'{MONEO_API_BASE}/weather/pittsburgh', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return f"It's {data['temp']} degrees and {data['condition']}"
            return "Weather unavailable"
        except Exception as e:
            logger.warning(f'Failed to get weather: {e}')
            return "Weather unavailable"

    def get_task_count(self):
        """Count pending tasks from tasks.md"""
        try:
            tasks_file = '/root/moneo/data/obsidian/tasks/tasks.md'
            if not os.path.exists(tasks_file):
                return 0

            with open(tasks_file, 'r') as f:
                content = f.read()

            # Count unchecked tasks - [ ]
            return content.count('- [ ]')
        except Exception as e:
            logger.warning(f'Failed to count tasks: {e}')
            return 0

    def get_daily_poem(self):
        """Fetch a poem excerpt (placeholder - needs real API)"""
        # TODO: Integrate with Poetry Foundation API or similar
        return "A poem for today: placeholder content"

    def get_hackernews_top(self):
        """Get top HackerNews story"""
        try:
            # HN API: https://hacker-news.firebaseio.com/v0/topstories.json
            response = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=5)
            if response.status_code == 200:
                story_ids = response.json()[:1]  # Get top story
                story_response = requests.get(
                    f'https://hacker-news.firebaseio.com/v0/item/{story_ids[0]}.json',
                    timeout=5
                )
                if story_response.status_code == 200:
                    story = story_response.json()
                    return story.get('title', 'No title')
            return "No top story available"
        except Exception as e:
            logger.warning(f'Failed to get HN story: {e}')
            return "News unavailable"

    def check_daily_recurring(self, schedule):
        """Check if any daily recurring events should trigger"""
        now = datetime.now()
        current_time = now.strftime('%H:%M')

        for event in schedule.get('daily_recurring', []):
            event_time = event['time']
            event_key = f"daily_{event_time}"

            # Check if it's time to trigger
            if event_time == current_time:
                # Prevent duplicate triggers within same minute
                last_trigger = self.last_triggered.get(event_key)
                if last_trigger and (now - last_trigger).seconds < 60:
                    continue

                # Expand template variables
                text = self.expand_template_vars(event['text'])

                # Send announcement
                self.send_announcement(text, event['priority'])
                self.last_triggered[event_key] = now
                logger.info(f'Triggered daily event: {event_time} - {text[:50]}...')

    def check_one_time_reminders(self, schedule):
        """Check if any one-time reminders should trigger"""
        now = datetime.now()

        for event in schedule.get('one_time', []):
            try:
                event_datetime = datetime.strptime(event['datetime'], '%Y-%m-%d %H:%M')
                event_key = f"onetime_{event['datetime']}"

                # Check if event time has passed and not already triggered
                if now >= event_datetime and event_key not in self.last_triggered:
                    # Within 2 minutes of scheduled time
                    if (now - event_datetime).seconds < 120:
                        text = self.expand_template_vars(event['text'])
                        self.send_announcement(text, event['priority'])
                        self.last_triggered[event_key] = now
                        logger.info(f'Triggered one-time reminder: {event["datetime"]} - {text[:50]}...')
            except Exception as e:
                logger.error(f'Error parsing one-time event: {e}')

    def check_news_monitors(self, schedule):
        """Check news monitors for new items"""
        now = datetime.now()

        for monitor in schedule.get('news_monitors', []):
            source = monitor.get('source', '')
            interval = monitor.get('interval', '30min')
            priority = monitor.get('priority', 'medium')

            # Parse interval (e.g., "30min", "1hour")
            interval_match = re.match(r'(\d+)(min|hour)', interval)
            if not interval_match:
                continue

            amount, unit = interval_match.groups()
            amount = int(amount)

            if unit == 'min':
                interval_seconds = amount * 60
            elif unit == 'hour':
                interval_seconds = amount * 3600
            else:
                continue

            # Check if enough time has passed since last check
            monitor_key = f"news_{source}"
            last_check = self.last_triggered.get(monitor_key)
            if last_check and (now - last_check).seconds < interval_seconds:
                continue

            # Check the news source
            if 'HackerNews' in source:
                self.check_hackernews(monitor, monitor_key, now)

            # Update last check time
            self.last_triggered[monitor_key] = now

    def check_hackernews(self, monitor, monitor_key, now):
        """Check HackerNews for high-scoring stories"""
        try:
            min_score = int(monitor.get('min_score', 200))

            response = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=5)
            if response.status_code != 200:
                return

            story_ids = response.json()[:5]  # Check top 5

            for story_id in story_ids:
                # Skip if we've already announced this story
                if story_id in self.news_cache.get('hn_announced', []):
                    continue

                story_response = requests.get(
                    f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json',
                    timeout=5
                )
                if story_response.status_code != 200:
                    continue

                story = story_response.json()
                score = story.get('score', 0)

                if score >= min_score:
                    title = story.get('title', 'No title')
                    text = f"Breaking tech news: {title}. Score: {score} points on HackerNews."

                    self.send_announcement(text, monitor.get('priority', 'medium'))

                    # Mark as announced
                    if 'hn_announced' not in self.news_cache:
                        self.news_cache['hn_announced'] = []
                    self.news_cache['hn_announced'].append(story_id)

                    logger.info(f'Announced HN story: {title} (score: {score})')
                    break  # Only announce one story per check

        except Exception as e:
            logger.error(f'Error checking HackerNews: {e}')

    def send_announcement(self, text, priority):
        """Send announcement to Oracle via FIFO"""
        try:
            # Create FIFO if it doesn't exist
            if not os.path.exists(FIFO_PATH):
                os.mkfifo(FIFO_PATH)
                logger.info(f'Created FIFO: {FIFO_PATH}')

            # Prepare message
            message = {
                'text': text,
                'priority': priority
            }

            # Write to FIFO (non-blocking)
            with open(FIFO_PATH, 'w') as fifo:
                json.dump(message, fifo)
                fifo.write('\n')

            logger.info(f'Sent announcement ({priority}): {text[:100]}...')

        except Exception as e:
            logger.error(f'Failed to send announcement: {e}')

    def run(self):
        """Main loop"""
        logger.info('Oracle Scheduler starting...')
        logger.info(f'Schedule file: {SCHEDULE_FILE}')
        logger.info(f'FIFO path: {FIFO_PATH}')
        logger.info(f'Check interval: {CHECK_INTERVAL}s')

        while True:
            try:
                # Reload schedule every iteration (allows live updates)
                schedule = self.load_schedule()

                if schedule:
                    self.check_daily_recurring(schedule)
                    self.check_one_time_reminders(schedule)
                    self.check_news_monitors(schedule)

                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info('Received interrupt signal, shutting down...')
                break
            except Exception as e:
                logger.error(f'Error in main loop: {e}')
                time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    scheduler = OracleScheduler()
    scheduler.run()
