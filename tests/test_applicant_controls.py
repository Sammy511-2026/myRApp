import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from recruitment.models import (
    ApplicantProfile,
    Application,
    RecruitmentCycle,
    ScreeningAction,
    User,
)


class ApplicantSelfServiceTests(TestCase):
    document_types = (
        "G12_CERT", "BIRTH_CERT", "NID_PASSPORT", "MED_CLEAR", "POL_CLEAR", "CHAR_REF",
    )

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.user = User.objects.create_user(
            username="applicant", password="test-password", role=User.Roles.APPLICANT
        )
        self.profile = self.user.profile
        self.profile.full_name = "Applicant One"
        self.profile.save(update_fields=["full_name"])
        self.cycle = RecruitmentCycle.objects.create(
            name="Regular Recruit",
            intake_year=2026,
            start_date="2026-01-01",
            end_date="2026-12-31",
            is_active=True,
        )
        self.client.force_login(self.user)

    def application_form_data(self, intent):
        data = {
            "full_name": self.profile.full_name,
            "dob": "2000-01-01",
            "gender": ApplicantProfile.Gender.OTHER,
            "province": "",
            "district": "",
            "province_of_origin": "",
            "highest_education_level": ApplicantProfile.EducationLevel.G12,
            "edu-TOTAL_FORMS": "1",
            "edu-INITIAL_FORMS": "0",
            "edu-MIN_NUM_FORMS": "0",
            "edu-MAX_NUM_FORMS": "1000",
            "work-TOTAL_FORMS": "1",
            "work-INITIAL_FORMS": "0",
            "work-MIN_NUM_FORMS": "0",
            "work-MAX_NUM_FORMS": "1000",
            "ref-TOTAL_FORMS": "1",
            "ref-INITIAL_FORMS": "0",
            "ref-MIN_NUM_FORMS": "0",
            "ref-MAX_NUM_FORMS": "1000",
            "intent": intent,
        }
        for index, doc_type in enumerate(self.document_types):
            data[f"doc_{index}-doc_type"] = doc_type
        return data

    def test_applicant_can_update_profile_and_upload_picture(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="navy").save(image_buffer, format="PNG")
        photo = SimpleUploadedFile("profile.png", image_buffer.getvalue(), content_type="image/png")

        response = self.client.post(
            reverse("recruitment:profile_edit"),
            {
                "full_name": "Updated Applicant",
                "dob": "2000-01-01",
                "gender": ApplicantProfile.Gender.OTHER,
                "phone": "70000000",
                "email": "updated@example.com",
                "province": "",
                "district": "",
                "province_of_origin": "",
                "nid_number": "",
                "highest_education_level": ApplicantProfile.EducationLevel.G12,
                "photo": photo,
            },
        )

        self.assertRedirects(response, reverse("recruitment:applicant_dashboard"))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, "Updated Applicant")
        self.assertEqual(self.profile.phone, "70000000")
        self.assertTrue(self.profile.photo.name)

    def test_duplicate_nid_is_reported_on_profile_and_case_insensitive(self):
        other_user = User.objects.create_user(
            username="nid-owner", password="test-password", role=User.Roles.APPLICANT
        )
        other_profile = other_user.profile
        other_profile.nid_number = "PG-12345"
        other_profile.save(update_fields=["nid_number"])

        response = self.client.post(
            reverse("recruitment:profile_edit"),
            {
                "full_name": "Applicant One",
                "dob": "2000-01-01",
                "gender": ApplicantProfile.Gender.OTHER,
                "phone": "",
                "email": "",
                "province": "",
                "district": "",
                "province_of_origin": "",
                "nid_number": " pg-12345 ",
                "highest_education_level": ApplicantProfile.EducationLevel.G12,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already associated with another applicant")
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.nid_number)

    def test_applicant_can_keep_their_own_nid(self):
        self.profile.nid_number = "PG-54321"
        self.profile.save(update_fields=["nid_number"])

        response = self.client.post(
            reverse("recruitment:profile_edit"),
            {
                "full_name": "Applicant One",
                "dob": "2000-01-01",
                "gender": ApplicantProfile.Gender.OTHER,
                "phone": "",
                "email": "",
                "province": "",
                "district": "",
                "province_of_origin": "",
                "nid_number": "pg-54321",
                "highest_education_level": ApplicantProfile.EducationLevel.G12,
            },
        )

        self.assertRedirects(response, reverse("recruitment:applicant_dashboard"))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nid_number, "pg-54321")

    def test_application_status_only_shows_admin_status_and_staff_actions(self):
        self.profile.email = "applicant@example.com"
        self.profile.phone = "70001234"
        self.profile.nid_number = "PG-99887"
        self.profile.save()
        application = Application.objects.create(
            applicant=self.profile,
            cycle=self.cycle,
            status=Application.Status.SCREENING,
            applied_unit="Highlands",
            reason_for_applying="I want to serve my community.",
            submitted_at="2026-10-22T00:00:00Z",
        )
        staff_user = User.objects.create_user(
            username="recruitment-officer",
            password="test-password",
            role=User.Roles.OFFICER,
        )
        ScreeningAction.objects.create(
            application=application,
            by_user=staff_user,
            reason="Status changed from Pending to Screening. Documents are under review.",
        )

        response = self.client.get(reverse("recruitment:application_status"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "/static/recruitment/css/application_status.css?v=20261022-0225",
        )
        for displayed_value in (
            "Screening",
            "Status changed from Pending to Screening",
            "Documents are under review.",
            "recruitment-officer",
        ):
            with self.subTest(displayed_value=displayed_value):
                self.assertContains(response, displayed_value)
        for private_applicant_data in (
            "applicant@example.com",
            "70001234",
            "PG-99887",
            "I want to serve my community.",
        ):
            with self.subTest(private_applicant_data=private_applicant_data):
                self.assertNotContains(response, private_applicant_data)
        self.assertEqual(response.context["app"], application)

    def test_application_status_shows_waiting_message_without_admin_action(self):
        Application.objects.create(
            applicant=self.profile,
            cycle=self.cycle,
            status=Application.Status.PENDING,
            submitted_at="2026-10-22T00:00:00Z",
        )

        response = self.client.get(reverse("recruitment:application_status"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Awaiting staff review")
        self.assertContains(response, "awaiting its first update from recruitment staff")

    def test_application_status_ignores_actions_not_recorded_by_staff(self):
        application = Application.objects.create(
            applicant=self.profile,
            cycle=self.cycle,
            status=Application.Status.PENDING,
            submitted_at="2026-10-22T00:00:00Z",
        )
        ScreeningAction.objects.create(
            application=application,
            by_user=self.user,
            reason="Applicant-originated entry must not appear.",
        )

        response = self.client.get(reverse("recruitment:application_status"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Awaiting staff review")
        self.assertNotContains(response, "Applicant-originated entry must not appear.")

    def test_applicant_can_save_and_delete_their_own_draft(self):
        response = self.client.post(
            reverse("recruitment:application_form"), self.application_form_data("save")
        )

        if response.status_code != 302:
            errors = {
                key: str(response.context[key].errors)
                for key in ("profile_form", "application_form", "education_formset", "work_formset", "reference_formset")
            }
            errors["documents"] = [str(row["form"].errors) for row in response.context["document_rows"]]
            self.fail(f"Draft save did not redirect: {errors}")
        self.assertRedirects(response, reverse("recruitment:application_form"))
        application = Application.objects.get(applicant=self.profile, cycle=self.cycle)
        self.assertIsNone(application.submitted_at)

        response = self.client.post(
            reverse("recruitment:application_delete", args=[application.pk])
        )
        self.assertRedirects(response, reverse("recruitment:applicant_dashboard"))
        self.assertFalse(Application.objects.filter(pk=application.pk).exists())

    def test_applicant_can_submit_application_with_required_documents(self):
        data = self.application_form_data("submit")
        data.update({
            f"doc_{index}-file": SimpleUploadedFile(
                f"document-{index}.pdf", b"Applicant supporting document", content_type="application/pdf"
            )
            for index in range(len(self.document_types))
        })
        data["declaration_agreed"] = "on"

        response = self.client.post(reverse("recruitment:application_form"), data)

        if response.status_code != 302:
            errors = {
                key: str(response.context[key].errors)
                for key in ("profile_form", "application_form", "education_formset", "work_formset", "reference_formset")
            }
            errors["documents"] = [str(row["form"].errors) for row in response.context["document_rows"]]
            self.fail(f"Application submit did not redirect: {errors}")
        self.assertRedirects(response, reverse("recruitment:application_status"), fetch_redirect_response=False)
        application = Application.objects.get(applicant=self.profile, cycle=self.cycle)
        self.assertIsNotNone(application.submitted_at)
    def test_applicant_cannot_delete_another_users_application(self):
        another_user = User.objects.create_user(
            username="another-applicant", password="test-password"
        )
        another_profile = another_user.profile
        another_profile.full_name = "Another Applicant"
        another_profile.save(update_fields=["full_name"])
        application = Application.objects.create(applicant=another_profile, cycle=self.cycle)

        response = self.client.post(
            reverse("recruitment:application_delete", args=[application.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Application.objects.filter(pk=application.pk).exists())

    def test_submitted_application_cannot_be_deleted_or_edited(self):
        application = Application.objects.create(
            applicant=self.profile,
            cycle=self.cycle,
            submitted_at="2026-10-22T00:00:00Z",
        )

        response = self.client.post(
            reverse("recruitment:application_delete", args=[application.pk])
        )
        self.assertRedirects(response, reverse("recruitment:application_status"))
        self.assertTrue(Application.objects.filter(pk=application.pk).exists())

        response = self.client.get(reverse("recruitment:application_form"))
        self.assertRedirects(response, reverse("recruitment:application_status"))

    def test_application_form_renders_alternate_contact_controls_and_current_script(self):
        response = self.client.get(reverse("recruitment:application_form"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="alt-TOTAL_FORMS"')
        self.assertContains(response, 'data-add-formset="alt"')
        self.assertContains(response, 'class="formset-remove"')
        self.assertContains(
            response,
            "recruitment/js/application_formsets.js?v=2",
            html=False,
        )
