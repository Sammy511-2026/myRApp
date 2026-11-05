from __future__ import annotations
from django.contrib import admin
from .admin_site import rpngc_admin_site
from .models import (
    ApplicantProfile, AlternativeContact, ParentGuardian, EducationRecord,
    WorkHistory, Reference, Document, Application
)

# ---- read-only mixins ----
class ReadOnlyMixin:
    def has_add_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_view_permission(self, request, obj=None): return True
    def get_readonly_fields(self, request, obj=None):
        ro = [f.name for f in self.model._meta.fields]
        ro += [m.name for m in self.model._meta.many_to_many]
        return ro

class ReadOnlyInlineMixin:
    can_delete = False
    extra = 0
    def has_add_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_view_permission(self, request, obj=None): return True
    def get_readonly_fields(self, request, obj=None):
        ro = [f.name for f in self.model._meta.fields]
        ro += [m.name for m in self.model._meta.many_to_many]
        return ro

# ---- inlines ----
class AlternativeContactInlineRO(ReadOnlyInlineMixin, admin.StackedInline):
    model = AlternativeContact
    max_num = 1

class ParentGuardianInlineRO(ReadOnlyInlineMixin, admin.TabularInline):
    model = ParentGuardian

class EducationRecordInlineRO(ReadOnlyInlineMixin, admin.StackedInline):
    model = EducationRecord

class WorkHistoryInlineRO(ReadOnlyInlineMixin, admin.StackedInline):
    model = WorkHistory

class ReferenceInlineRO(ReadOnlyInlineMixin, admin.TabularInline):
    model = Reference

class DocumentInlineRO(ReadOnlyInlineMixin, admin.TabularInline):
    model = Document
    fields = ("doc_type", "file", "verify_status", "verified_by", "verification_note", "uploaded_at")
    readonly_fields = ("uploaded_at",)
    autocomplete_fields = ("verified_by",)

class ApplicationInlineRO(ReadOnlyInlineMixin, admin.TabularInline):
    model = Application
    fields = ("cycle", "status", "total_score", "submitted_at")
    readonly_fields = ("cycle", "status", "total_score", "submitted_at")
    autocomplete_fields = ("cycle",)

# ---- main read-only ApplicantProfile ----
@admin.register(ApplicantProfile, site=rpngc_admin_site)
class ApplicantProfileAdmin(ReadOnlyMixin, admin.ModelAdmin):
    inlines = [
        AlternativeContactInlineRO, ParentGuardianInlineRO,
        EducationRecordInlineRO, WorkHistoryInlineRO, ReferenceInlineRO,
        DocumentInlineRO, ApplicationInlineRO,
    ]
    list_display = ("full_name", "user", "nid_number", "gender", "province", "district", "highest_education_level")
    list_filter = ("gender", "province", "highest_education_level")
    search_fields = ("full_name", "user__username", "nid_number", "phone", "address")
    autocomplete_fields = ("user", "province", "district", "province_of_origin")
    fieldsets = (
        ("Identity", {"fields": ("user", "full_name", "dob", "gender", "nid_number", "photo")}),
        ("Contact", {"fields": ("address", "province", "district", "phone", "email")}),
        ("Origin", {"fields": ("province_of_origin",)}),
        ("Education", {"fields": ("highest_education_level",)}),
        ("Meta", {"fields": ("created_at",)}),
    )
