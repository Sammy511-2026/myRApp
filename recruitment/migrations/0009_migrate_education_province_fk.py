from django.db import migrations, models
import django.db.models.deletion

def forwards(apps, schema_editor):
    EducationRecord = apps.get_model("recruitment", "EducationRecord")
    Province = apps.get_model("recruitment", "Province")

    # Build quick lookup by normalized name/code
    name_map = {}
    for p in Province.objects.all():
        if p.name:
            name_map[p.name.strip().lower()] = p.id
        if p.code:
            name_map[p.code.strip().lower()] = p.id

    # Best-effort copy/convert old text to FK
    for rec in EducationRecord.objects.all():
        raw = (rec.province or "").strip()
        if not raw:
            continue
        key = raw.lower()
        pid = name_map.get(key)
        if not pid:
            # try exact name match ignoring case
            m = Province.objects.filter(name__iexact=raw).first()
            if not m:
                # try partial contains as a last resort
                m = Province.objects.filter(name__icontains=raw).first()
            pid = m.id if m else None
        if pid:
            # write directly to *_id avoids extra fetch
            setattr(rec, "province_fk_id", pid)
            rec.save(update_fields=["province_fk_id"])

def backwards(apps, schema_editor):
    EducationRecord = apps.get_model("recruitment", "EducationRecord")
    # On reverse, write province name back into the text column
    for rec in EducationRecord.objects.select_related("province_fk").all():
        val = rec.province_fk.name if getattr(rec, "province_fk_id", None) else ""
        setattr(rec, "province", val)
        rec.save(update_fields=["province"])

class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0008_alter_educationrecord_province_and_more"),
    ]

    operations = [
        # 1) add a temporary FK column
        migrations.AddField(
            model_name="educationrecord",
            name="province_fk",
            field=models.ForeignKey(
                to="recruitment.province",
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
            ),
        ),
        # 2) copy data from the old text column into the FK
        migrations.RunPython(forwards, backwards),
        # 3) drop old text column and rename FK to 'province'
        migrations.RemoveField(
            model_name="educationrecord",
            name="province",
        ),
        migrations.RenameField(
            model_name="educationrecord",
            old_name="province_fk",
            new_name="province",
        ),
    ]
