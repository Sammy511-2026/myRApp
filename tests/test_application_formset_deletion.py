from datetime import date

from django.test import TestCase

from recruitment.forms import (
    AlternativeContactFormSet,
    EducationRecordFormSet,
    ReferenceFormSet,
    WorkFormSet,
)
from recruitment.models import (
    ApplicantProfile,
    AlternativeContact,
    EducationRecord,
    Reference,
    User,
    WorkHistory,
)


class ApplicantFormsetDeletionTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="formset-applicant", password="test-password")
        self.profile = user.profile
        self.profile.full_name = "Formset Applicant"
        self.profile.dob = date(2000, 1, 1)
        self.profile.gender = ApplicantProfile.Gender.OTHER
        self.profile.save()

    def assert_formset_deletes_record(self, formset_class, prefix, record, extra_data=None):
        data = {
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "1",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-id": str(record.pk),
            f"{prefix}-0-DELETE": "on",
        }
        data.update(extra_data or {})
        formset = formset_class(data, instance=self.profile, prefix=prefix)

        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.assertFalse(record.__class__.objects.filter(pk=record.pk).exists())

    def test_education_delete_is_saved(self):
        record = EducationRecord.objects.create(
            applicant=self.profile,
            level=EducationRecord.Level.G12,
            institution="Example School",
        )
        self.assert_formset_deletes_record(EducationRecordFormSet, "edu", record)

    def test_education_start_and_end_dates_are_saved_as_full_dates(self):
        formset = EducationRecordFormSet(
            {
                "edu-TOTAL_FORMS": "1",
                "edu-INITIAL_FORMS": "0",
                "edu-MIN_NUM_FORMS": "0",
                "edu-MAX_NUM_FORMS": "1000",
                "edu-0-level": EducationRecord.Level.G12,
                "edu-0-start_date": "2018-02-15",
                "edu-0-end_date": "2020-11-30",
            },
            instance=self.profile,
            prefix="edu",
        )

        self.assertEqual(formset.forms[0].fields["start_date"].widget.input_type, "date")
        self.assertEqual(formset.forms[0].fields["end_date"].widget.input_type, "date")
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()

        record = self.profile.education.get()
        self.assertEqual(record.start_date.isoformat(), "2018-02-15")
        self.assertEqual(record.end_date.isoformat(), "2020-11-30")

    def test_work_history_delete_is_saved(self):
        record = WorkHistory.objects.create(
            applicant=self.profile,
            employer="Example Employer",
        )
        self.assert_formset_deletes_record(WorkFormSet, "work", record)

    def test_reference_delete_is_saved(self):
        record = Reference.objects.create(
            applicant=self.profile,
            name="Example Referee",
        )
        self.assert_formset_deletes_record(ReferenceFormSet, "ref", record)

    def test_multiple_alternative_contacts_can_be_added(self):
        data = {
            "alt-TOTAL_FORMS": "2",
            "alt-INITIAL_FORMS": "0",
            "alt-MIN_NUM_FORMS": "0",
            "alt-MAX_NUM_FORMS": "20",
            "alt-0-name": "First Contact",
            "alt-0-relationship": "Sibling",
            "alt-1-name": "Second Contact",
            "alt-1-relationship": "Parent",
        }
        formset = AlternativeContactFormSet(data, instance=self.profile, prefix="alt")

        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.assertEqual(self.profile.alt_contacts.count(), 2)

    def test_alternative_contact_delete_is_saved(self):
        record = AlternativeContact.objects.create(
            applicant=self.profile,
            name="Example Contact",
        )
        self.assert_formset_deletes_record(AlternativeContactFormSet, "alt", record)
