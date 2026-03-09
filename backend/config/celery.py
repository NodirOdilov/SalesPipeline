"""
Celery configuration for SalesPipeline project.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("salespipeline")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    "recalculate-lead-scores": {
        "task": "apps.leads.tasks.recalculate_all_lead_scores",
        "schedule": crontab(hour="*/6", minute=0),
    },
    "process-email-sequences": {
        "task": "apps.sequences.tasks.process_pending_sequence_steps",
        "schedule": crontab(minute="*/15"),
    },
    "generate-daily-forecast": {
        "task": "apps.forecasting.tasks.generate_daily_forecast",
        "schedule": crontab(hour=1, minute=0),
    },
    "send-follow-up-reminders": {
        "task": "apps.sequences.tasks.send_follow_up_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
