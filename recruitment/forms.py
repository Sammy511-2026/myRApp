from __future__ import annotations

from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db.models.functions import Lower
from django.forms import inlineformset_factory

from .models import (
    User,
    ApplicantProfile,
    AlternativeContact,
    ParentGuardian,
    EducationRecord,
    WorkHistory,
    Reference,
    Application,
    Document,
    Province,
    District,
)


def _group_province_choices(field):
    grouped_choices = {}
    for province in field.queryset.order_by("name"):
        grouped_choices.setdefault(province.region, []).append((str(province.pk), str(province)))
    choices = [("", field.empty_label or "---------")]
    for region, label in Province.Region.choices:
        if region in grouped_choices:
            choices.append((label, grouped_choices[region]))
    if "" in grouped_choices:
        choices.append(("Other / Unassigned", grouped_choices[""]))
    field.choices = choices


class ProvinceChoiceFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("province", "province_of_origin"):
            if field_name in self.fields:
                _group_province_choices(self.fields[field_name])
        if "district" in self.fields:
            self.fields["district"].queryset = District.objects.none()
            province_id = self.data.get(
                self.add_prefix("province"),
                self.initial.get("province") or getattr(self.instance, "province_id", None),
            )
            try:
                province_id = int(province_id) if province_id else None
            except (TypeError, ValueError):
                province_id = None
            if province_id is not None:
                self.fields["district"].queryset = District.objects.filter(province_id=province_id)


class ApplicantNIDValidationMixin:
    def clean_nid_number(self):
        nid_number = (self.cleaned_data.get("nid_number") or "").strip()
        if not nid_number:
            return None

        existing_profiles = ApplicantProfile.objects.annotate(
            normalized_nid=Lower("nid_number")
        ).filter(normalized_nid=nid_number.lower())
        if self.instance.pk:
            existing_profiles = existing_profiles.exclude(pk=self.instance.pk)
        if existing_profiles.exists():
            raise forms.ValidationError(
                "This NID / Passport number is already associated with another applicant."
            )
        return nid_number


# ------------------------------------------------------------
# Registration form (user + profile fields in one)
# ------------------------------------------------------------
class ApplicantRegistrationForm(ProvinceChoiceFormMixin, ApplicantNIDValidationMixin, UserCreationForm):
    # Core user bits
    username = forms.CharField(label="Username", max_length=150)

    # ApplicantProfile fields we want at registration time
    full_name = forms.CharField(label="Full name", max_length=150)
    dob = forms.DateField(label="Date of birth", widget=forms.DateInput(attrs={"type": "date"}))
    gender = forms.ChoiceField(label="Sex", choices=ApplicantProfile.Gender.choices)
    phone = forms.CharField(label="Mobile number", max_length=30, required=False)
    email = forms.EmailField(label="Email address", required=False)
    province = forms.ModelChoiceField(
        label="Province (residence)", queryset=Province.objects.all(), required=False
    )
    district = forms.ModelChoiceField(
        label="District (residence)", queryset=District.objects.none(), required=False
    )
    province_of_origin = forms.ModelChoiceField(
        label="Province of origin", queryset=Province.objects.all(), required=False
    )
    nid_number = forms.CharField(label="NID / Passport No.", max_length=30, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def save(self, commit=True) -> User:
        user = super().save(commit=False)
        user.role = User.Roles.APPLICANT
        if commit:
            user.save()

        # Create / update ApplicantProfile with provided details
        ApplicantProfile.objects.update_or_create(
            user=user,
            defaults=dict(
                full_name=self.cleaned_data.get("full_name"),
                dob=self.cleaned_data.get("dob") or date(2000, 1, 1),
                gender=self.cleaned_data.get("gender"),
                phone=self.cleaned_data.get("phone", ""),
                email=self.cleaned_data.get("email", ""),
                province=self.cleaned_data.get("province"),
                district=self.cleaned_data.get("district"),
                province_of_origin=self.cleaned_data.get("province_of_origin"),
                nid_number=self.cleaned_data.get("nid_number") or None,
            ),
        )
        return user


# ------------------------------------------------------------
# Core model forms
# ------------------------------------------------------------
class ApplicantProfileForm(ProvinceChoiceFormMixin, ApplicantNIDValidationMixin, forms.ModelForm):
    class Meta:
        model = ApplicantProfile
        fields = [
            "full_name",
            "dob",
            "gender",
            "province_of_origin",
            "province",
            "district",
            "phone",
            "email",
            "nid_number",
            "photo",
            "highest_education_level",
        ]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
        }


class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "profile_photo"]
        labels = {
            "first_name": "First name",
            "last_name": "Last name",
            "email": "Email address",
            "profile_photo": "Profile picture",
        }


class ApplicantApplicationProfileForm(ApplicantProfileForm):
        class Meta(ApplicantProfileForm.Meta):
            fields = [
                "full_name",
                "dob",
                "gender",
                "province_of_origin",
                "province",
                "district",
                "phone",
                "email",
                "nid_number",
                "highest_education_level",
            ]


class EducationRecordForm(ProvinceChoiceFormMixin, forms.ModelForm):
    province = forms.ModelChoiceField(queryset=Province.objects.all(), required=False)

    class Meta:
        model = EducationRecord
        fields = [
            "level",
            "institution",
            "province",
            "start_date",
            "end_date",
            "gpa",
            "english_grade",
            "mathematics_grade",
            "science_grade",
            "other_grade",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            "applied_unit",
            "from_bougainville",
            "years_experience",
            "years_experience_other",
            "reservist_2021_2022",
            "reason_for_applying",
            "criminal_conviction",
            "declaration_agreed",
            "signature_name",
            "signature_date",
        ]
        widgets = {
            "signature_date": forms.DateInput(attrs={"type": "date"}),
            "reason_for_applying": forms.Textarea(attrs={"rows": 4}),
        }


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["doc_type", "file"]


# ------------------------------------------------------------
# Inline formsets for composite Application form
# ------------------------------------------------------------
AlternativeContactFormSet = inlineformset_factory(
    ApplicantProfile,
    AlternativeContact,
    fields=["name", "relationship", "phone", "address"],
    extra=1,
    can_delete=True,
    max_num=20,
)

ParentGuardianFormSet = inlineformset_factory(
    ApplicantProfile,
    ParentGuardian,
    fields=["kind", "name", "phone", "address", "is_alive"],
    extra=1,
    can_delete=True,
)

EducationRecordFormSet = inlineformset_factory(
    ApplicantProfile,
    EducationRecord,
    form=EducationRecordForm,
    fields=[
        "level",
        "institution",
        "province",
        "start_date",
        "end_date",
        "gpa",
        "english_grade",
        "mathematics_grade",
        "science_grade",
        "other_grade",
    ],
    extra=1,
    can_delete=True,
)

# NOTE: Your views import WorkFormSet. Define it here (alias for WorkHistory formset).
WorkFormSet = inlineformset_factory(
    ApplicantProfile,
    WorkHistory,
    fields=["employer", "position", "start_date", "end_date", "duties"],
    widgets={
        "start_date": forms.DateInput(attrs={"type": "date"}),
        "end_date": forms.DateInput(attrs={"type": "date"}),
        "duties": forms.Textarea(attrs={"rows": 2}),
    },
    extra=1,
    can_delete=True,
)

ReferenceFormSet = inlineformset_factory(
    ApplicantProfile,
    Reference,
    fields=["name", "position_title", "phone_number", "email"],
    extra=1,
    can_delete=True,
)
REQUIRED_DOC_TYPES = (
    Document.DocType.G12_CERT,
    Document.DocType.BIRTH_CERT,
    Document.DocType.NID_PASSPORT,
    Document.DocType.MED_CLEAR,
    Document.DocType.POL_CLEAR,
    Document.DocType.CHAR_REF,
    # Document.DocType.TERTIARY,  # <- include if you want it required
)

class DocumentUploadForm(forms.ModelForm):
    """
    Per-type upload form used inside the application page.
    Doc type is fixed per row (hidden field), file is optional on save-draft,
    but must be present at final submit (enforced in the view).
    """
    class Meta:
        model = Document
        fields = ["doc_type", "file"]
        widgets = {"doc_type": forms.HiddenInput()}

    def __init__(self, *args, file_required=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].required = file_required
