# recruitment/admin_site.py
from __future__ import annotations

from django.contrib.admin import AdminSite, ModelAdmin, TabularInline, StackedInline
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from .admin_applicant_table import ApplicantTableMixin
from . import models


# =========================
# Custom Admin Site
# =========================
class RPNGCAdminSite(AdminSite):
    site_header = "RPNGC Recruitment Admin"
    site_title = "RPNGC Admin"
    index_title = "Applications and Admin Settings"

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        models_by_name = {
            model["object_name"]: model
            for app in app_list
            for model in app["models"]
        }

        sections = (
            ("Applications", ("Application",)),
            (
                "Admin settings",
                ("User", "Group", "Province", "District", "RecruitmentCycle", "Test", "Question", "Choice"),
            ),
        )
        grouped = []
        for section_name, object_names in sections:
            section_models = sorted(
                (models_by_name[name] for name in object_names if name in models_by_name),
                key=lambda model: (object_names.index(model["object_name"]), model["name"].lower()),
            )
            if section_models:
                grouped.append({
                    "name": section_name,
                    "app_label": f"rpngc_{section_name.lower().replace(' ', '_')}",
                    "app_url": (
                        section_models[0]["admin_url"]
                        if section_name == "Applications"
                        else reverse(f"{self.name}:index")
                    ),
                    "has_module_perms": True,
                    "models": section_models,
                })
        return grouped

rpngc_admin = RPNGCAdminSite(name="rpngc_admin")
rpngc_admin.index_template = "admin/rpngc_index.html"


# =========================
# Inlines on ApplicantProfile
# =========================
class AlternativeContactInline(StackedInline):
    model = models.AlternativeContact
    extra = 0
    max_num = 1
    can_delete = True
    fk_name = "applicant"
    show_change_link = True


class ParentGuardianInline(TabularInline):
    model = models.ParentGuardian
    extra = 0
    fk_name = "applicant"
    show_change_link = True


class EducationRecordInline(TabularInline):
    model = models.EducationRecord
    extra = 0
    fk_name = "applicant"
    show_change_link = True


class WorkHistoryInline(TabularInline):
    model = models.WorkHistory
    extra = 0
    fk_name = "applicant"
    show_change_link = True


class ReferenceInline(TabularInline):
    model = models.Reference
    extra = 0
    fk_name = "applicant"
    show_change_link = True


class DocumentInline(TabularInline):
    model = models.Document
    extra = 0
    fk_name = "applicant"
    fields = ("doc_type", "file", "verify_status", "verified_by", "uploaded_at")
    readonly_fields = ("uploaded_at",)
    show_change_link = True


class ApplicationInline(TabularInline):
    model = models.Application
    extra = 0
    fk_name = "applicant"
    fields = ("cycle", "status", "eligibility_passed", "total_score", "submitted_at")
    readonly_fields = ("submitted_at", "total_score", "eligibility_passed")
    show_change_link = True


# =========================
# Helper: current application (active cycle preferred)
# =========================
def _current_application_for_profile(prof: models.ApplicantProfile) -> models.Application | None:
    active_cycle = models.RecruitmentCycle.objects.filter(is_active=True).order_by("-start_date").first()
    if active_cycle:
        app = models.Application.objects.filter(applicant=prof, cycle=active_cycle).first()
        if app:
            return app
    return (
        models.Application.objects.filter(applicant=prof)
        .order_by("-submitted_at", "-id")
        .first()
    )


# =========================
# ApplicantProfile Admin — ONE PAGE + actions + printable page
# =========================
@admin.register(models.ApplicantProfile, site=rpngc_admin)
class ApplicantProfileAdmin(ApplicantTableMixin, ModelAdmin):
    change_form_template = "admin/recruitment/applicantprofile/change_form.html"

    inlines = [
        AlternativeContactInline,
        ParentGuardianInline,
        EducationRecordInline,
        WorkHistoryInline,
        ReferenceInline,
        DocumentInline,
        ApplicationInline,
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<path:object_id>/application/<str:action>/",
                self.admin_site.admin_view(self._application_action),
                name="recruitment_applicantprofile_application_action",
            ),
            path(
                "<path:object_id>/print/",
                self.admin_site.admin_view(self._print_view),
                name="recruitment_applicantprofile_print",
            ),
        ]
        return custom + urls

    def render_change_form(self, request, context, *args, **kwargs):
        obj: models.ApplicantProfile | None = context.get("original")
        current_app = None
        eligibility = None
        documents = ()
        screening_actions = ()

        if obj:
            current_app = _current_application_for_profile(obj)
            if current_app:
                eligibility = getattr(current_app, "eligibility", None)
                screening_actions = current_app.screening_actions.select_related("by_user").all()
            documents = models.Document.objects.filter(applicant=obj).select_related(
                "verified_by"
            ).order_by("doc_type", "-uploaded_at")

        context.update(
            current_app=current_app,
            current_elig=eligibility,
            current_app_docs=documents,
            current_app_contacts=obj.alt_contacts.all() if obj else (),
            current_app_parents=obj.parents.all() if obj else (),
            current_app_education=obj.education.select_related("province").all() if obj else (),
            current_app_work=obj.work_history.all() if obj else (),
            current_app_references=obj.references.all() if obj else (),
            current_app_screening_actions=screening_actions,
            can_change_application=request.user.has_perm("recruitment.change_application"),
        )
        return super().render_change_form(request, context, *args, **kwargs)

    @transaction.atomic
    @method_decorator(require_POST)
    def _application_action(self, request, object_id: str, action: str):
        prof = get_object_or_404(models.ApplicantProfile, pk=object_id)
        app = _current_application_for_profile(prof)
        if not app:
            messages.error(request, "No application found for this applicant.")
            return redirect(self._obj_url(prof))

        if not request.user.has_perm("recruitment.change_application"):
            messages.error(request, "You do not have permission to update applications.")
            return redirect(self._obj_url(prof))

        prev = app.status
        if action == "approve":
            app.status = models.Application.Status.ACCEPTED
        elif action == "reject":
            app.status = models.Application.Status.REJECTED
        elif action == "shortlist":
            app.status = models.Application.Status.SHORTLISTED
        else:
            messages.error(request, "Unknown action.")
            return redirect(self._obj_url(prof))

        app.last_updated = timezone.now()
        app.recalc_total(save=False)
        app.save(update_fields=["status", "total_score", "last_updated"])

        models.ScreeningAction.objects.create(
            application=app,
            auto_score=app.auto_screen_score,
            manual_adjustment=app.manual_adjustment,
            reason=f"Status changed via Applicant page: {prev} → {app.status}",
            by_user=request.user,
        )
        models.AuditLog.objects.create(
            actor=request.user,
            action=models.AuditLog.Action.APPROVE if action == "approve"
                   else models.AuditLog.Action.REJECT if action == "reject"
                   else models.AuditLog.Action.SHORTLIST,
            entity="Application",
            entity_id=str(app.pk),
            payload={"from": prev, "to": app.status, "via": "ApplicantProfileAdmin"},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        messages.success(request, f"Application updated: {prev} → {app.status}.")
        return redirect(self._obj_url(prof))

    def _obj_url(self, obj) -> str:
        return reverse("rpngc_admin:recruitment_applicantprofile_change", args=[obj.pk])

    # Printable view (single dossier page)
    def _print_view(self, request, object_id: str):
        from django.template.response import TemplateResponse

        prof = get_object_or_404(models.ApplicantProfile, pk=object_id)
        app = _current_application_for_profile(prof)
        docs = models.Document.objects.filter(applicant=prof).order_by("doc_type", "-uploaded_at")
        edu = models.EducationRecord.objects.filter(applicant=prof).order_by("level", "end_date", "id")
        work = models.WorkHistory.objects.filter(applicant=prof).order_by("-start_date", "-end_date", "id")
        refs = models.Reference.objects.filter(applicant=prof).order_by("id")
        alt_contacts = prof.alt_contacts.all()
        parents = models.ParentGuardian.objects.filter(applicant=prof).order_by("kind")

        elig = getattr(app, "eligibility", None) if app else None

        ctx = dict(
            title=f"{prof.full_name} — Applicant Dossier",
            profile=prof,
            application=app,
            eligibility=elig,
            documents=docs,
            education=edu,
            workhistory=work,
            references=refs,
            alt_contacts=alt_contacts,
            parents=parents,
            admin_site=self.admin_site,
        )
        return TemplateResponse(request, "admin/recruitment/applicantprofile/print.html", ctx)


# =========================
# Application admin — object-tools actions
# =========================
@admin.register(models.Application, site=rpngc_admin)
class ApplicationAdmin(ModelAdmin):
    list_display = (
        "id",
        "applicant",
        "applicant_region",
        "cycle",
        "status",
        "total_score",
        "eligibility_passed",
        "submitted_at",
    )
    list_filter = (
        "applicant__province__region",
        "applicant__province",
        "applicant__district",
        "status",
        "eligibility_passed",
        "cycle__intake_year",
        "cycle__rec_type",
    )
    search_fields = ("applicant__full_name", "applicant__user__username")
    autocomplete_fields = ("applicant", "cycle")
    readonly_fields = ("total_score", "submitted_at", "last_updated")
    change_form_template = "admin/recruitment/application/change_form.html"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "applicant__province",
            "applicant__district",
            "cycle",
        )

    @admin.display(description="Region", ordering="applicant__province__region")
    def applicant_region(self, obj):
        province = obj.applicant.province
        if not province or not province.region:
            return "—"
        return province.get_region_display()

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<path:object_id>/approve/", self.admin_site.admin_view(self.approve), name="recruitment_application_approve"),
            path("<path:object_id>/reject/", self.admin_site.admin_view(self.reject), name="recruitment_application_reject"),
            path("<path:object_id>/shortlist/", self.admin_site.admin_view(self.shortlist), name="recruitment_application_shortlist"),
        ]
        return custom + urls

    def _do_status_change(self, request, object_id: str, to_status: str):
        app = get_object_or_404(models.Application, pk=object_id)
        if not request.user.has_perm("recruitment.change_application"):
            messages.error(request, "You do not have permission to update applications.")
            return redirect(reverse("rpngc_admin:recruitment_application_change", args=[app.pk]))

        prev = app.status
        app.status = to_status
        app.last_updated = timezone.now()
        app.recalc_total(save=False)
        app.save(update_fields=["status", "total_score", "last_updated"])

        models.ScreeningAction.objects.create(
            application=app,
            auto_score=app.auto_screen_score,
            manual_adjustment=app.manual_adjustment,
            reason=f"Status changed via Application page: {prev} → {to_status}",
            by_user=request.user,
        )
        models.AuditLog.objects.create(
            actor=request.user,
            action=models.AuditLog.Action.APPROVE if to_status == models.Application.Status.ACCEPTED
                   else models.AuditLog.Action.REJECT if to_status == models.Application.Status.REJECTED
                   else models.AuditLog.Action.SHORTLIST,
            entity="Application",
            entity_id=str(app.pk),
            payload={"from": prev, "to": to_status, "via": "ApplicationAdmin"},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        messages.success(request, f"Application updated: {prev} → {to_status}.")
        return redirect(reverse("rpngc_admin:recruitment_application_change", args=[app.pk]))

    def approve(self, request, object_id: str):
        return self._do_status_change(request, object_id, models.Application.Status.ACCEPTED)

    def reject(self, request, object_id: str):
        return self._do_status_change(request, object_id, models.Application.Status.REJECTED)

    def shortlist(self, request, object_id: str):
        return self._do_status_change(request, object_id, models.Application.Status.SHORTLISTED)


# =========================
# User admin — shows overview + actions (linked to applicant)
# =========================
@admin.register(models.User, site=rpngc_admin)
class UserAdmin(ModelAdmin):
    change_form_template = "admin/recruitment/user/change_form.html"
    list_display = ("username", "email", "role", "is_active", "is_staff", "last_login")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email")

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if "profile_photo" in fields and "profile_photo_preview" not in fields:
            fields.insert(fields.index("profile_photo") + 1, "profile_photo_preview")
        return fields

    def get_readonly_fields(self, request, obj=None):
        return (*super().get_readonly_fields(request, obj), "profile_photo_preview")

    @admin.display(description="Current profile picture")
    def profile_photo_preview(self, obj):
        if obj and obj.profile_photo:
            return format_html(
                '<img src="{}" alt="Profile picture" style="width:96px;height:96px;object-fit:cover;border-radius:50%">',
                obj.profile_photo.url,
            )
        return "No profile picture uploaded."

    def _get_profile(self, obj: models.User) -> models.ApplicantProfile | None:
        if not obj:
            return None
        try:
            return obj.profile
        except models.ApplicantProfile.DoesNotExist:
            return None

    def render_change_form(self, request, context, *args, **kwargs):
        user_obj: models.User | None = context.get("original")
        prof = self._get_profile(user_obj) if user_obj else None
        current_app = None
        elig = None
        docs = None
        doc_rows = []

        if prof:
            current_app = _current_application_for_profile(prof)
            if current_app:
                elig = getattr(current_app, "eligibility", None)
            docs = models.Document.objects.filter(applicant=prof).order_by("doc_type", "-uploaded_at")

        def doc_badge(d: models.Document) -> str:
            color = {
                models.Document.VerifyStatus.PENDING: "#f59e0b",
                models.Document.VerifyStatus.APPROVED: "#16a34a",
                models.Document.VerifyStatus.REJECTED: "#dc2626",
            }.get(d.verify_status, "#6b7280")
            return f'<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:{color};color:#fff;font-size:11px">{d.get_verify_status_display()}</span>'

        if docs:
            for d in docs:
                fn = d.file.name if d.file else "(missing)"
                doc_rows.append(f"<tr><td>{d.get_doc_type_display()}</td><td>{fn}</td><td>{doc_badge(d)}</td></tr>")

        context.update(
            profile=prof,
            profile_url=(reverse("rpngc_admin:recruitment_applicantprofile_change", args=[prof.pk]) if prof else ""),
            current_app=current_app,
            current_elig=elig,
            current_app_docs=mark_safe("".join(doc_rows)) if doc_rows else "",
        )
        return super().render_change_form(request, context, *args, **kwargs)


# =========================
# Remaining registrations
# =========================
@admin.register(models.Province, site=rpngc_admin)
class ProvinceAdmin(ModelAdmin):
    list_display = ("name", "code", "region")
    list_filter = ("region",)
    search_fields = ("name", "code")

@admin.register(models.District, site=rpngc_admin)
class DistrictAdmin(ModelAdmin):
    list_display = ("name", "province")
    list_filter = ("province",)
    search_fields = ("name",)

@admin.register(models.AlternativeContact, site=rpngc_admin)
class AlternativeContactAdmin(ModelAdmin):
    list_display = ("applicant", "name", "relationship", "phone")
    search_fields = ("name", "phone", "applicant__full_name")

@admin.register(models.ParentGuardian, site=rpngc_admin)
class ParentGuardianAdmin(ModelAdmin):
    list_display = ("applicant", "kind", "name", "is_alive")
    list_filter = ("kind", "is_alive")
    search_fields = ("name", "applicant__full_name")

@admin.register(models.EducationRecord, site=rpngc_admin)
class EducationRecordAdmin(ModelAdmin):
    list_display = ("applicant", "level", "institution", "province", "start_date", "end_date", "gpa")
    list_filter = ("level", "province", "start_date", "end_date")
    search_fields = ("institution", "applicant__full_name")

@admin.register(models.WorkHistory, site=rpngc_admin)
class WorkHistoryAdmin(ModelAdmin):
    list_display = ("applicant", "employer", "position", "start_date", "end_date")
    list_filter = ("start_date", "end_date")
    search_fields = ("employer", "position", "applicant__full_name")

@admin.register(models.Reference, site=rpngc_admin)
class ReferenceAdmin(ModelAdmin):
    list_display = ("applicant", "name", "position_title", "phone_number", "email")
    search_fields = ("name", "position_title", "phone_number", "email", "applicant__full_name")

@admin.register(models.Document, site=rpngc_admin)
class DocumentAdmin(ModelAdmin):
    list_display = ("applicant", "doc_type", "verify_status", "uploaded_at")
    list_filter = ("doc_type", "verify_status")
    search_fields = ("applicant__full_name",)

@admin.register(models.RecruitmentCycle, site=rpngc_admin)
class RecruitmentCycleAdmin(ModelAdmin):
    list_display = ("name", "intake_year", "rec_type", "start_date", "end_date", "is_active",
                    "min_age", "max_age", "min_education_level")
    list_filter = ("rec_type", "is_active", "intake_year")
    search_fields = ("name",)

@admin.register(models.ApplicationEligibility, site=rpngc_admin)
class ApplicationEligibilityAdmin(ModelAdmin):
    list_display = ("application", "age_ok", "education_ok", "medical_ok", "police_ok",
                    "duplicates_ok", "result", "run_at")
    list_filter = ("result", "age_ok", "education_ok", "medical_ok", "police_ok")

@admin.register(models.ScreeningAction, site=rpngc_admin)
class ScreeningActionAdmin(ModelAdmin):
    list_display = ("application", "auto_score", "manual_adjustment", "by_user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("application__applicant__full_name",)

@admin.register(models.Test, site=rpngc_admin)
class TestAdmin(ModelAdmin):
    list_display = ("name", "cycle", "opens_at", "closes_at", "is_published", "max_score", "max_attempts")
    list_filter = ("is_published", "cycle")
    search_fields = ("name",)

@admin.register(models.Question, site=rpngc_admin)
class QuestionAdmin(ModelAdmin):
    list_display = ("test", "order", "points")
    list_filter = ("test",)
    search_fields = ("text",)

@admin.register(models.Choice, site=rpngc_admin)
class ChoiceAdmin(ModelAdmin):
    list_display = ("question", "text", "is_correct")
    list_filter = ("is_correct", "question")

@admin.register(models.TestAttempt, site=rpngc_admin)
class TestAttemptAdmin(ModelAdmin):
    list_display = ("test", "application", "status", "score", "started_at", "submitted_at")
    list_filter = ("status", "test")
    search_fields = ("application__applicant__full_name",)

@admin.register(models.AttemptAnswer, site=rpngc_admin)
class AttemptAnswerAdmin(ModelAdmin):
    list_display = ("attempt", "question", "selected_choice", "is_correct", "awarded_points")
    list_filter = ("is_correct", "attempt__test")

@admin.register(models.InterviewSchedule, site=rpngc_admin)
class InterviewScheduleAdmin(ModelAdmin):
    list_display = ("application", "scheduled_at", "location", "panel_name", "status", "created_by")
    list_filter = ("status", "scheduled_at")
    search_fields = ("application__applicant__full_name", "panel_name")

@admin.register(models.InterviewScore, site=rpngc_admin)
class InterviewScoreAdmin(ModelAdmin):
    list_display = ("schedule", "interviewer", "score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("schedule__application__applicant__full_name",)

@admin.register(models.FinalSelection, site=rpngc_admin)
class FinalSelectionAdmin(ModelAdmin):
    list_display = ("application", "rank", "total_score_snapshot", "is_published", "approved_by", "approved_at")
    list_filter = ("is_published",)
    search_fields = ("application__applicant__full_name",)

@admin.register(models.Notification, site=rpngc_admin)
class NotificationAdmin(ModelAdmin):
    list_display = ("user", "ntype", "title", "is_read", "created_at")
    list_filter = ("ntype", "is_read", "created_at")
    search_fields = ("title", "user__username", "user__email")

@admin.register(models.AuditLog, site=rpngc_admin)
class AuditLogAdmin(ModelAdmin):
    list_display = ("actor", "action", "entity", "entity_id", "created_at", "ip_address")
    list_filter = ("action", "created_at")
    search_fields = ("entity", "entity_id", "actor__username")
