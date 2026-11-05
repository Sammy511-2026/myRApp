from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from recruitment.models import RecruitmentCycle, User

class Command(BaseCommand):
    help = "Create a sample active recruitment cycle (for local dev/testing)."

    def handle(self, *args, **options):
        today = date.today()
        start = today - timedelta(days=7)
        end = today + timedelta(days=60)

        admin = User.objects.filter(role=User.Roles.ADMIN).first()

        cycle, created = RecruitmentCycle.objects.get_or_create(
            name="Police Intake",
            intake_year=today.year,
            rec_type=RecruitmentCycle.RecType.REGULAR,
            defaults=dict(
                start_date=start,
                end_date=end,
                is_active=True,
                min_age=18,
                max_age=30,
                min_education_level=12,
                created_by=admin,
            )
        )
        if not created:
            cycle.is_active = True
            cycle.start_date = start
            cycle.end_date = end
            cycle.save()

        self.stdout.write(self.style.SUCCESS(f"Active cycle ready: {cycle}"))
