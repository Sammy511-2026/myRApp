import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from recruitment.models import Document, User


class ProtectedMediaTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.applicant = User.objects.create_user(
            username="media-applicant",
            password="test-password",
            role=User.Roles.APPLICANT,
        )
        self.other_applicant = User.objects.create_user(
            username="other-media-applicant",
            password="test-password",
            role=User.Roles.APPLICANT,
        )
        self.staff = User.objects.create_user(
            username="media-officer",
            password="test-password",
            role=User.Roles.OFFICER,
        )
        self.document = Document.objects.create(
            applicant=self.applicant.profile,
            doc_type=Document.DocType.BIRTH_CERT,
            file=SimpleUploadedFile(
                "birth-certificate.pdf",
                b"test document",
                content_type="application/pdf",
            ),
        )

    def media_url(self, file_field):
        return f"/media/{file_field.name}"

    def test_anonymous_users_are_redirected_to_login(self):
        response = self.client.get(self.media_url(self.document.file))

        self.assertRedirects(
            response,
            f"{reverse('recruitment:login')}?next={self.media_url(self.document.file)}",
        )

    def test_applicant_can_download_their_own_document(self):
        self.client.force_login(self.applicant)

        response = self.client.get(self.media_url(self.document.file))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(b"".join(response.streaming_content), b"test document")

    def test_applicant_cannot_download_another_applicants_document(self):
        self.client.force_login(self.other_applicant)

        response = self.client.get(self.media_url(self.document.file))

        self.assertEqual(response.status_code, 404)

    def test_recruitment_staff_can_download_applicant_documents(self):
        self.client.force_login(self.staff)

        response = self.client.get(self.media_url(self.document.file))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"test document")

    def test_applicant_can_view_their_own_profile_photo(self):
        self.applicant.profile.photo.save(
            "portrait.png",
            SimpleUploadedFile(
                "portrait.png",
                b"test image",
                content_type="image/png",
            ),
        )
        self.client.force_login(self.applicant)

        response = self.client.get(self.media_url(self.applicant.profile.photo))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertNotIn("attachment", response["Content-Disposition"])

    def test_invalid_media_paths_are_not_served(self):
        self.client.force_login(self.staff)

        response = self.client.get("/media/../../.env")

        self.assertEqual(response.status_code, 404)
