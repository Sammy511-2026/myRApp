from django.db import migrations, models
from django.db.models import Q
import django.db.models.functions as dbfunc

def normalize_empty_nid_to_null(apps, schema_editor):
    ApplicantProfile = apps.get_model("recruitment", "ApplicantProfile")
    # After column allows NULL, convert any empty strings to NULL
    ApplicantProfile.objects.filter(nid_number="").update(nid_number=None)

class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0001_initial"),
    ]

    operations = [
        # 1) First, allow NULLs (and drop the old unique on the field if it existed)
        migrations.AlterField(
            model_name="applicantprofile",
            name="nid_number",
            field=models.CharField(max_length=30, null=True, blank=True),
        ),
        # 2) Now it's legal to write NULLs
        migrations.RunPython(normalize_empty_nid_to_null, migrations.RunPython.noop),
        # 3) Add conditional, case-insensitive uniqueness only when NID is present
        migrations.AddConstraint(
            model_name="applicantprofile",
            constraint=models.UniqueConstraint(
                dbfunc.Lower("nid_number"),
                name="uniq_nid_when_present_ci",
                condition=Q(nid_number__isnull=False) & ~Q(nid_number=""),
            ),
        ),
    ]
