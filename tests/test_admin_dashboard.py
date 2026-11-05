from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from recruitment.models import (
    AlternativeContact,
    ApplicantProfile,
    Application,
    EducationRecord,
    ParentGuardian,
    RecruitmentCycle,
    Reference,
    User,
    WorkHistory,
)


class AdminDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="dashboard-admin",
            email="dashboard-admin@example.com",
            password="test-password",
        )

    def test_admin_index_renders_rpngc_dashboard(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/rpngc_index.html")
        self.assertContains(response, "Operations dashboard")
        self.assertContains(response, "Registered applicants")
        self.assertContains(response, "Administration areas")
        self.assertContains(response, "recruitment/css/rpngc_admin.css")
        self.assertContains(response, "recruitment/js/admin_overrides.js")

    def test_admin_login_uses_branded_login_page_and_logo(self):
        response = self.client.get(reverse("admin:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/rpngc_login.html")
        self.assertContains(response, "Recruitment portal")
        self.assertContains(response, "Authorized Royal Papua New Guinea Constabulary personnel only.")
        self.assertContains(response, "/static/recruitment/images/Logo.png")
        self.assertContains(response, "recruitment/css/rpngc_admin.css")

    def test_custom_admin_action_urls_are_mounted(self):
        action_names = (
            "recruitment_application_approve",
            "recruitment_application_reject",
            "recruitment_application_shortlist",
        )

        for action_name in action_names:
            with self.subTest(action=action_name):
                action_url = reverse(
                    f"rpngc_admin:{action_name}",
                    args=[1],
                )
                self.assertTrue(action_url.startswith("/rpngc-admin/"))

    def test_staff_control_center_uses_one_navigation_interface(self):
        self.admin_user.role = get_user_model().Roles.ADMIN
        self.admin_user.save(update_fields=["role"])
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("recruitment:staff_dashboard"))

        self.assertRedirects(response, reverse("admin:index"))

    def test_admin_loads_asset_that_suppresses_embedded_navigation(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "recruitment/js/admin_overrides.js")
    def test_applicant_changelist_combines_profile_and_application_details(self):
        applicant_user = get_user_model().objects.create_user(
            username="table-applicant",
            password="test-password",
        )
        applicant = applicant_user.profile
        applicant.full_name = "Table Applicant"
        applicant.dob = "2000-01-02"
        applicant.gender = ApplicantProfile.Gender.FEMALE
        applicant.nid_number = "123456"
        applicant.email = "applicant@example.com"
        applicant.phone = "70000000"
        applicant.save()
        cycle = RecruitmentCycle.objects.create(
            name="2026 Intake",
            intake_year=2026,
            start_date="2026-01-01",
            end_date="2026-12-31",
        )
        Application.objects.create(applicant=applicant, cycle=cycle)

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("admin:recruitment_applicantprofile_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nid number")
        self.assertContains(response, "Phone")
        self.assertContains(response, "Latest intake")
        self.assertContains(response, "Application status")
        self.assertContains(response, "Table Applicant")
        self.assertContains(response, "123456")
        self.assertContains(response, "70000000")
        self.assertContains(response, "2026 Intake")
        self.assertContains(response, "Pending")

    def test_default_applicant_profile_displays_full_application_and_record_inlines(self):
        applicant_user = User.objects.create_user(
            username="default-profile-review",
            password="test-password",
        )
        applicant = applicant_user.profile
        applicant.full_name = "Default Profile Review"
        applicant.dob = "2000-01-02"
        applicant.save()
        cycle = RecruitmentCycle.objects.create(
            name="Default Admin Review Intake",
            intake_year=2026,
            start_date="2026-01-01",
            end_date="2026-12-31",
        )
        Application.objects.create(
            applicant=applicant,
            cycle=cycle,
            applied_unit="Gulf Province",
            reason_for_applying="Serve the community",
        )
        AlternativeContact.objects.create(applicant=applicant, name="Default Contact")
        EducationRecord.objects.create(
            applicant=applicant,
            level=EducationRecord.Level.G12,
            institution="Default High School",
        )
        WorkHistory.objects.create(applicant=applicant, employer="Default Employer")
        Reference.objects.create(applicant=applicant, name="Default Referee")
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("admin:recruitment_applicantprofile_change", args=[applicant.pk])
        )

        self.assertEqual(response.status_code, 200)
        for value in (
            "Applicant application review",
            "Default Admin Review Intake",
            "Gulf Province",
            "Serve the community",
            "Default Contact",
            "Default High School",
            "Default Employer",
            "Default Referee",
            "Shortlist",
            "Approve",
            "Reject",
            "Required documents",
        ):
            with self.subTest(value=value):
                self.assertContains(response, value)

    def test_custom_applicant_profile_shows_complete_application_and_review_data(self):
        applicant_user = User.objects.create_user(
            username="profile-review-applicant",
            password="test-password",
        )
        applicant = applicant_user.profile
        applicant.full_name = "Profile Review Applicant"
        applicant.dob = "2000-01-02"
        applicant.gender = ApplicantProfile.Gender.FEMALE
        applicant.email = "profile-review@example.com"
        applicant.save()
        cycle = RecruitmentCycle.objects.create(
            name="Profile Review Intake",
            intake_year=2026,
            start_date="2026-01-01",
            end_date="2026-12-31",
        )
        application = Application.objects.create(
            applicant=applicant,
            cycle=cycle,
            applied_unit="Central Province",
            reason_for_applying="To serve the community",
            signature_name="Profile Review Applicant",
        )
        AlternativeContact.objects.create(
            applicant=applicant,
            name="Alternative Contact",
        )
        ParentGuardian.objects.create(
            applicant=applicant,
            kind=ParentGuardian.Kind.GUARDIAN,
            name="Applicant Guardian",
        )
        EducationRecord.objects.create(
            applicant=applicant,
            level=EducationRecord.Level.G12,
            institution="Central High School",
        )
        WorkHistory.objects.create(
            applicant=applicant,
            employer="Community Services",
        )
        Reference.objects.create(
            applicant=applicant,
            name="Applicant Referee",
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("rpngc_admin:recruitment_applicantprofile_change", args=[applicant.pk])
        )

        self.assertEqual(response.status_code, 200)
        for value in (
            "Application details",
            "Central Province",
            "To serve the community",
            "Alternative Contact",
            "Applicant Guardian",
            "Central High School",
            "Community Services",
            "Applicant Referee",
            "Required documents",
            "Eligibility review",
            "Approve",
            "Reject",
            "Shortlist",
        ):
            with self.subTest(value=value):
                self.assertContains(response, value)

    def test_admin_can_shortlist_from_applicant_profile(self):
        applicant_user = User.objects.create_user(
            username="profile-action-applicant",
            password="test-password",
        )
        applicant = applicant_user.profile
        applicant.full_name = "Profile Action Applicant"
        applicant.save(update_fields=["full_name"])
        cycle = RecruitmentCycle.objects.create(
            name="Profile Action Intake",
            intake_year=2026,
            start_date="2026-01-01",
            end_date="2026-12-31",
        )
        application = Application.objects.create(applicant=applicant, cycle=cycle)
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                "rpngc_admin:recruitment_applicantprofile_application_action",
                args=[applicant.pk, "shortlist"],
            )
        )

        self.assertRedirects(
            response,
            reverse("rpngc_admin:recruitment_applicantprofile_change", args=[applicant.pk]),
        )
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.SHORTLISTED)

    def test_applicant_action_rejects_get_requests(self):
        applicant_user = User.objects.create_user(
            username="profile-get-action-applicant",
            password="test-password",
        )
        applicant = applicant_user.profile
        cycle = RecruitmentCycle.objects.create(
            name="Profile GET Action Intake",
            intake_year=2026,
            start_date="2026-01-01",
            end_date="2026-12-31",
        )
        Application.objects.create(applicant=applicant, cycle=cycle)
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                "rpngc_admin:recruitment_applicantprofile_application_action",
                args=[applicant.pk, "reject"],
            )
        )

        self.assertEqual(response.status_code, 405)
