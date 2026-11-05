from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from recruitment.models import (
    ApplicantProfile,
    Application,
    District,
    Notification,
    Province,
    RecruitmentCycle,
    User,
)


class ApplicantAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.applicant = User.objects.create_user(
            username="api-applicant",
            password="test-password",
            role=User.Roles.APPLICANT,
        )
        cls.other_applicant = User.objects.create_user(
            username="other-api-applicant",
            password="test-password",
            role=User.Roles.APPLICANT,
        )
        cls.staff_user = User.objects.create_user(
            username="api-staff",
            password="test-password",
            role=User.Roles.OFFICER,
        )
        cls.profile = cls.applicant.profile
        cls.profile.full_name = "API Applicant"
        cls.profile.save(update_fields=["full_name"])
        cls.other_profile = cls.other_applicant.profile

        cls.province = Province.objects.create(
            name="Central API",
            code="CAP",
            region=Province.Region.SOUTHERN,
        )
        cls.other_province = Province.objects.create(
            name="Highlands API",
            code="HAP",
            region=Province.Region.HIGHLANDS,
        )
        cls.district = District.objects.create(
            province=cls.province,
            name="Rigo API",
        )
        cls.other_district = District.objects.create(
            province=cls.other_province,
            name="Goroka API",
        )
        cls.active_cycle = RecruitmentCycle.objects.create(
            name="Active API Cycle",
            intake_year=2026,
            rec_type=RecruitmentCycle.RecType.REGULAR,
            start_date="2026-01-01",
            end_date="2026-12-31",
            is_active=True,
        )
        cls.inactive_cycle = RecruitmentCycle.objects.create(
            name="Inactive API Cycle",
            intake_year=2025,
            rec_type=RecruitmentCycle.RecType.REGULAR,
            start_date="2025-01-01",
            end_date="2025-12-31",
            is_active=False,
        )
        cls.application = Application.objects.create(
            applicant=cls.profile,
            cycle=cls.active_cycle,
            applied_unit="Central",
        )
        cls.other_application = Application.objects.create(
            applicant=cls.other_profile,
            cycle=cls.active_cycle,
            applied_unit="Highlands",
        )
        cls.notification = Notification.objects.create(
            user=cls.applicant,
            title="Application received",
            body="Your application was received.",
        )
        cls.other_notification = Notification.objects.create(
            user=cls.other_applicant,
            title="Private notification",
        )

    def setUp(self):
        self.client = APIClient()

    def authenticate_as(self, user):
        self.client.force_login(user)

    def test_api_requires_authentication(self):
        response = self.client.get(reverse("api:profile"))

        self.assertEqual(response.status_code, 403)

    def test_staff_accounts_cannot_use_applicant_api(self):
        self.authenticate_as(self.staff_user)

        response = self.client.get(reverse("api:profile"))

        self.assertEqual(response.status_code, 403)

    def test_applicant_can_read_and_update_only_editable_profile_fields(self):
        self.authenticate_as(self.applicant)

        response = self.client.get(reverse("api:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["full_name"], "API Applicant")
        self.assertNotIn("user", response.json())

        response = self.client.patch(
            reverse("api:profile"),
            {"phone": "70001234", "role": User.Roles.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.applicant.refresh_from_db()
        self.assertEqual(self.profile.phone, "70001234")
        self.assertEqual(self.applicant.role, User.Roles.APPLICANT)

    def test_profile_update_rejects_district_outside_selected_province(self):
        self.authenticate_as(self.applicant)

        response = self.client.patch(
            reverse("api:profile"),
            {
                "province": self.province.pk,
                "district": self.other_district.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("district", response.json())

    def test_session_authenticated_api_writes_require_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.applicant)

        response = client.patch(
            reverse("api:profile"),
            {"phone": "70001234"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_applicant_can_only_list_and_retrieve_their_own_applications(self):
        self.authenticate_as(self.applicant)

        response = self.client.get(reverse("api:applications"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [self.application.pk])
        self.assertNotIn("total_score", response.json()[0])

        own_response = self.client.get(
            reverse("api:application-detail", args=[self.application.pk])
        )
        other_response = self.client.get(
            reverse("api:application-detail", args=[self.other_application.pk])
        )

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 404)

    def test_applications_are_read_only_in_the_api(self):
        self.authenticate_as(self.applicant)

        response = self.client.post(
            reverse("api:applications"),
            {"applied_unit": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, 405)

    def test_only_active_recruitment_cycles_are_returned(self):
        self.authenticate_as(self.applicant)

        response = self.client.get(reverse("api:cycles"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()],
            [self.active_cycle.pk],
        )

    def test_notifications_are_scoped_to_the_signed_in_applicant(self):
        self.authenticate_as(self.applicant)

        response = self.client.get(reverse("api:notifications"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()],
            [self.notification.pk],
        )
        other_response = self.client.get(
            reverse("api:notification-detail", args=[self.other_notification.pk])
        )
        self.assertEqual(other_response.status_code, 404)

    def test_applicant_can_mark_own_notification_read(self):
        self.authenticate_as(self.applicant)

        response = self.client.patch(
            reverse("api:notification-detail", args=[self.notification.pk]),
            {"is_read": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_read_all_marks_only_current_applicants_notifications(self):
        self.authenticate_as(self.applicant)

        response = self.client.post(reverse("api:notifications-read-all"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"updated": 1})
        self.notification.refresh_from_db()
        self.other_notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertFalse(self.other_notification.is_read)