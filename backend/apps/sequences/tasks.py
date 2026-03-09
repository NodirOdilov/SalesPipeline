"""
Celery tasks for email sequences and automated follow-ups.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_sequence_email(self, enrollment_id):
    """
    Send an email for a specific sequence enrollment step.
    """
    from .models import SequenceEnrollment

    try:
        enrollment = SequenceEnrollment.objects.select_related(
            "sequence", "current_step", "lead"
        ).get(id=enrollment_id)

        if enrollment.status != SequenceEnrollment.Status.ACTIVE:
            logger.info(f"Enrollment {enrollment_id} is not active. Skipping.")
            return

        step = enrollment.current_step
        if not step or step.step_type != "email":
            logger.info(f"Current step for enrollment {enrollment_id} is not an email step.")
            return

        lead = enrollment.lead

        # Render email template with lead context
        context = Context({
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "full_name": lead.full_name,
            "company": lead.company,
            "email": lead.email,
            "job_title": lead.job_title,
        })

        subject = Template(step.subject).render(context)
        body_html = Template(step.body_html).render(context)
        body_text = Template(step.body_text).render(context) if step.body_text else ""

        # Determine sender
        from_email = settings.DEFAULT_FROM_EMAIL
        if enrollment.sequence.send_as and enrollment.sequence.send_as.email:
            from_email = enrollment.sequence.send_as.email

        # Send email
        send_mail(
            subject=subject,
            message=body_text,
            from_email=from_email,
            recipient_list=[lead.email],
            html_message=body_html,
            fail_silently=False,
        )

        # Update enrollment tracking
        enrollment.emails_sent += 1
        enrollment.last_step_completed = step
        enrollment.save(update_fields=["emails_sent", "last_step_completed"])

        # Log activity
        from apps.leads.models import LeadActivity

        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.EMAIL_SENT,
            title=f"Sequence email sent: {subject}",
            description=f"Step {step.order} of sequence '{enrollment.sequence.name}'",
            metadata={
                "sequence_id": str(enrollment.sequence.id),
                "step_id": str(step.id),
                "step_order": step.order,
                "subject": subject,
            },
        )

        # Schedule next step
        _advance_enrollment(enrollment)

        logger.info(
            f"Sequence email sent to {lead.email} "
            f"(sequence: {enrollment.sequence.name}, step: {step.order})"
        )

    except Exception as exc:
        logger.error(f"Failed to send sequence email for enrollment {enrollment_id}: {exc}")
        raise self.retry(exc=exc)


def _advance_enrollment(enrollment):
    """Move enrollment to the next step or mark as completed."""
    current_step = enrollment.current_step
    next_steps = enrollment.sequence.steps.filter(
        order__gt=current_step.order, is_active=True
    ).order_by("order")

    next_step = next_steps.first()
    if next_step:
        enrollment.current_step = next_step
        delay = timedelta(days=next_step.delay_days, hours=next_step.delay_hours)
        enrollment.next_step_scheduled_at = timezone.now() + delay
        enrollment.save(
            update_fields=["current_step", "next_step_scheduled_at"]
        )
    else:
        # Sequence completed
        enrollment.status = SequenceEnrollment.Status.COMPLETED
        enrollment.completed_at = timezone.now()
        enrollment.current_step = None
        enrollment.next_step_scheduled_at = None
        enrollment.save(
            update_fields=["status", "completed_at", "current_step", "next_step_scheduled_at"]
        )
        logger.info(
            f"Sequence completed for lead {enrollment.lead.email} "
            f"in sequence {enrollment.sequence.name}"
        )


@shared_task
def process_pending_sequence_steps():
    """
    Process all pending sequence steps that are due.
    Called periodically by Celery Beat.
    """
    from .models import SequenceEnrollment

    now = timezone.now()
    pending = SequenceEnrollment.objects.filter(
        status=SequenceEnrollment.Status.ACTIVE,
        next_step_scheduled_at__lte=now,
        current_step__isnull=False,
    ).select_related("current_step", "sequence")

    count = 0
    for enrollment in pending:
        step = enrollment.current_step
        if step.step_type == "email":
            send_sequence_email.delay(str(enrollment.id))
            count += 1
        elif step.step_type == "wait":
            _advance_enrollment(enrollment)
            count += 1
        elif step.step_type == "task":
            _create_follow_up_task(enrollment)
            _advance_enrollment(enrollment)
            count += 1

    logger.info(f"Processed {count} pending sequence steps.")
    return count


def _create_follow_up_task(enrollment):
    """Create a follow-up task activity for the assigned rep."""
    from apps.leads.models import LeadActivity

    lead = enrollment.lead
    step = enrollment.current_step

    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.TASK,
        title=f"Follow-up task: {step.task_description or 'Follow up with lead'}",
        description=(
            f"Auto-generated task from sequence '{enrollment.sequence.name}', "
            f"step {step.order}."
        ),
        performed_by=lead.assigned_to,
        metadata={
            "sequence_id": str(enrollment.sequence.id),
            "step_id": str(step.id),
            "auto_generated": True,
        },
    )


@shared_task
def send_follow_up_reminders():
    """
    Send follow-up reminders for leads with past-due follow-up dates.
    Called daily by Celery Beat.
    """
    from apps.leads.models import Lead

    now = timezone.now()
    overdue_leads = Lead.objects.filter(
        next_follow_up__lt=now,
        status__in=[Lead.Status.NEW, Lead.Status.CONTACTED, Lead.Status.QUALIFIED],
        assigned_to__isnull=False,
    ).select_related("assigned_to")

    count = 0
    for lead in overdue_leads:
        try:
            send_mail(
                subject=f"Follow-up reminder: {lead.full_name} ({lead.company})",
                message=(
                    f"Hi {lead.assigned_to.first_name},\n\n"
                    f"This is a reminder to follow up with {lead.full_name} "
                    f"from {lead.company}.\n\n"
                    f"The follow-up was due on {lead.next_follow_up.strftime('%B %d, %Y at %I:%M %p')}.\n\n"
                    f"Lead email: {lead.email}\n"
                    f"Lead phone: {lead.phone or 'N/A'}\n\n"
                    f"-- SalesPipeline"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[lead.assigned_to.email],
                fail_silently=True,
            )
            count += 1
        except Exception as e:
            logger.error(f"Failed to send follow-up reminder for lead {lead.id}: {e}")

    logger.info(f"Sent {count} follow-up reminders.")
    return count


@shared_task
def enroll_lead_in_sequence(sequence_id, lead_id, enrolled_by_id=None):
    """
    Enroll a lead in a sequence. Creates the enrollment and schedules the first step.
    """
    from apps.leads.models import Lead
    from .models import EmailSequence, SequenceEnrollment

    try:
        sequence = EmailSequence.objects.get(id=sequence_id)
        lead = Lead.objects.get(id=lead_id)
    except (EmailSequence.DoesNotExist, Lead.DoesNotExist) as e:
        logger.error(f"Failed to enroll lead {lead_id} in sequence {sequence_id}: {e}")
        return

    if sequence.status != EmailSequence.Status.ACTIVE:
        logger.warning(f"Cannot enroll in inactive sequence {sequence_id}")
        return

    # Check if already enrolled
    if SequenceEnrollment.objects.filter(sequence=sequence, lead=lead).exists():
        logger.info(f"Lead {lead_id} already enrolled in sequence {sequence_id}")
        return

    first_step = sequence.steps.filter(is_active=True).order_by("order").first()
    if not first_step:
        logger.warning(f"Sequence {sequence_id} has no active steps")
        return

    delay = timedelta(days=first_step.delay_days, hours=first_step.delay_hours)

    enrollment = SequenceEnrollment.objects.create(
        sequence=sequence,
        lead=lead,
        status=SequenceEnrollment.Status.ACTIVE,
        current_step=first_step,
        next_step_scheduled_at=timezone.now() + delay,
        enrolled_by_id=enrolled_by_id,
    )

    logger.info(
        f"Lead {lead.email} enrolled in sequence '{sequence.name}'. "
        f"First step scheduled at {enrollment.next_step_scheduled_at}"
    )

    return str(enrollment.id)
