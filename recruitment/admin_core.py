from __future__ import annotations
import csv
from django.contrib import admin, messages
from django.http import HttpResponse
from .admin_site import rpngc_admin_site
from .models import (
    Province, District, User, ApplicantProfile, Document,
    RecruitmentCycle, Application, ApplicationEligibility, ScreeningAction,
    Test, Question, Choice, TestAttempt, AttemptAnswer,
    InterviewSchedule, InterviewScore, FinalSelection,
    Notification, AuditLog,
)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def export_as_csv(modeladmin, request, queryset, *, filename: str, fields: list[str], header: list[str] | None = None):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    w = csv.writer(response)
    w.writerow(header or fields)
    for obj in queryset:
        row = []
        for f in fields:
            val = obj
            for attr in f.split("__"):
                val = getattr(val, attr, "")
                if callable(val):
                    val = val()
            row.append(val)
        w.writerow(row)
    return response

# -------------------------------------------------------------------
# Geography
# -------------------------------------------------------------------
@admin.register(Province, site=rpngc_admin_site)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")

@admin.register(District, site=rpngc_admin_site)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "province")
    list_filter = ("province",)
    search_fields = ("name", "province__name")
    autocomplete_fields = ("province",)

# -------------------------------------------------------------------
# Users
# -------------------------------------------------------------------
class ApplicantProfileInline(admin.StackedInline):
    model = ApplicantProfile
    fk_name = "user"
    extra = 0
    can_delete = False
    show_change_link = False
    readonly_fields = ("full_name", "dob", "gender", "nid_number", "photo",
                       "address", "province", "district", "phone", "email",
                       "province_of_origin", "highest_education_level")

@admin.register(User, site=rpngc_admin_site)
class UserAdmin(admin.ModelAdmin):
    inlines = [ApplicantProfileInline]
    list_display = ("username", "role", "is_active", "is_staff", "is_superuser", "last_login", "last_ip")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email")

# -------------------------------------------------------------------
# Documents
# -------------------------------------------------------------------
@admin.register(Document, site=rpngc_admin_site)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("applicant", "doc_type", "verify_status", "verified_by", "uploaded_at")
    list_filter = ("doc_type", "verify_status")
    search_fields = ("applicant__full_name", "applicant__user__username")
    autocomplete_fields = ("applicant", "verified_by")
    actions = ["mark_approved", "mark_rejected"]

    @admin.action(description="Mark selected Approved")
    def mark_approved(self, request, queryset):
        queryset.update(verify_status=Document.VerifyStatus.APPROVED)
        self.message_user(request, "Documents marked Approved.", messages.SUCCESS)

    @admin.action(description="Mark selected Rejected")
    def mark_rejected(self, request, queryset):
        queryset.update(verify_status=Document.VerifyStatus.REJECTED)
        self.message_user(request, "Documents marked Rejected.", messages.WARNING)

# -------------------------------------------------------------------
# Recruitment & Applications
# -------------------------------------------------------------------
@admin.register(RecruitmentCycle, site=rpngc_admin_site)
class RecruitmentCycleAdmin(admin.ModelAdmin):
    list_display = ("name", "intake_year", "rec_type", "is_active", "start_date", "end_date", "min_age", "max_age")
    list_filter = ("rec_type", "is_active")
    search_fields = ("name",)
    autocomplete_fields = ("created_by",)

@admin.register(Application, site=rpngc_admin_site)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "applicant", "cycle", "status", "total_score", "submitted_at")
    list_filter = ("status", "cycle")
    search_fields = ("applicant__full_name", "cycle__name")
    autocomplete_fields = ("applicant", "cycle")
    actions = ["export_basic_csv"]

    @admin.action(description="Export CSV")
    def export_basic_csv(self, request, queryset):
        fields = ["id", "applicant__full_name", "cycle__name", "status", "total_score"]
        header = ["ID", "Applicant", "Cycle", "Status", "Score"]
        return export_as_csv(self, request, queryset, filename="applications.csv", fields=fields, header=header)

@admin.register(ApplicationEligibility, site=rpngc_admin_site)
class ApplicationEligibilityAdmin(admin.ModelAdmin):
    list_display = ("application", "result", "age_ok", "education_ok", "medical_ok", "police_ok", "run_at")
    list_filter = ("result",)

@admin.register(ScreeningAction, site=rpngc_admin_site)
class ScreeningActionAdmin(admin.ModelAdmin):
    list_display = ("application", "auto_score", "manual_adjustment", "by_user", "created_at")
    list_filter = ("created_at",)
    autocomplete_fields = ("application", "by_user")

# -------------------------------------------------------------------
# Tests & MCQ
# -------------------------------------------------------------------
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0

@admin.register(Test, site=rpngc_admin_site)
class TestAdmin(admin.ModelAdmin):
    list_display = ("name", "cycle", "opens_at", "closes_at", "is_published")
    list_filter = ("is_published",)
    inlines = [QuestionInline]
    autocomplete_fields = ("cycle",)

@admin.register(Question, site=rpngc_admin_site)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("test", "order", "text", "points")
    search_fields = ("text",)
    autocomplete_fields = ("test",)

@admin.register(Choice, site=rpngc_admin_site)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "text", "is_correct")
    list_filter = ("is_correct",)
    autocomplete_fields = ("question",)

@admin.register(TestAttempt, site=rpngc_admin_site)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ("test", "application", "status", "score")
    list_filter = ("status",)
    autocomplete_fields = ("test", "application")

@admin.register(AttemptAnswer, site=rpngc_admin_site)
class AttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "selected_choice", "is_correct", "awarded_points")
    list_filter = ("is_correct",)
    autocomplete_fields = ("attempt", "question")

# -------------------------------------------------------------------
# Interviews & Final
# -------------------------------------------------------------------
class InterviewScoreInline(admin.TabularInline):
    model = InterviewScore
    extra = 0

@admin.register(InterviewSchedule, site=rpngc_admin_site)
class InterviewScheduleAdmin(admin.ModelAdmin):
    list_display = ("application", "scheduled_at", "location", "status")
    list_filter = ("status",)
    inlines = [InterviewScoreInline]
    autocomplete_fields = ("application", "created_by")

@admin.register(InterviewScore, site=rpngc_admin_site)
class InterviewScoreAdmin(admin.ModelAdmin):
    list_display = ("schedule", "interviewer", "score")
    autocomplete_fields = ("schedule", "interviewer")

@admin.register(FinalSelection, site=rpngc_admin_site)
class FinalSelectionAdmin(admin.ModelAdmin):
    list_display = ("application", "rank", "total_score_snapshot", "approved_by", "is_published")
    list_filter = ("is_published",)
    autocomplete_fields = ("application", "approved_by")

# -------------------------------------------------------------------
# Notifications & Audit
# -------------------------------------------------------------------
@admin.register(Notification, site=rpngc_admin_site)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "ntype", "title", "is_read", "created_at")
    list_filter = ("ntype", "is_read")
    autocomplete_fields = ("user",)

@admin.register(AuditLog, site=rpngc_admin_site)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "entity", "entity_id", "created_at")
    list_filter = ("action",)
    autocomplete_fields = ("actor",)
