from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.db.models.functions import Lower

# ---------------------------------------------------------------------
# Core / Accounts
# ---------------------------------------------------------------------
def user_profile_photo_path(instance: "User", filename: str) -> str:
    return f"users/{instance.pk}/profile/{filename}"


class User(AbstractUser):
    class Roles(models.TextChoices):
        APPLICANT = "APPLICANT", "Applicant"
        OFFICER = "OFFICER", "Recruitment Officer"
        ADMIN = "ADMIN", "Administrator"

    role = models.CharField(max_length=16, choices=Roles.choices, default=Roles.APPLICANT, db_index=True)
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    profile_photo = models.ImageField(upload_to=user_profile_photo_path, null=True, blank=True)

    def is_applicant(self) -> bool: return self.role == self.Roles.APPLICANT
    def is_officer(self) -> bool: return self.role == self.Roles.OFFICER
    def is_admin(self) -> bool: return self.role == self.Roles.ADMIN


# ---------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------
class Province(models.Model):
    class Region(models.TextChoices):
        SOUTHERN = "SOUTHERN", "Southern"
        HIGHLANDS = "HIGHLANDS", "Highlands"
        MOMASE = "MOMASE", "Momase"
        ISLANDS = "ISLANDS", "Islands"

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    region = models.CharField(max_length=12, choices=Region.choices, blank=True)

    class Meta:
        ordering = ["region", "name"]
        db_table = "geo_provinces"

    def __str__(self): return self.name


class District(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=120)

    class Meta:
        unique_together = ("province", "name")
        ordering = ["province__name", "name"]
        db_table = "geo_districts"

    def __str__(self): return f"{self.name} ({self.province.code})"


# ---------------------------------------------------------------------
# Applicant Profile & Documents
# ---------------------------------------------------------------------
def applicant_photo_path(instance: "ApplicantProfile", filename: str) -> str:
    return f"applicants/{instance.user_id}/photo/{filename}"

def document_upload_path(instance: "Document", filename: str) -> str:
    return f"applicants/{instance.applicant_id}/docs/{instance.doc_type}/{filename}"

class ApplicantProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other / Prefer not to say"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150)
    dob = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices)

    nid_number = models.CharField(max_length=30, null=True, blank=True)
    photo = models.ImageField(upload_to=applicant_photo_path, null=True, blank=True)

    address = models.TextField(blank=True)
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    province_of_origin = models.ForeignKey(
        Province, on_delete=models.SET_NULL, null=True, blank=True, related_name="origin_profiles"
    )

    class EducationLevel(models.IntegerChoices):
        G12 = 12, "Grade 12"
        TER_TI = 13, "Tertiary – Certificate/Diploma"
        TER_BACH = 16, "Tertiary – Bachelor"
        TER_PG = 18, "Tertiary – Postgraduate"

    highest_education_level = models.IntegerField(
        choices=EducationLevel.choices,
        default=EducationLevel.G12,
        help_text="Used for baseline eligibility; documents provide proof."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "applicant_profiles"
        constraints = [
            UniqueConstraint(
                Lower("nid_number"),
                name="uniq_nid_when_present_ci",
                condition=Q(nid_number__isnull=False) & ~Q(nid_number=""),
            ),
        ]

    @property
    def age(self) -> Optional[int]:
        if not self.dob:
            return None
        today = date.today()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))

    def __str__(self): return f"{self.full_name} ({self.user.username})"


class Document(models.Model):
    class DocType(models.TextChoices):
        G12_CERT = "G12_CERT", "Grade 12 Certificate"
        BIRTH_CERT = "BIRTH_CERT", "Birth Certificate"
        NID_PASSPORT = "NID_PASSPORT", "NID/Passport"
        MED_CLEAR = "MED_CLEAR", "Medical Clearance"
        POL_CLEAR = "POL_CLEAR", "Police Clearance"
        CHAR_REF = "CHAR_REF", "Character Reference"
        TERTIARY = "TERTIARY", "Tertiary Qualification"

    class VerifyStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    applicant = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=20, choices=DocType.choices, db_index=True)
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png"])],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verify_status = models.CharField(max_length=10, choices=VerifyStatus.choices, default=VerifyStatus.PENDING)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_documents"
    )
    verification_note = models.TextField(blank=True)

    class Meta:
        unique_together = ("applicant", "doc_type")
        indexes = [models.Index(fields=["doc_type", "verify_status"])]
        db_table = "applicant_documents"

    def __str__(self): return f"{self.get_doc_type_display()} - {self.applicant}"


# ---------------------------------------------------------------------
# Recruitment Cycles & Eligibility
# ---------------------------------------------------------------------
class RecruitmentCycle(models.Model):
    class RecType(models.TextChoices):
        REGULAR = "REGULAR", "Regular"
        RESERVE = "RESERVE", "Reservist"
        SPECIAL = "SPECIAL", "Cadet"

    name = models.CharField(max_length=120)
    intake_year = models.PositiveIntegerField()
    rec_type = models.CharField(max_length=10, choices=RecType.choices, default=RecType.REGULAR, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    min_age = models.PositiveSmallIntegerField(default=18, validators=[MinValueValidator(15), MaxValueValidator(60)])
    max_age = models.PositiveSmallIntegerField(default=30, validators=[MinValueValidator(15), MaxValueValidator(60)])
    min_education_level = models.IntegerField(
        choices=ApplicantProfile.EducationLevel.choices,
        default=ApplicantProfile.EducationLevel.G12
    )

    quotas = models.JSONField(blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_cycles"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-intake_year", "-start_date"]
        unique_together = ("intake_year", "name", "rec_type")
        db_table = "recruitment_cycles"

    def __str__(self): return f"{self.name} {self.intake_year} ({self.get_rec_type_display()})"

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError("start_date must be before end_date.")


class EligibilityCheck(models.Model):
    class Status(models.TextChoices):
        PASS = "PASS", "Pass"
        FAIL = "FAIL", "Fail"

    age_ok = models.BooleanField(default=False)
    education_ok = models.BooleanField(default=False)
    medical_ok = models.BooleanField(default=False)
    police_ok = models.BooleanField(default=False)
    duplicates_ok = models.BooleanField(default=True)

    result = models.CharField(max_length=4, choices=Status.choices, default=Status.FAIL)
    details = models.JSONField(blank=True, null=True)
    run_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------
# Applications & Screening
# ---------------------------------------------------------------------
class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SCREENING = "SCREENING", "Screening"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        REJECTED = "REJECTED", "Rejected"
        ACCEPTED = "ACCEPTED", "Accepted"

    class YearsExperience(models.TextChoices):
        Y1_2 = "1-2", "1–2"
        Y2_5 = "2-5", "2–5"
        Y5_7 = "5-7", "5–7"
        OTHER = "OTHER", "Other"

    applicant = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE, related_name="applications")
    cycle = models.ForeignKey(RecruitmentCycle, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    applied_unit = models.CharField(max_length=120, blank=True)

    from_bougainville = models.BooleanField(default=False)
    years_experience = models.CharField(max_length=8, choices=YearsExperience.choices, blank=True)
    years_experience_other = models.CharField(max_length=50, blank=True)
    reservist_2021_2022 = models.BooleanField(default=False)
    reason_for_applying = models.TextField(blank=True)
    criminal_conviction = models.BooleanField(null=True, blank=True)
    declaration_agreed = models.BooleanField(default=False)
    signature_name = models.CharField(max_length=120, blank=True)
    signature_date = models.DateField(null=True, blank=True)

    auto_screen_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    manual_adjustment = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    test_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    interview_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    total_score = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"), db_index=True)

    eligibility_passed = models.BooleanField(default=False)
    disqualification_reason = models.TextField(blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("applicant", "cycle")
        indexes = [
            models.Index(fields=["cycle", "status"]),
            models.Index(fields=["cycle", "total_score"]),
        ]
        ordering = ["-total_score", "id"]
        db_table = "applications"

    def __str__(self): return f"{self.applicant.full_name} - {self.cycle}"

    def recalc_total(self, save: bool = True):
        self.total_score = (self.auto_screen_score or 0) + (self.manual_adjustment or 0) + \
                           (self.test_score or 0) + (self.interview_score or 0)
        if save:
            self.save(update_fields=["total_score"])


class ApplicationEligibility(EligibilityCheck):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="eligibility")

    class Meta:
        db_table = "application_eligibility"


class ScreeningAction(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="screening_actions")
    auto_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    manual_adjustment = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    reason = models.TextField(blank=True)
    by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "screening_actions"


# ---------------------------------------------------------------------
# Tests / Interviews / Final Selection / Notifications
# ---------------------------------------------------------------------
class Test(models.Model):
    cycle = models.ForeignKey(RecruitmentCycle, on_delete=models.CASCADE, related_name="tests")
    name = models.CharField(max_length=120)
    instructions = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("100.00"))
    max_attempts = models.PositiveSmallIntegerField(default=1)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = ("cycle", "name")
        ordering = ["-opens_at"]
        db_table = "tests"

    def __str__(self): return f"{self.name} ({self.cycle})"

    def clean(self):
        if self.opens_at >= self.closes_at:
            raise ValidationError("Test opens_at must be before closes_at.")


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    points = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.00"))
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["order", "id"]
        db_table = "test_questions"

    def __str__(self): return f"Q{self.order} - {self.test.name}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=1000)
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = "test_choices"

    def __str__(self): return f"Choice for Q{self.question_id}"


class TestAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        SUBMITTED = "SUBMITTED", "Submitted"
        GRADED = "GRADED", "Graded"

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="test_attempts")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("test", "application")
        indexes = [models.Index(fields=["test", "application", "status"])]
        db_table = "test_attempts"

    def __str__(self): return f"{self.application_id} - {self.test.name} ({self.status})"


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    awarded_points = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("attempt", "question")
        db_table = "test_attempt_answers"


class InterviewSchedule(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        COMPLETED = "COMPLETED", "Completed"
        NO_SHOW = "NO_SHOW", "No Show"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    scheduled_at = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    panel_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_interviews")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]
        db_table = "interview_schedules"

    def __str__(self): return f"Interview for App#{self.application_id} at {self.scheduled_at}"


class InterviewScore(models.Model):
    schedule = models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE, related_name="scores")
    interviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="interview_scores")
    score = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("schedule", "interviewer")
        db_table = "interview_scores"


def offer_letter_path(instance: "FinalSelection", filename: str) -> str:
    return f"offers/{instance.application_id}/{filename}"

class FinalSelection(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="final_selection")
    rank = models.PositiveIntegerField(db_index=True)
    total_score_snapshot = models.DecimalField(max_digits=7, decimal_places=2)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="approved_selections")
    approved_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    offer_letter = models.FileField(
        upload_to=offer_letter_path, null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )

    class Meta:
        ordering = ["rank"]
        db_table = "final_selections"


class Notification(models.Model):
    class NType(models.TextChoices):
        INFO = "INFO", "Info"
        APPLICATION = "APPLICATION", "Application"
        SHORTLIST = "SHORTLIST", "Shortlist"
        TEST = "TEST", "Test"
        INTERVIEW = "INTERVIEW", "Interview"
        RESULT = "RESULT", "Result"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    ntype = models.CharField(max_length=12, choices=NType.choices, default=NType.INFO, db_index=True)
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    ref_model = models.CharField(max_length=60, blank=True)
    ref_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "is_read", "ntype"])]
        ordering = ["-created_at"]
        db_table = "notifications"

    def __str__(self): return f"{self.get_ntype_display()}: {self.title}"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        SHORTLIST = "SHORTLIST", "Shortlist"
        APPROVE = "APPROVE", "Approve"
        REJECT = "REJECT", "Reject"
        SCORE = "SCORE", "Score"
        EXPORT = "EXPORT", "Export"

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=12, choices=Action.choices, db_index=True)
    entity = models.CharField(max_length=80, help_text="Model name or domain entity")
    entity_id = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["action", "entity"]), models.Index(fields=["created_at"])]
        ordering = ["-created_at"]
        db_table = "audit_logs"


# ---------- Extended applicant details ----------
class AlternativeContact(models.Model):
    applicant = models.ForeignKey(
        "ApplicantProfile",
        on_delete=models.CASCADE,
        related_name="alt_contacts",
    )
    name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)

    class Meta: db_table = "applicant_alt_contact"


class ParentGuardian(models.Model):
    class Kind(models.TextChoices):
        FATHER = "FATHER", "Father"
        MOTHER = "MOTHER", "Mother"
        GUARDIAN = "GUARDIAN", "Guardian"

    applicant = models.ForeignKey("ApplicantProfile", on_delete=models.CASCADE, related_name="parents")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    is_alive = models.BooleanField(default=True)

    class Meta:
        db_table = "applicant_parents"
        unique_together = ("applicant", "kind")


class EducationRecord(models.Model):
    class Level(models.TextChoices):
        G10 = "G10", "Grade 10"
        G12 = "G12", "Grade 12"
        TERT_CERT = "TERT_CERT", "Tertiary Certificate"
        TERT_DIP = "TERT_DIP", "Tertiary Diploma"
        BACHELOR = "BACHELOR", "Bachelor"
        POSTGRAD = "POSTGRAD", "Postgraduate"

    applicant = models.ForeignKey("ApplicantProfile", on_delete=models.CASCADE, related_name="education")
    level = models.CharField(max_length=12, choices=Level.choices)
    institution = models.CharField(max_length=200, blank=True)
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    certificate_title = models.CharField(max_length=200, blank=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    english_grade = models.CharField(max_length=5, blank=True)
    mathematics_grade = models.CharField(max_length=5, blank=True)
    science_grade = models.CharField(max_length=5, blank=True)
    other_grade = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "applicant_education"
        ordering = ["level", "end_date", "id"]


class WorkHistory(models.Model):
    applicant = models.ForeignKey("ApplicantProfile", on_delete=models.CASCADE, related_name="work_history")
    employer = models.CharField(max_length=200)
    position = models.CharField(max_length=120, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    duties = models.TextField(blank=True)

    class Meta:
        db_table = "applicant_work_history"
        ordering = ["-start_date", "-end_date", "id"]


class Reference(models.Model):
    applicant = models.ForeignKey("ApplicantProfile", on_delete=models.CASCADE, related_name="references")
    name = models.CharField(max_length=150)
    position_title = models.CharField(max_length=120, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)

    class Meta: db_table = "applicant_references"

    def __str__(self): return f"{self.name} ({self.position_title})"


# ---------------------------------------------------------------------
# Eligibility helper & Signals
# ---------------------------------------------------------------------
def run_automated_eligibility(application: Application) -> "ApplicationEligibility":
    prof = application.applicant
    cycle = application.cycle

    age_ok = (prof.age is not None) and (cycle.min_age <= prof.age <= cycle.max_age)
    education_ok = prof.highest_education_level >= cycle.min_education_level

    def has_ok(doc_type: str) -> bool:
        try:
            d = prof.documents.get(doc_type=doc_type)
            return d.verify_status == Document.VerifyStatus.APPROVED
        except Document.DoesNotExist:
            return False

    medical_ok = has_ok(Document.DocType.MED_CLEAR)
    police_ok = has_ok(Document.DocType.POL_CLEAR)
    duplicates_ok = True

    passed = age_ok and education_ok and medical_ok and police_ok and duplicates_ok

    elig, _ = ApplicationEligibility.objects.update_or_create(
        application=application,
        defaults=dict(
            age_ok=age_ok,
            education_ok=education_ok,
            medical_ok=medical_ok,
            police_ok=police_ok,
            duplicates_ok=duplicates_ok,
            result=ApplicationEligibility.Status.PASS if passed else ApplicationEligibility.Status.FAIL,
            details={
                "age": prof.age,
                "min_age": cycle.min_age,
                "max_age": cycle.max_age,
                "edu_level": prof.highest_education_level,
                "min_edu_level": cycle.min_education_level,
            },
        ),
    )

    application.eligibility_passed = passed
    if not passed and not application.disqualification_reason:
        reasons = []
        if not age_ok: reasons.append("Age outside allowed range.")
        if not education_ok: reasons.append("Education level below requirement.")
        if not medical_ok: reasons.append("Medical clearance missing/not approved.")
        if not police_ok: reasons.append("Police clearance missing/not approved.")
        application.disqualification_reason = " ".join(reasons)
    application.save(update_fields=["eligibility_passed", "disqualification_reason"])
    return elig


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_profile_for_applicant(sender, instance: User, created: bool, **kwargs):
    if created and instance.role == User.Roles.APPLICANT:
        ApplicantProfile.objects.get_or_create(
            user=instance,
            defaults=dict(
                full_name=instance.get_full_name() or instance.username,
                dob=date(2000, 1, 1),
                gender=ApplicantProfile.Gender.OTHER,
                highest_education_level=ApplicantProfile.EducationLevel.G12,
                nid_number=None,
            ),
        )

@receiver(post_save, sender=TestAttempt)
def update_test_score_on_submit(sender, instance: "TestAttempt", **kwargs):
    if instance.status in (TestAttempt.Status.SUBMITTED, TestAttempt.Status.GRADED):
        app = instance.application
        app.test_score = instance.score
        app.recalc_total(save=True)

@receiver(post_save, sender=InterviewScore)
def update_interview_score_cache(sender, instance: "InterviewScore", **kwargs):
    schedule = instance.schedule
    app = schedule.application
    agg = schedule.scores.aggregate(avg=models.Avg("score"))
    app.interview_score = agg["avg"] or Decimal("0.00")
    app.recalc_total(save=True)
