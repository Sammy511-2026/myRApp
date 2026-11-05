# recruitment/apps.py
from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class RPNGCAdminConfig(AdminConfig):
    default = False
    default_site = "recruitment.admin_site.RPNGCAdminSite"

class RecruitmentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recruitment"
    verbose_name = "Recruitment"
