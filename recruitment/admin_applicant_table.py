from django.contrib import admin
from django.db.models import Prefetch

from .models import ApplicantProfile, Application


class ApplicantTableMixin:
    list_display = (
        "full_name",
        "nid_number",
        "dob",
        "gender",
        "email",
        "phone",
        "region",
        "province",
        "district",
        "province_of_origin",
        "highest_education_level",
        "application_cycle",
        "application_status",
        "application_submitted_at",
    )
    list_filter = (
        "gender",
        "province__region",
        "province",
        "district",
        "province_of_origin",
        "highest_education_level",
    )
    search_fields = ("full_name", "user__username", "email", "phone", "nid_number")
    list_per_page = 50

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related(
            "user",
            "province",
            "district",
            "province_of_origin",
        ).prefetch_related(
            Prefetch(
                "applications",
                queryset=Application.objects.select_related("cycle").order_by("-submitted_at", "-pk"),
                to_attr="_admin_applications",
            )
        )

    @staticmethod
    def _latest_application(obj: ApplicantProfile) -> Application | None:
        applications = getattr(obj, "_admin_applications", ())
        return applications[0] if applications else None

    @admin.display(description="Latest intake")
    def application_cycle(self, obj: ApplicantProfile):
        application = self._latest_application(obj)
        return application.cycle if application else "—"

    @admin.display(description="Application status")
    def application_status(self, obj: ApplicantProfile):
        application = self._latest_application(obj)
        return application.get_status_display() if application else "—"

    @admin.display(description="Submitted")
    def application_submitted_at(self, obj: ApplicantProfile):
        application = self._latest_application(obj)
        return application.submitted_at if application else None

    @admin.display(description="Region", ordering="province__region")
    def region(self, obj: ApplicantProfile):
        if not obj.province_id or not obj.province.region:
            return "—"
        return obj.province.get_region_display()
