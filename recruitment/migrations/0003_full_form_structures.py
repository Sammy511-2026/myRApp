from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("recruitment", "0002_profile_nid_nullable_and_constraint"),
    ]

    operations = [
        migrations.CreateModel(
            name="AlternativeContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("relationship", models.CharField(blank=True, max_length=80)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("address", models.TextField(blank=True)),
                ("applicant", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="alt_contact", to="recruitment.applicantprofile")),
            ],
            options={"db_table": "applicant_alt_contact"},
        ),
        migrations.CreateModel(
            name="ParentGuardian",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("FATHER","Father"),("MOTHER","Mother"),("GUARDIAN","Guardian")], max_length=10)),
                ("name", models.CharField(max_length=150)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("address", models.TextField(blank=True)),
                ("is_alive", models.BooleanField(default=True)),
                ("applicant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="parents", to="recruitment.applicantprofile")),
            ],
            options={"db_table": "applicant_parents"},
        ),
        migrations.AlterUniqueTogether(
            name="parentguardian",
            unique_together={("applicant","kind")},
        ),
        migrations.CreateModel(
            name="EducationRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("level", models.CharField(choices=[("G10","Grade 10"),("G12","Grade 12"),("TERT_CERT","Tertiary Certificate"),("TERT_DIP","Tertiary Diploma"),("BACHELOR","Bachelor"),("POSTGRAD","Postgraduate")], max_length=12)),
                ("institution", models.CharField(blank=True, max_length=200)),
                ("province", models.CharField(blank=True, max_length=100)),
                ("start_year", models.PositiveIntegerField(blank=True, null=True)),
                ("end_year", models.PositiveIntegerField(blank=True, null=True)),
                ("certificate_title", models.CharField(blank=True, max_length=200)),
                ("gpa", models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ("english_grade", models.CharField(blank=True, max_length=5)),
                ("mathematics_grade", models.CharField(blank=True, max_length=5)),
                ("science_grade", models.CharField(blank=True, max_length=5)),
                ("other_grade", models.CharField(blank=True, max_length=20)),
                ("applicant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="education", to="recruitment.applicantprofile")),
            ],
            options={"db_table": "applicant_education","ordering":["level","end_year","id"]},
        ),
        migrations.CreateModel(
            name="WorkHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employer", models.CharField(max_length=200)),
                ("position", models.CharField(blank=True, max_length=120)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("duties", models.TextField(blank=True)),
                ("applicant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_history", to="recruitment.applicantprofile")),
            ],
            options={"db_table": "applicant_work_history","ordering":["-start_date","-end_date","id"]},
        ),
    ]
