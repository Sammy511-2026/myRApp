"""
Seed PNG provinces and districts from the Open Admin Data dataset.

Source: https://github.com/open-admin-data/papua-new-guinea-administrative-divisions
License: CC-BY-4.0
The province/district records are adapted from that dataset; regional groupings
are assigned here according to Papua New Guinea's four regions.
"""

from django.db import migrations


PROVINCES = (
    ("PG20", "Autonomous Region of Bougainville", "ISLANDS"),
    ("PG03", "Central Province", "SOUTHERN"),
    ("PG10", "Chimbu (Simbu) Province", "HIGHLANDS"),
    ("PG18", "East New Britain Province", "ISLANDS"),
    ("PG14", "East Sepik Province", "MOMASE"),
    ("PG11", "Eastern Highlands Province", "HIGHLANDS"),
    ("PG08", "Enga Province", "HIGHLANDS"),
    ("PG02", "Gulf Province", "SOUTHERN"),
    ("PG21", "Hela Province", "HIGHLANDS"),
    ("PG22", "Jiwaka Province", "HIGHLANDS"),
    ("PG13", "Madang Province", "MOMASE"),
    ("PG16", "Manus Province", "ISLANDS"),
    ("PG05", "Milne Bay Province", "SOUTHERN"),
    ("PG12", "Morobe Province", "MOMASE"),
    ("PG04", "National Capital District", "SOUTHERN"),
    ("PG17", "New Ireland Province", "ISLANDS"),
    ("PG06", "Northern (Oro) Province", "SOUTHERN"),
    ("PG07", "Southern Highlands Province", "HIGHLANDS"),
    ("PG19", "West New Britain Province", "ISLANDS"),
    ("PG15", "West Sepik (Sandaun) Province", "MOMASE"),
    ("PG09", "Western Highlands Province", "HIGHLANDS"),
    ("PG01", "Western Province", "SOUTHERN"),
)

DISTRICTS = {
    "PG20": ("Central Bougainville", "North Bougainville", "South Bougainville"),
    "PG03": ("Abau", "Goilala", "Kairuku - Hiri", "Rigo"),
    "PG10": (
        "Chuave", "Gumine", "Karimui/Nomane", "Kerowagi",
        "Kundiawa/Gembogl", "Sina Sina Yonggomugl",
    ),
    "PG18": ("Gazelle", "Kokopo", "Pomio", "Rabaul"),
    "PG14": (
        "Ambunti/Drekikier", "Angoram", "Maprik", "Wewak",
        "Wosera Gawi", "Yangoru Saussia",
    ),
    "PG11": (
        "Daulo", "Goroka", "Henganofi", "Kainanatu",
        "Lufa", "Obura/Wonenara", "Okapa", "Unggai/Benna",
    ),
    "PG08": ("Kandep", "Kompiam", "Lagaip/Pogera", "Wabag", "Wapenamanda"),
    "PG02": ("Kerema", "Kikori"),
    "PG21": ("Komo/Magarima", "Koroba/Kopiago", "Tari/Pori"),
    "PG22": ("Anglimp/South Waghi", "Jimi", "North Waghi"),
    "PG13": (
        "Bogia", "Madang", "Middle Ramu", "Rai Coast",
        "Sumkar", "Usino Bundi",
    ),
    "PG16": ("Manus",),
    "PG05": ("Alotau", "Esa'ala", "Kiriwina-Goodenough", "Samarai-Murua"),
    "PG12": (
        "Bulolo", "Finschafen", "Huon", "Kabwum", "Lae",
        "Markham", "Menyamya", "Nawae", "Tawae/Siassi",
    ),
    "PG04": ("National Capital District",),
    "PG17": ("Kavieng", "Namatanai"),
    "PG06": ("Ijivitari", "Sohe"),
    "PG07": (
        "Ialibu/Pangia", "Imbonggu", "Kagua/Erave",
        "Mendi/Munihu", "Nipa/Kutubu",
    ),
    "PG19": ("Kandrian/Gloucester", "Talasea"),
    "PG15": ("Aitape/Lumi", "Nuku", "Telefomin", "Vanimo/Green River"),
    "PG09": ("Dei", "Mt Hagen", "Mul/Baiyer", "Tambul/Nebilyer"),
    "PG01": ("Middle Fly", "North Fly", "South Fly"),
}


def seed_geography(apps, schema_editor):
    Province = apps.get_model("recruitment", "Province")
    District = apps.get_model("recruitment", "District")
    database = schema_editor.connection.alias

    provinces_by_code = {}
    for code, name, region in PROVINCES:
        province, _ = Province.objects.using(database).get_or_create(
            name=name,
            defaults={"code": code, "region": region},
        )
        if province.region != region:
            Province.objects.using(database).filter(pk=province.pk).update(region=region)
        provinces_by_code[code] = province

    for code, district_names in DISTRICTS.items():
        province = provinces_by_code[code]
        District.objects.using(database).bulk_create(
            [
                District(province_id=province.pk, name=name)
                for name in district_names
            ],
            ignore_conflicts=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("recruitment", "0012_province_region"),
    ]

    operations = [
        migrations.RunPython(seed_geography, migrations.RunPython.noop),
    ]
