from django import template
from django.utils import timezone

from recruitment.models import ApplicantProfile, Application, Document, InterviewSchedule, RecruitmentCycle

register = template.Library()


@register.simple_tag
def dashboard_metrics():
    now = timezone.now()
    return {
        "applicants": ApplicantProfile.objects.count(),
        "submitted_applications": Application.objects.filter(submitted_at__isnull=False).count(),
        "applications_in_review": Application.objects.filter(
            submitted_at__isnull=False,
            status__in=(Application.Status.PENDING, Application.Status.SCREENING),
        ).count(),
        "documents_to_review": Document.objects.filter(
            verify_status=Document.VerifyStatus.PENDING,
        ).count(),
        "upcoming_interviews": InterviewSchedule.objects.filter(
            scheduled_at__gte=now,
            status=InterviewSchedule.Status.SCHEDULED,
        ).count(),
        "active_cycle": RecruitmentCycle.objects.filter(is_active=True).order_by("-start_date").first(),
    }
