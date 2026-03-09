"""
Forecasting service.
Generates sales forecasts based on pipeline data and historical trends.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.pipeline.models import Deal, Stage

from .models import Forecast, ForecastPeriod

logger = logging.getLogger(__name__)


class ForecastingService:
    """Service for generating and managing sales forecasts."""

    def generate_forecast(
        self,
        pipeline_id=None,
        team_id=None,
        sales_rep_id=None,
        forecast_type="monthly",
        start_date=None,
        end_date=None,
        created_by=None,
    ):
        """
        Generate a new forecast based on current pipeline data.
        Uses weighted pipeline method combined with historical conversion rates.
        """
        today = timezone.now().date()

        if not start_date:
            start_date = today.replace(day=1)
        if not end_date:
            if forecast_type == "monthly":
                next_month = (start_date.replace(day=28) + timedelta(days=4))
                end_date = next_month.replace(day=1) - timedelta(days=1)
            elif forecast_type == "quarterly":
                end_date = start_date + timedelta(days=90)
            else:
                end_date = start_date.replace(year=start_date.year + 1) - timedelta(days=1)

        # Get deals in scope
        deals_qs = Deal.objects.filter(status=Deal.Status.OPEN)
        if pipeline_id:
            deals_qs = deals_qs.filter(pipeline_id=pipeline_id)
        if sales_rep_id:
            deals_qs = deals_qs.filter(assigned_to_id=sales_rep_id)
        if team_id:
            deals_qs = deals_qs.filter(
                assigned_to__sales_profile__team_id=team_id
            )

        # Filter by expected close date within forecast period
        period_deals = deals_qs.filter(
            expected_close_date__gte=start_date,
            expected_close_date__lte=end_date,
        ).select_related("stage")

        # Calculate weighted pipeline value
        weighted_total = Decimal("0")
        best_case_total = Decimal("0")
        worst_case_total = Decimal("0")
        committed_total = Decimal("0")

        deal_details = []
        for deal in period_deals:
            probability = Decimal(str(deal.stage.probability)) / Decimal("100")
            weighted_value = deal.value * probability

            weighted_total += weighted_value
            best_case_total += deal.value  # 100% of all deals
            worst_case_total += deal.value * max(probability - Decimal("0.2"), Decimal("0"))

            # Committed deals are those in high-probability stages (>70%)
            if deal.stage.probability >= 70:
                committed_total += deal.value

            deal_details.append(
                {
                    "deal_id": str(deal.id),
                    "title": deal.title,
                    "value": float(deal.value),
                    "stage": deal.stage.name,
                    "probability": deal.stage.probability,
                    "weighted_value": float(weighted_value),
                    "expected_close": str(deal.expected_close_date),
                }
            )

        # Adjust predicted revenue using historical conversion rates
        historical_rate = self._get_historical_conversion_rate(
            pipeline_id=pipeline_id,
            team_id=team_id,
            sales_rep_id=sales_rep_id,
        )

        predicted_revenue = weighted_total * Decimal(str(historical_rate))

        # Create forecast
        name = f"Forecast {start_date.strftime('%B %Y')}"
        if forecast_type == "quarterly":
            quarter = (start_date.month - 1) // 3 + 1
            name = f"Forecast Q{quarter} {start_date.year}"
        elif forecast_type == "yearly":
            name = f"Forecast {start_date.year}"

        forecast = Forecast.objects.create(
            name=name,
            forecast_type=forecast_type,
            pipeline_id=pipeline_id,
            team_id=team_id,
            sales_rep_id=sales_rep_id,
            start_date=start_date,
            end_date=end_date,
            predicted_revenue=predicted_revenue,
            best_case=best_case_total,
            worst_case=worst_case_total,
            weighted_pipeline=weighted_total,
            committed=committed_total,
            calculation_details={
                "historical_conversion_rate": historical_rate,
                "deal_count": len(deal_details),
                "deals": deal_details,
            },
            created_by=created_by,
        )

        # Generate sub-period breakdown
        self._generate_periods(forecast, period_deals)

        logger.info(
            f"Forecast generated: {forecast.name} - "
            f"Predicted: {predicted_revenue}, Weighted: {weighted_total}"
        )

        return forecast

    def _get_historical_conversion_rate(
        self, pipeline_id=None, team_id=None, sales_rep_id=None, lookback_days=180
    ):
        """
        Calculate historical conversion rate (won deals / closed deals).
        Returns a multiplier to adjust weighted pipeline predictions.
        """
        cutoff = timezone.now() - timedelta(days=lookback_days)
        closed_deals = Deal.objects.filter(
            status__in=[Deal.Status.WON, Deal.Status.LOST],
            actual_close_date__gte=cutoff.date(),
        )

        if pipeline_id:
            closed_deals = closed_deals.filter(pipeline_id=pipeline_id)
        if sales_rep_id:
            closed_deals = closed_deals.filter(assigned_to_id=sales_rep_id)
        if team_id:
            closed_deals = closed_deals.filter(
                assigned_to__sales_profile__team_id=team_id
            )

        total_closed = closed_deals.count()
        won = closed_deals.filter(status=Deal.Status.WON).count()

        if total_closed == 0:
            return 1.0  # No historical data, use weighted pipeline as-is

        rate = won / total_closed

        # Apply a correction factor: if historical rate is significantly
        # different from stage probabilities, we adjust
        return max(min(rate * 1.1, 1.5), 0.5)  # Cap between 0.5x and 1.5x

    def _generate_periods(self, forecast, deals):
        """Generate weekly sub-periods within the forecast range."""
        current = forecast.start_date
        week_num = 1

        while current <= forecast.end_date:
            period_end = min(current + timedelta(days=6), forecast.end_date)
            period_deals = deals.filter(
                expected_close_date__gte=current,
                expected_close_date__lte=period_end,
            )

            period_weighted = sum(
                float(d.value) * (d.stage.probability / 100)
                for d in period_deals
            )

            ForecastPeriod.objects.create(
                forecast=forecast,
                period_start=current,
                period_end=period_end,
                label=f"Week {week_num}",
                predicted_revenue=Decimal(str(period_weighted)),
                deal_count=period_deals.count(),
                weighted_value=Decimal(str(period_weighted)),
                metadata={
                    "deal_ids": [str(d.id) for d in period_deals],
                },
            )

            current = period_end + timedelta(days=1)
            week_num += 1

    def update_actuals(self, forecast_id):
        """Update forecast with actual revenue for completed periods."""
        forecast = Forecast.objects.get(id=forecast_id)
        today = timezone.now().date()

        won_deals = Deal.objects.filter(
            status=Deal.Status.WON,
            actual_close_date__gte=forecast.start_date,
            actual_close_date__lte=min(forecast.end_date, today),
        )

        if forecast.pipeline:
            won_deals = won_deals.filter(pipeline=forecast.pipeline)
        if forecast.sales_rep:
            won_deals = won_deals.filter(assigned_to=forecast.sales_rep)
        if forecast.team:
            won_deals = won_deals.filter(
                assigned_to__sales_profile__team=forecast.team
            )

        actual = won_deals.aggregate(total=Sum("value"))["total"] or 0
        forecast.actual_revenue = actual
        forecast.save(update_fields=["actual_revenue", "updated_at"])

        # Update sub-periods
        for period in forecast.periods.all():
            if period.period_end <= today:
                period_won = won_deals.filter(
                    actual_close_date__gte=period.period_start,
                    actual_close_date__lte=period.period_end,
                )
                period.actual_revenue = (
                    period_won.aggregate(total=Sum("value"))["total"] or 0
                )
                period.save(update_fields=["actual_revenue"])

        return forecast
