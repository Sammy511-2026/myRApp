# recruitment/migrations/00XX_create_reference.py
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0001_initial"),  # <-- change to your last migration name
    ]

    operations = [
        migrations.CreateModel(
            name="Reference",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("position_title", models.CharField(blank=True, max_length=120)),
                ("phone_number", models.CharField(blank=True, max_length=50)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("applicant",
                 models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="references",
                    to="recruitment.applicantprofile", )
                ),
            ],
            options={
                "db_table": "applicant_references",
            },
        ),
    ]
