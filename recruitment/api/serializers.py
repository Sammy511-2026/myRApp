from django.db.models.functions import Lower
from rest_framework import serializers

from recruitment.models import (
    ApplicantProfile,
    Application,
    Notification,
    RecruitmentCycle,
)


class RecruitmentCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruitmentCycle
        fields = (
            "id",
            "name",
            "intake_year",
            "rec_type",
            "start_date",
            "end_date",
            "is_active",
            "min_age",
            "max_age",
            "min_education_level",
        )
        read_only_fields = fields


class ApplicantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicantProfile
        fields = (
            "full_name",
            "dob",
            "gender",
            "nid_number",
            "address",
            "province",
            "district",
            "phone",
            "email",
            "province_of_origin",
            "highest_education_level",
        )

    def validate_nid_number(self, value):
        value = (value or "").strip()
        if not value:
            return None

        duplicates = ApplicantProfile.objects.annotate(
            normalized_nid=Lower("nid_number")
        ).filter(normalized_nid=value.lower())
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                "This NID / Passport number is already associated with another applicant."
            )
        return value

    def validate(self, attrs):
        province = attrs.get("province", getattr(self.instance, "province", None))
        district = attrs.get("district", getattr(self.instance, "district", None))
        if district and (province is None or district.province_id != province.pk):
            raise serializers.ValidationError(
                {"district": "Select a district in the selected province."}
            )
        return attrs


class ApplicationSerializer(serializers.ModelSerializer):
    cycle = RecruitmentCycleSerializer(read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "cycle",
            "status",
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
            "submitted_at",
            "last_updated",
        )
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "ntype", "title", "body", "is_read", "created_at")
        read_only_fields = ("id", "ntype", "title", "body", "created_at")
