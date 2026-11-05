from datetime import date

from django.test import TestCase
from django.urls import reverse

from recruitment.models import (
    AlternativeContact,
    ApplicantProfile,
    Application,
    RecruitmentCycle,
    User,
)


class ApplicantApplicationPrintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="print-applicant",
            password="test-password",
            role=User.Roles.APPLICANT,
        )
        self.profile = self.user.profile
        self.profile.full_name = "Print Applicant"
        self.profile.dob = date(2000, 1, 1)
        self.profile.gender = ApplicantProfile.Gender.OTHER
        self.profile.save()
        self.cycle = RecruitmentCycle.objects.create(
            name="Regular Recruit",
            intake_year=2026,
            start_date="2026-01-01",
            end_date="2026-12-31",
            is_active=True,
        )
        self.application = Application.objects.create(
            applicant=self.profile,
            cycle=self.cycle,
            applied_unit="National Capital District",
        )
        AlternativeContact.objects.create(
            applicant=self.profile,
            name="Print Contact",
            relationship="Sibling",
        )
        self.client.force_login(self.user)

    def test_application_print_page_includes_application_and_contacts(self):
        response = self.client.get(reverse("recruitment:application_print"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RPNGC Recruitment Application")
        self.assertContains(response, "Print Applicant")
        self.assertContains(response, "National Capital District")
        self.assertContains(response, "Print Contact")
        self.assertContains(response, "Print / Download as PDF")
