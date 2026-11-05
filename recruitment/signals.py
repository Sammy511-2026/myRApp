from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import InterviewSchedule, Notification

@receiver(post_save, sender=InterviewSchedule)
def notify_interview_created(sender, instance: InterviewSchedule, created, **kwargs):
    if not created:
        return
    app = instance.application
    try:
        Notification.objects.create(
            user=app.applicant.user,
            ntype=Notification.NType.INTERVIEW,
            title="Interview scheduled",
            body=f"Your interview is on {instance.scheduled_at:%Y-%m-%d %H:%M} at {instance.location or 'TBA'}.",
            ref_model="interviewschedule",
            ref_id=instance.pk,
        )
    except Exception:
        pass
