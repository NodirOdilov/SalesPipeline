"""
Lead scoring service.
Calculates lead scores based on demographic, behavioral, engagement,
and firmographic signals.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from .models import Lead, LeadActivity, LeadScore

logger = logging.getLogger(__name__)

# Scoring weights
DEMOGRAPHIC_WEIGHT = 0.25
BEHAVIORAL_WEIGHT = 0.30
ENGAGEMENT_WEIGHT = 0.25
FIRMOGRAPHIC_WEIGHT = 0.20

# Max score per category
MAX_CATEGORY_SCORE = 100


class LeadScoringService:
    """Service for calculating and updating lead scores."""

    # Industries with higher conversion rates
    HIGH_VALUE_INDUSTRIES = [
        "technology",
        "finance",
        "healthcare",
        "saas",
        "enterprise software",
    ]

    # Job titles indicating decision-maker status
    DECISION_MAKER_TITLES = [
        "ceo",
        "cto",
        "cfo",
        "coo",
        "vp",
        "vice president",
        "director",
        "head of",
        "chief",
        "president",
        "owner",
        "founder",
    ]

    INFLUENCER_TITLES = [
        "manager",
        "lead",
        "senior",
        "principal",
        "architect",
    ]

    def calculate_score(self, lead: Lead) -> LeadScore:
        """
        Calculate a comprehensive lead score and persist it.
        Returns the new LeadScore instance.
        """
        demographic = self._calculate_demographic_score(lead)
        behavioral = self._calculate_behavioral_score(lead)
        engagement = self._calculate_engagement_score(lead)
        firmographic = self._calculate_firmographic_score(lead)

        total = int(
            demographic * DEMOGRAPHIC_WEIGHT
            + behavioral * BEHAVIORAL_WEIGHT
            + engagement * ENGAGEMENT_WEIGHT
            + firmographic * FIRMOGRAPHIC_WEIGHT
        )

        score = LeadScore.objects.create(
            lead=lead,
            demographic_score=demographic,
            behavioral_score=behavioral,
            engagement_score=engagement,
            firmographic_score=firmographic,
            total_score=total,
            score_details={
                "demographic": {
                    "score": demographic,
                    "weight": DEMOGRAPHIC_WEIGHT,
                    "weighted": int(demographic * DEMOGRAPHIC_WEIGHT),
                },
                "behavioral": {
                    "score": behavioral,
                    "weight": BEHAVIORAL_WEIGHT,
                    "weighted": int(behavioral * BEHAVIORAL_WEIGHT),
                },
                "engagement": {
                    "score": engagement,
                    "weight": ENGAGEMENT_WEIGHT,
                    "weighted": int(engagement * ENGAGEMENT_WEIGHT),
                },
                "firmographic": {
                    "score": firmographic,
                    "weight": FIRMOGRAPHIC_WEIGHT,
                    "weighted": int(firmographic * FIRMOGRAPHIC_WEIGHT),
                },
            },
        )

        # Log score update
        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.SCORE_UPDATE,
            title=f"Lead score updated to {total}",
            metadata={"score_id": str(score.id), "total_score": total},
        )

        # Auto-update priority based on score
        self._update_priority(lead, total)

        logger.info(f"Lead {lead.id} scored: {total} (D:{demographic} B:{behavioral} E:{engagement} F:{firmographic})")
        return score

    def _calculate_demographic_score(self, lead: Lead) -> int:
        """Score based on contact information completeness and quality."""
        score = 0

        # Contact info completeness
        if lead.email:
            score += 15
            # Business email is more valuable
            personal_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
            domain = lead.email.split("@")[-1].lower()
            if domain not in personal_domains:
                score += 10

        if lead.phone:
            score += 10
        if lead.company:
            score += 10
        if lead.job_title:
            score += 10

        # Decision-maker bonus
        title_lower = (lead.job_title or "").lower()
        if any(t in title_lower for t in self.DECISION_MAKER_TITLES):
            score += 25
        elif any(t in title_lower for t in self.INFLUENCER_TITLES):
            score += 15

        # Location completeness
        if lead.city and lead.country:
            score += 5
        if lead.website:
            score += 5

        return min(score, MAX_CATEGORY_SCORE)

    def _calculate_behavioral_score(self, lead: Lead) -> int:
        """Score based on lead activities and interactions."""
        score = 0
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)

        activities = lead.activities.filter(created_at__gte=last_30_days)

        # Activity counts
        activity_counts = {}
        for activity in activities:
            activity_type = activity.activity_type
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1

        # Email engagement
        emails_opened = activity_counts.get(LeadActivity.ActivityType.EMAIL_OPENED, 0)
        emails_replied = activity_counts.get(LeadActivity.ActivityType.EMAIL_REPLIED, 0)
        score += min(emails_opened * 5, 20)
        score += min(emails_replied * 15, 30)

        # Website visits
        website_visits = activity_counts.get(LeadActivity.ActivityType.WEBSITE_VISIT, 0)
        score += min(website_visits * 3, 15)

        # Form submissions
        form_submissions = activity_counts.get(LeadActivity.ActivityType.FORM_SUBMISSION, 0)
        score += min(form_submissions * 10, 20)

        # Meeting scheduled
        meetings = activity_counts.get(LeadActivity.ActivityType.MEETING, 0)
        score += min(meetings * 15, 30)

        # Recency bonus - extra points for recent activity
        recent_activities = lead.activities.filter(created_at__gte=last_7_days).count()
        if recent_activities > 0:
            score += min(recent_activities * 3, 15)

        return min(score, MAX_CATEGORY_SCORE)

    def _calculate_engagement_score(self, lead: Lead) -> int:
        """Score based on engagement level and responsiveness."""
        score = 0

        # Status-based scoring
        status_scores = {
            Lead.Status.NEW: 10,
            Lead.Status.CONTACTED: 25,
            Lead.Status.QUALIFIED: 50,
            Lead.Status.CONVERTED: 100,
            Lead.Status.UNQUALIFIED: 5,
            Lead.Status.LOST: 0,
        }
        score += status_scores.get(lead.status, 0)

        # Recency of last contact
        if lead.last_contacted_at:
            days_since_contact = (timezone.now() - lead.last_contacted_at).days
            if days_since_contact <= 1:
                score += 25
            elif days_since_contact <= 7:
                score += 15
            elif days_since_contact <= 30:
                score += 5
            else:
                score -= 10  # Penalize stale leads

        # Follow-up scheduled
        if lead.next_follow_up:
            if lead.next_follow_up >= timezone.now():
                score += 10  # Active follow-up scheduled

        # Estimated deal value bonus
        if lead.estimated_value > 0:
            if lead.estimated_value >= 100000:
                score += 15
            elif lead.estimated_value >= 50000:
                score += 10
            elif lead.estimated_value >= 10000:
                score += 5

        return min(max(score, 0), MAX_CATEGORY_SCORE)

    def _calculate_firmographic_score(self, lead: Lead) -> int:
        """Score based on company/firmographic data."""
        score = 0

        # Industry match
        industry_lower = (lead.industry or "").lower()
        if any(ind in industry_lower for ind in self.HIGH_VALUE_INDUSTRIES):
            score += 30

        # Company information completeness
        if lead.company:
            score += 15
        if lead.industry:
            score += 10
        if lead.website:
            score += 10

        # Tags can indicate additional firmographic signals
        high_value_tags = ["enterprise", "mid-market", "funded", "growing"]
        if lead.tags:
            matching_tags = [t for t in lead.tags if t.lower() in high_value_tags]
            score += len(matching_tags) * 10

        # Estimated value as a firmographic proxy
        if lead.estimated_value >= 100000:
            score += 25
        elif lead.estimated_value >= 50000:
            score += 15
        elif lead.estimated_value >= 10000:
            score += 10

        return min(score, MAX_CATEGORY_SCORE)

    def _update_priority(self, lead: Lead, score: int):
        """Automatically adjust lead priority based on score."""
        if score >= 75:
            new_priority = Lead.Priority.CRITICAL
        elif score >= 50:
            new_priority = Lead.Priority.HIGH
        elif score >= 25:
            new_priority = Lead.Priority.MEDIUM
        else:
            new_priority = Lead.Priority.LOW

        if lead.priority != new_priority:
            old_priority = lead.priority
            lead.priority = new_priority
            lead.save(update_fields=["priority", "updated_at"])

            LeadActivity.objects.create(
                lead=lead,
                activity_type=LeadActivity.ActivityType.STATUS_CHANGE,
                title=f"Priority changed from {old_priority} to {new_priority}",
                metadata={
                    "old_priority": old_priority,
                    "new_priority": new_priority,
                    "triggered_by": "auto_scoring",
                },
            )


def calculate_lead_score(lead_id: str) -> LeadScore:
    """Convenience function to score a single lead by ID."""
    lead = Lead.objects.get(id=lead_id)
    service = LeadScoringService()
    return service.calculate_score(lead)


def recalculate_all_scores():
    """Recalculate scores for all active leads."""
    service = LeadScoringService()
    leads = Lead.objects.exclude(status__in=[Lead.Status.CONVERTED, Lead.Status.LOST])
    results = []
    for lead in leads:
        try:
            score = service.calculate_score(lead)
            results.append({"lead_id": str(lead.id), "score": score.total_score})
        except Exception as e:
            logger.error(f"Error scoring lead {lead.id}: {e}")
            results.append({"lead_id": str(lead.id), "error": str(e)})
    return results
