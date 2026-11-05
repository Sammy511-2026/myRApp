from django.test import TestCase
from django.urls import reverse

from recruitment.models import RecruitmentCycle


class LandingPageTests(TestCase):
    def test_landing_page_shows_brand_purpose_and_applicant_actions(self):
        response = self.client.get(reverse("recruitment:landing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A career in service.")
        self.assertContains(response, "Service with pride. Integrity in every action.")
        self.assertContains(response, "Start your application")
        self.assertContains(response, "Applicant sign in")
        self.assertContains(response, "recruitment/css/landing.css")
        self.assertContains(response, "/static/recruitment/images/Logo.png")
        self.assertContains(response, "No active intake")

    def test_landing_page_displays_active_recruitment_cycle(self):
        RecruitmentCycle.objects.create(
            name="RPNGC Recruitment",
            intake_year=2026,
            start_date="2026-10-01",
            end_date="2026-12-31",
            is_active=True,
        )

        response = self.client.get(reverse("recruitment:landing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RPNGC Recruitment")
        self.assertContains(response, "Applications open")
