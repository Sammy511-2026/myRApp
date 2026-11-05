from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from .admin_applicant_table import ApplicantTableMixin
from .models import (
    User,
    Province, District,
    ApplicantProfile, AlternativeContact, ParentGuardian,
    EducationRecord, WorkHistory, Reference, Document,
    RecruitmentCycle, Application, ApplicationEligibility, ScreeningAction,
    Test, Question, Choice, TestAttempt, AttemptAnswer,
    InterviewSchedule, InterviewScore, FinalSelection,
    Notification, AuditLog,
)

# =============================
# Helpers & Role gating
# =============================

def _is_admin_user(user):
    """Admins/Officers (or superusers) can edit status; others view-only."""
    if user.is_superuser:
        return True
    role = getattr(user, "role", None)
    try:
        return role in (User.Roles.ADMIN, User.Roles.OFFICER)
    except Exception:
        # Fallback if no roles available
        return user.is_staff

def _has_field(model, name: str) -> bool:
    return any(getattr(f, "name", None) == name for f in model._meta.get_fields())

def _table(rows):
    body = format_html_join(
        "",
        "<tr><th style='text-align:left;padding:6px 8px;width:220px;color:#444'>{}</th>"
        "<td style='padding:6px 8px'>{}</td></tr>",
        rows,
    )
    return format_html("<table style='width:100%;border-collapse:collapse'>{}</table>", body)


def _records_table(title, headers, rows):
    rows = list(rows)
    if not rows:
        return format_html("<h3>{}</h3><p><em>None recorded.</em></p>", title)

    header_cells = format_html_join("", "<th style='text-align:left;padding:6px 8px'>{}</th>", ((h,) for h in headers))
    body_rows = format_html_join(
        "",
        "<tr>{}</tr>",
        (
            (format_html_join("", "<td style='padding:6px 8px;vertical-align:top'>{}</td>", ((value,) for value in row)),)
            for row in rows
        ),
    )
    table = format_html(
        "<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse'>"
        "<thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>",
        header_cells,
        body_rows,
    )
    return format_html("<h3>{}</h3>{}", title, table) if title else table


# =============================
# Core / Accounts
# =============================
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff", "is_superuser")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

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


# =============================
# Locations
# =============================
@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "region")
    list_filter = ("region",)
    search_fields = ("name", "code")


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "province")
    list_filter = ("province",)
    search_fields = ("name", "province__name", "province__code")


# =============================
# Applicant Profile & Related (LOCKED: view-only)
# =============================

class ApplicantReadOnlyInline:
    extra = 0
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)


class ApplicantApplicationInline(ApplicantReadOnlyInline, admin.StackedInline):
    model = Application
    show_change_link = True
    fields = (
        "cycle", "status", "submitted_at", "last_updated", "applied_unit",
        "from_bougainville", "years_experience", "years_experience_other",
        "reservist_2021_2022", "reason_for_applying", "criminal_conviction",
        "declaration_agreed", "signature_name", "signature_date",
        "auto_screen_score", "manual_adjustment", "test_score", "interview_score",
        "total_score", "eligibility_passed", "disqualification_reason",
    )


class ApplicantContactInline(ApplicantReadOnlyInline, admin.StackedInline):
    model = AlternativeContact
    fk_name = "applicant"
    max_num = 20


class ApplicantParentInline(ApplicantReadOnlyInline, admin.TabularInline):
    model = ParentGuardian
    fk_name = "applicant"


class ApplicantEducationInline(ApplicantReadOnlyInline, admin.TabularInline):
    model = EducationRecord
    fk_name = "applicant"
    fields = (
        "level", "institution", "province", "start_date", "end_date", "gpa",
        "english_grade", "mathematics_grade", "science_grade", "other_grade",
    )


class ApplicantWorkInline(ApplicantReadOnlyInline, admin.TabularInline):
    model = WorkHistory
    fk_name = "applicant"


class ApplicantReferenceInline(ApplicantReadOnlyInline, admin.TabularInline):
    model = Reference
    fk_name = "applicant"


class ApplicantDocumentInline(ApplicantReadOnlyInline, admin.TabularInline):
    model = Document
    fk_name = "applicant"
    fields = (
        "doc_type", "file_link", "verify_status", "verified_by",
        "verification_note", "uploaded_at",
    )

    def get_readonly_fields(self, request, obj=None):
        return (*super().get_readonly_fields(request, obj), "file_link")

    @admin.display(description="Uploaded file")
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank" rel="noopener">Open document</a>', obj.file.url)
        return "—"


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(ApplicantTableMixin, admin.ModelAdmin):
    change_form_template = "admin/recruitment/applicantprofile/default_change_form.html"
    inlines = (
        ApplicantApplicationInline,
        ApplicantContactInline,
        ApplicantParentInline,
        ApplicantEducationInline,
        ApplicantWorkInline,
        ApplicantReferenceInline,
        ApplicantDocumentInline,
    )

    def get_readonly_fields(self, request, obj=None):
        # All fields read-only
        return [f.name for f in ApplicantProfile._meta.fields]

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    def render_change_form(self, request, context, *args, **kwargs):
        profile = context.get("original")
        current_app = None
        documents = ()
        screening_actions = ()
        if profile:
            active_cycle = RecruitmentCycle.objects.filter(is_active=True).order_by("-start_date").first()
            current_app = (
                Application.objects.filter(applicant=profile, cycle=active_cycle).select_related("cycle").first()
                if active_cycle else None
            )
            if current_app is None:
                current_app = Application.objects.filter(applicant=profile).select_related(
                    "cycle"
                ).order_by("-submitted_at", "-pk").first()
            documents = Document.objects.filter(applicant=profile).select_related(
                "verified_by"
            ).order_by("doc_type", "-uploaded_at")
            if current_app:
                screening_actions = current_app.screening_actions.select_related("by_user").all()

        context.update(
            profile_application=current_app,
            profile_documents=documents,
            profile_screening_actions=screening_actions,
            can_change_profile_application=request.user.has_perm("recruitment.change_application"),
            profile_print_url=(
                reverse("rpngc_admin:recruitment_applicantprofile_print", args=[profile.pk])
                if profile else ""
            ),
        )
        return super().render_change_form(request, context, *args, **kwargs)


class _ViewOnlyAdmin(admin.ModelAdmin):
    """Base for related applicant models: read-only, no add/change/delete."""
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AlternativeContact)
class AlternativeContactAdmin(_ViewOnlyAdmin):
    list_display = ("applicant", "name", "relationship", "phone")
    search_fields = ("applicant__full_name", "name", "relationship", "phone")


@admin.register(ParentGuardian)
class ParentGuardianAdmin(_ViewOnlyAdmin):
    list_display = ("applicant", "kind", "name", "is_alive")
    list_filter = ("kind", "is_alive")
    search_fields = ("applicant__full_name", "name")


@admin.register(EducationRecord)
class EducationRecordAdmin(_ViewOnlyAdmin):
    list_display = ("applicant", "level", "institution", "province", "start_date", "end_date", "gpa")
    list_filter = ("level", "province", "start_date", "end_date")
    search_fields = ("applicant__full_name", "institution", "certificate_title")


@admin.register(WorkHistory)
class WorkHistoryAdmin(_ViewOnlyAdmin):
    list_display = ("applicant", "employer", "position", "start_date", "end_date")
    list_filter = ("start_date", "end_date")
    search_fields = ("applicant__full_name", "employer", "position", "duties")


@admin.register(Reference)
class ReferenceAdmin(_ViewOnlyAdmin):
    list_display = ("applicant", "name", "position_title", "phone_number", "email")
    search_fields = ("applicant__full_name", "name", "position_title", "phone_number", "email")


@admin.register(Document)
class DocumentAdmin(_ViewOnlyAdmin):
    """Documents are view/download-only in admin."""
    list_display = ("applicant", "doc_type", "verify_status", "uploaded_at", "file_link")
    list_filter = ("doc_type", "verify_status")
    search_fields = ("applicant__full_name", "verification_note")
    autocomplete_fields = ("applicant",)

    def file_link(self, obj):
        f = getattr(obj, "file", None)
        if f:
            return format_html('<a href="{}" target="_blank" rel="noopener">Open</a>', f.url)
        return "—"
    file_link.short_description = "File"


# =============================
# Recruitment Cycles
# =============================
@admin.register(RecruitmentCycle)
class RecruitmentCycleAdmin(admin.ModelAdmin):
    list_display = ("name", "intake_year", "rec_type", "start_date", "end_date", "is_active")
    list_filter = ("rec_type", "is_active", "intake_year")
    search_fields = ("name",)
    date_hierarchy = "start_date"


# =============================
# Applications (Inline status update + one-screen review + notify on change)
# =============================

class ApplicationDecisionForm(forms.ModelForm):
    # Non-model field to include a note in the applicant Notification (used on detail page)
    decision_note = forms.CharField(
        label="Decision note (sent to applicant)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "style": "resize:vertical;"}),
        help_text="Optional message included in the applicant notification."
    )

    class Meta:
        model = Application
        fields = ("status",)  # Only editable model field


class ApplicationEligibilityInline(admin.StackedInline):
    model = ApplicationEligibility
    extra = 0
    max_num = 1
    can_delete = False
    readonly_fields = tuple(field.name for field in ApplicationEligibility._meta.fields)

    def has_add_permission(self, request, obj=None):
        return False


class ScreeningActionInline(admin.TabularInline):
    model = ScreeningAction
    extra = 0
    can_delete = False
    fields = ("auto_score", "manual_adjustment", "reason", "by_user", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ApplicationInterviewInline(admin.TabularInline):
    model = InterviewSchedule
    extra = 1
    fields = ("scheduled_at", "location", "panel_name", "status", "created_by", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields["created_by"].initial = request.user.pk
        formset.form.base_fields["created_by"].required = False
        return formset


class ApplicationTestAttemptInline(admin.TabularInline):
    model = TestAttempt
    extra = 0
    can_delete = False
    fields = ("test", "status", "started_at", "submitted_at", "score")
    readonly_fields = fields
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ApplicationFinalSelectionInline(admin.StackedInline):
    model = FinalSelection
    extra = 1
    max_num = 1
    fields = ("rank", "total_score_snapshot", "approved_by", "approved_at", "is_published", "offer_letter")
    readonly_fields = ("approved_at",)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields["approved_by"].initial = request.user.pk
        formset.form.base_fields["approved_by"].required = False
        return formset


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    form = ApplicationDecisionForm
    inlines = (
        ApplicationEligibilityInline,
        ScreeningActionInline,
        ApplicationInterviewInline,
        ApplicationTestAttemptInline,
        ApplicationFinalSelectionInline,
    )

    list_display = ("applicant_link", "region", "cycle", "status", "submitted_at")
    list_display_links = ("applicant_link",)
    list_filter = (
        "applicant__province__region",
        "applicant__province",
        "applicant__district",
        "status",
        "cycle__intake_year",
        "cycle__rec_type",
        "eligibility_passed",
    )
    search_fields = (
        "applicant__full_name",
        "applicant__user__username",
        "applicant__phone",
        "applicant__email",
        "cycle__name",
    )
    ordering = ("-submitted_at", "-pk")
    actions = None

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(submitted_at__isnull=False)
            .select_related("applicant__user", "applicant__province", "applicant__district", "cycle")
            .prefetch_related(
                "applicant__alt_contacts",
                "applicant__parents",
                "applicant__education",
                "applicant__work_history",
                "applicant__references",
                "applicant__documents",
            )
        )

    @admin.display(description="Region", ordering="applicant__province__region")
    def region(self, obj):
        province = obj.applicant.province
        if not province or not province.region:
            return "—"
        return province.get_region_display()

    BASE_SECTIONS = ("_applicant_info", "_application_info", "_documents_list", "_timeline")
    def get_fields(self, request, obj=None):
        return ("status", "decision_note", *self.BASE_SECTIONS)

    def get_readonly_fields(self, request, obj=None):
        ro = set(self.BASE_SECTIONS)
        for f in Application._meta.fields:
            ro.add(f.name)
        ro.discard("status")
        valid = set(self.BASE_SECTIONS) | {f.name for f in Application._meta.fields}
        return tuple(n for n in ro if n in valid)

    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return _is_admin_user(request.user)

    @admin.display(description="Applicant")
    def applicant_link(self, obj: Application):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:recruitment_application_change", args=[obj.pk]),
            obj.applicant.full_name,
        )

    @admin.display(description="Applicant")
    def _applicant_info(self, obj: Application):
        p = obj.applicant
        u = getattr(p, "user", None)
        rows = [
            ("Full name", getattr(p, "full_name", "—")),
            ("Username", getattr(u, "username", "—") if u else "—"),
            ("Email", getattr(p, "email", "") or (getattr(u, "email", "—") if u else "—")),
            ("DOB", getattr(p, "dob", "—")),
            ("Age", p.age if p.age is not None else "—"),
            ("Gender", p.get_gender_display() if hasattr(p, "get_gender_display") else getattr(p, "gender", "—")),
            ("Highest education", p.get_highest_education_level_display() if hasattr(p, "get_highest_education_level_display") else getattr(p, "highest_education_level", "—")),
            ("NID", getattr(p, "nid_number", "—") or "—"),
            ("Phone", getattr(p, "phone", "—") or "—"),
            ("Address", getattr(p, "address", "—") or "—"),
            ("Province", getattr(p, "province", "—") or "—"),
            ("District", getattr(p, "district", "—") or "—"),
            ("Province of origin", getattr(p, "province_of_origin", "—") or "—"),
        ]
        if p.photo:
            rows.append((
                "Profile picture",
                format_html('<a href="{}" target="_blank" rel="noopener">View profile picture</a>', p.photo.url),
            ))
        related = [
            _records_table(
                "Alternative contacts",
                ("Name", "Relationship", "Phone", "Address"),
                (
                    (contact.name, contact.relationship or "—", contact.phone or "—", contact.address or "—")
                    for contact in p.alt_contacts.all()
                ),
            ),
            _records_table(
                "Parents and guardians",
                ("Type", "Name", "Phone", "Address", "Status"),
                (
                    (
                        parent.get_kind_display(),
                        parent.name,
                        parent.phone or "—",
                        parent.address or "—",
                        "Alive" if parent.is_alive else "Deceased",
                    )
                    for parent in p.parents.all()
                ),
            ),
            _records_table(
                "Education",
                ("Level", "Institution", "Province", "Dates", "Certificate", "GPA", "Grades"),
                (
                    (
                        item.get_level_display(),
                        item.institution or "—",
                        item.province or "—",
                        f"{item.start_date or '—'} – {item.end_date or '—'}",
                        item.certificate_title or "—",
                        item.gpa or "—",
                        ", ".join(
                            f"{label}: {value}"
                            for label, value in (
                                ("English", item.english_grade),
                                ("Math", item.mathematics_grade),
                                ("Science", item.science_grade),
                                ("Other", item.other_grade),
                            )
                            if value
                        ) or "—",
                    )
                    for item in p.education.all()
                ),
            ),
            _records_table(
                "Work history",
                ("Employer", "Position", "Dates", "Duties"),
                (
                    (
                        item.employer,
                        item.position or "—",
                        f"{item.start_date or '—'} – {item.end_date or '—'}",
                        item.duties or "—",
                    )
                    for item in p.work_history.all()
                ),
            ),
            _records_table(
                "References",
                ("Name", "Position", "Phone", "Email"),
                (
                    (item.name, item.position_title or "—", item.phone_number or "—", item.email or "—")
                    for item in p.references.all()
                ),
            ),
        ]
        return format_html(
            "{}{}",
            _table(rows),
            format_html_join("", "{}", ((section,) for section in related)),
        )

    @admin.display(description="Application")
    def _application_info(self, obj: Application):
        rows = []
        for field in Application._meta.fields:
            value = getattr(obj, field.name)
            if field.choices:
                value = getattr(obj, f"get_{field.name}_display")()
            elif field.is_relation and value is not None:
                value = str(value)
            elif isinstance(value, bool):
                value = "Yes" if value else "No"
            elif value in (None, ""):
                value = "—"
            rows.append((field.verbose_name.capitalize(), value))
        return _table(rows)

    @admin.display(description="Documents")
    def _documents_list(self, obj: Application):
        docs = Document.objects.filter(applicant=obj.applicant).order_by("doc_type")
        if not docs.exists():
            return format_html("<p><em>No documents uploaded for this applicant.</em></p>")
        return _records_table(
            "",
            ("Document", "File", "Verification", "Verified by", "Verification note", "Uploaded"),
            (
                (
                    document.get_doc_type_display(),
                    format_html(
                        '<a href="{}" target="_blank" rel="noopener">Open document</a>',
                        document.file.url,
                    ) if document.file else "—",
                    format_html(
                        '<select name="document_status_{}">{}</select>',
                        document.pk,
                        format_html_join(
                            "",
                            '<option value="{}"{}>{}</option>',
                            (
                                (
                                    value,
                                    ' selected' if document.verify_status == value else '',
                                    label,
                                )
                                for value, label in Document.VerifyStatus.choices
                            ),
                        ),
                    ),
                    document.verified_by or "—",
                    format_html(
                        '<input type="text" name="document_note_{}" value="{}" '
                        'style="min-width:180px;max-width:100%">',
                        document.pk,
                        document.verification_note,
                    ),
                    document.uploaded_at,
                )
                for document in docs.select_related("verified_by")
            ),
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        application = form.instance
        documents = Document.objects.filter(applicant=application.applicant)
        for document in documents:
            status = request.POST.get(f"document_status_{document.pk}")
            note = request.POST.get(f"document_note_{document.pk}", document.verification_note)
            if status is None:
                continue
            if status not in Document.VerifyStatus.values:
                messages.error(request, f"Invalid verification status for {document.get_doc_type_display()}.")
                continue
            updates = []
            if document.verify_status != status:
                document.verify_status = status
                document.verified_by = request.user if status != Document.VerifyStatus.PENDING else None
                updates.extend(("verify_status", "verified_by"))
            if document.verification_note != note:
                document.verification_note = note
                updates.append("verification_note")
            if updates:
                document.save(update_fields=updates)

    @admin.display(description="Timeline")
    def _timeline(self, obj: Application):
        qs = ScreeningAction.objects.filter(application=obj).select_related("by_user").order_by("created_at")
        if not qs.exists():
            return format_html("<p><em>No recorded actions yet.</em></p>")
        lis = []
        for a in qs:
            by = a.by_user.get_full_name() or a.by_user.username if getattr(a, "by_user_id", None) else "—"
            note = (
                format_html("<div style='color:#555;margin-top:4px'>{}</div>", a.reason)
                if a.reason else ""
            )
            lis.append(format_html(
                "<strong>{}</strong> <span style='color:#666'>({})</span>{}",
                by,
                a.created_at.strftime("%Y-%m-%d %H:%M"),
                note,
            ))
        items = format_html_join("", "<li>{}</li>", ((item,) for item in lis))
        return format_html("<ul style='margin:0;padding-left:16px'>{}</ul>", items)

    # ---------- NOTIFY ON STATUS CHANGE (works for list and detail) ----------
    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            try:
                old_status = Application.objects.only("status").get(pk=obj.pk).status
            except Application.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        if old_status and obj.status != old_status:
            decision_note = ""
            if hasattr(form, "cleaned_data"):
                decision_note = form.cleaned_data.get("decision_note", "") or ""
            old_status_label = Application.Status(old_status).label
            new_status_label = obj.get_status_display()
            action_reason = (
                f"Status changed from {old_status_label} to {new_status_label}."
            )
            if decision_note:
                action_reason = f"{action_reason} {decision_note}"

            # optional timeline row
            try:
                ScreeningAction.objects.create(
                    application=obj,
                    by_user=request.user,
                    reason=action_reason,
                )
            except Exception:
                pass

            # notify applicant
            try:
                kwargs = dict(
                    user=obj.applicant.user,
                    title="Application status updated",
                    body=f"Your application for {obj.cycle} is now "
                         f"'{obj.get_status_display() if hasattr(obj,'get_status_display') else obj.status}'. "
                         f"{('Note: ' + decision_note) if decision_note else ''}",
                )
                if _has_field(Notification, "ntype"):
                    kwargs["ntype"] = "STATUS"
                if _has_field(Notification, "is_read"):
                    kwargs["is_read"] = False
                elif _has_field(Notification, "seen"):
                    kwargs["seen"] = False
                Notification.objects.create(**kwargs)
            except Exception:
                pass

            messages.success(request, "Status updated and applicant notified.")


# =============================
# Eligibility & Screening
# =============================
@admin.register(ApplicationEligibility)
class ApplicationEligibilityAdmin(admin.ModelAdmin):
    list_display = ("application", "result", "age_ok", "education_ok", "medical_ok", "police_ok", "run_at")
    list_filter = ("result", "age_ok", "education_ok", "medical_ok", "police_ok")
    search_fields = ("application__applicant__full_name",)


@admin.register(ScreeningAction)
class ScreeningActionAdmin(admin.ModelAdmin):
    """Make timeline viewable but not editable to avoid backdoor CRUD on applicant flow."""
    list_display = ("application", "auto_score", "manual_adjustment", "by_user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("application__applicant__full_name", "reason")
    autocomplete_fields = ("application", "by_user")

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in ScreeningAction._meta.fields]

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


# =============================
# Tests & Questions
# =============================
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("name", "cycle", "opens_at", "closes_at", "is_published", "max_score", "max_attempts")
    list_filter = ("is_published", "cycle__intake_year")
    search_fields = ("name", "cycle__name")
    autocomplete_fields = ("cycle",)
    date_hierarchy = "opens_at"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("test", "order", "points")
    list_filter = ("test",)
    search_fields = ("test__name", "text")
    autocomplete_fields = ("test",)
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "text", "is_correct")
    list_filter = ("is_correct",)
    search_fields = ("question__test__name", "text")
    autocomplete_fields = ("question",)


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ("test", "application", "status", "started_at", "submitted_at", "score")
    list_filter = ("status", "started_at", "submitted_at")
    search_fields = ("test__name", "application__applicant__full_name")
    autocomplete_fields = ("test", "application")
    inlines = (AttemptAnswerInline,)


@admin.register(AttemptAnswer)
class AttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "selected_choice", "is_correct", "awarded_points")
    list_filter = ("is_correct",)
    search_fields = ("attempt__test__name", "question__text")
    autocomplete_fields = ("attempt", "question", "selected_choice")


# =============================
# Interviews & Selection
# =============================
class InterviewScoreInline(admin.TabularInline):
    model = InterviewScore
    extra = 0
    fields = ("interviewer", "score", "remarks", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("interviewer",)


@admin.register(InterviewSchedule)
class InterviewScheduleAdmin(admin.ModelAdmin):
    list_display = ("application", "scheduled_at", "location", "panel_name", "status", "created_by")
    list_filter = ("status", "scheduled_at")
    search_fields = (
        "panel_name",
        "location",
        "application__applicant__full_name",
        "application__cycle__name",
    )
    autocomplete_fields = ("application", "created_by")
    date_hierarchy = "scheduled_at"
    inlines = (InterviewScoreInline,)


@admin.register(InterviewScore)
class InterviewScoreAdmin(admin.ModelAdmin):
    list_display = ("schedule", "interviewer", "score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("schedule__panel_name", "interviewer__username")
    autocomplete_fields = ("schedule", "interviewer")


@admin.register(FinalSelection)
class FinalSelectionAdmin(admin.ModelAdmin):
    list_display = ("application", "rank", "total_score_snapshot", "approved_by", "approved_at", "is_published")
    list_filter = ("is_published",)
    search_fields = ("application__applicant__full_name",)
    autocomplete_fields = ("application", "approved_by")


# =============================
# Notifications & Audit
# =============================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "ntype", "title", "is_read", "created_at")
    list_filter = ("ntype", "is_read", "created_at")
    search_fields = ("user__username", "title", "body")
    autocomplete_fields = ("user",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "entity", "entity_id", "ip_address", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "entity", "entity_id", "ip_address")
    autocomplete_fields = ("actor",)
