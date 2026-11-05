from django.db import migrations, models


REGION_PROVINCES = {
    "SOUTHERN": {
        "central",
        "gulf",
        "milne bay",
        "northern",
        "oro",
        "western",
        "national capital district",
        "ncd",
        "port moresby",
    },
    "HIGHLANDS": {
        "eastern highlands",
        "enga",
        "simbu",
        "chimbu",
        "southern highlands",
        "western highlands",
        "hela",
        "jiwaka",
    },
    "MOMASE": {
        "east sepik",
        "madang",
        "morobe",
        "west sepik",
        "sandaun",
    },
    "ISLANDS": {
        "east new britain",
        "new ireland",
        "west new britain",
        "manus",
        "north solomons",
        "bougainville",
        "autonomous region of bougainville",
        "arob",
    },
}


def assign_regions(apps, schema_editor):
    Province = apps.get_model("recruitment", "Province")
    for province in Province.objects.all().only("pk", "name"):
        normalized_name = province.name.strip().casefold()
        for region, names in REGION_PROVINCES.items():
            if normalized_name in names:
                Province.objects.filter(pk=province.pk).update(region=region)
                break


def unassign_regions(apps, schema_editor):
    Province = apps.get_model("recruitment", "Province")
    Province.objects.update(region="")


class Migration(migrations.Migration):
    dependencies = [
        ("recruitment", "0011_remove_recruitmentcycle_criteria"),
    ]

    operations = [
        migrations.AddField(
            model_name="province",
            name="region",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SOUTHERN", "Southern"),
                    ("HIGHLANDS", "Highlands"),
                    ("MOMASE", "Momase"),
                    ("ISLANDS", "Islands"),
                ],
                max_length=12,
            ),
        ),
        migrations.AlterModelOptions(
            name="province",
            options={
                "db_table": "geo_provinces",
                "ordering": ["region", "name"],
            },
        ),
        migrations.RunPython(assign_regions, unassign_regions),
    ]
