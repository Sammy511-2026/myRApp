from django.test import TestCase
from django.urls import reverse

from recruitment.forms import (
    ApplicantApplicationProfileForm,
    ApplicantProfileForm,
    ApplicantRegistrationForm,
)
from recruitment.models import District, Province, User


class ApplicantLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.southern_province = Province.objects.create(
            name="Central",
            code="CEN",
            region=Province.Region.SOUTHERN,
        )
        cls.highlands_province = Province.objects.create(
            name="Eastern Highlands",
            code="EHP",
            region=Province.Region.HIGHLANDS,
        )
        cls.southern_district = District.objects.create(
            province=cls.southern_province,
            name="Rigo",
        )
        cls.highlands_district = District.objects.create(
            province=cls.highlands_province,
            name="Goroka",
        )

    def test_province_dropdown_groups_options_by_region(self):
        form = ApplicantRegistrationForm()
        groups = [
            label
            for label, options in form.fields["province"].choices
            if isinstance(options, (list, tuple))
        ]

        self.assertIn("Southern", groups)
        self.assertIn("Highlands", groups)

    def test_registration_page_renders_region_groups_and_dependent_district_script(self):
        response = self.client.get(reverse("recruitment:register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<optgroup label="Southern">')
        self.assertContains(response, '<optgroup label="Highlands">')
        self.assertContains(response, "recruitment/js/location_selects.js")
        self.assertNotContains(response, 'name="photo"')

    def test_profile_photo_is_only_editable_from_profile_form(self):
        self.assertIn("photo", ApplicantProfileForm().fields)
        self.assertNotIn("photo", ApplicantApplicationProfileForm().fields)
        self.assertNotIn("photo", ApplicantRegistrationForm().fields)

    def test_district_endpoint_returns_districts_for_selected_province(self):
        response = self.client.get(
            reverse("recruitment:district_choices"),
            {"province_id": self.southern_province.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["province"], "Central")
        self.assertEqual(
            response.json()["districts"],
            [{"id": self.southern_district.pk, "name": "Rigo"}],
        )

    def test_png_province_and_district_reference_data_is_seeded(self):
        self.assertEqual(Province.objects.filter(code__startswith="PG").count(), 22)
        self.assertEqual(
            District.objects.filter(province__code__startswith="PG").count(),
            87,
        )

    def test_profile_form_rejects_district_from_a_different_province(self):
        user = User.objects.create_user(
            username="location-applicant",
            password="test-password",
        )
        form = ApplicantProfileForm(
            data={
                "full_name": "Location Applicant",
                "dob": "2000-01-02",
                "gender": "F",
                "province": str(self.southern_province.pk),
                "district": str(self.highlands_district.pk),
            },
            instance=user.profile,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("district", form.errors)
