import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- Security ---
DEVELOPMENT_SECRET_KEY = "django-insecure-local-development-key-change-me"
SECRET_KEY = os.getenv("SECRET_KEY", DEVELOPMENT_SECRET_KEY)
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
if not DEBUG and SECRET_KEY == DEVELOPMENT_SECRET_KEY:
    raise ImproperlyConfigured("Set a unique SECRET_KEY in the environment before running with DEBUG=False.")
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")]

# Useful for local dev with 127.0.0.1/localhost
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

INSTALLED_APPS = [
    "jazzmin",  # keep first
    "recruitment.apps.RPNGCAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd-party
    "rest_framework",
    "django_extensions",
    # local
    "recruitment.apps.RecruitmentConfig",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

# --- Database ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "RPNGC"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

# --- Auth / redirects (namespaced) ---
AUTH_USER_MODEL = "recruitment.User"
LOGIN_URL = "recruitment:login"
LOGIN_REDIRECT_URL = "recruitment:applicant_form"  # role-based view will override when appropriate
LOGOUT_REDIRECT_URL = "recruitment:landing"

# --- Static & media ---
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]       # dev/global static
STATIC_ROOT = BASE_DIR / "static_root"         # collectstatic target

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Recruitment policy knobs ---
RECRUITMENT_REQUIRED_DOCS = [
    "G12_CERT", "BIRTH_CERT", "NID_PASSPORT",
    "MED_CLEAR", "POL_CLEAR", "CHAR_REF",
]
RECRUITMENT_DOCS_MUST_BE_APPROVED = True
RECRUITMENT_ENFORCE_AGE_EDU = True

JAZZMIN_SETTINGS = {
    "site_title": "RPNGC Admin",
    "site_header": "Royal Papua New Guinea Constabulary",
    "site_brand": "RPNGC Recruitment",
    "welcome_sign": "Welcome to RPNGC Recruitment Admin",
    "site_logo": "recruitment/images/Logo.png",
    "login_logo": "recruitment/images/Logo.png",
    "site_icon": "recruitment/images/Logo.png",
    "copyright": "© 2026 Royal Papua New Guinea Constabulary",
    "site_footer": "Internal system — for authorized staff only.",
    "site_url": "/staff/",

    # Keep high-use workflow pages at the top; the custom JS groups them visually.
    "order_with_respect_to": [
        "recruitment.Application",
        "recruitment.RecruitmentCycle",
        "recruitment.ApplicationEligibility",
        "recruitment.ScreeningAction",
        "recruitment.ApplicantProfile",
        "recruitment.Document",
        "recruitment.AlternativeContact",
        "recruitment.ParentGuardian",
        "recruitment.EducationRecord",
        "recruitment.WorkHistory",
        "recruitment.Reference",
        "recruitment.Test",
        "recruitment.Question",
        "recruitment.Choice",
        "recruitment.TestAttempt",
        "recruitment.AttemptAnswer",
        "recruitment.InterviewSchedule",
        "recruitment.InterviewScore",
        "recruitment.FinalSelection",
        "recruitment.Notification",
        "recruitment.AuditLog",
        "recruitment.Province",
        "recruitment.District",
        "auth.User",
    ],

    "hide_apps": [],
    "hide_models": [
        "recruitment.ApplicationEligibility",
        "recruitment.ScreeningAction",
        "recruitment.ApplicantProfile",
        "recruitment.Document",
        "recruitment.AlternativeContact",
        "recruitment.ParentGuardian",
        "recruitment.EducationRecord",
        "recruitment.WorkHistory",
        "recruitment.Reference",
    ],

    # Icons (Lucide/FontAwesome supported by Jazzmin)
    "icons": {
        "recruitment.ApplicantProfile": "fas fa-user",
        "recruitment.Application": "fas fa-clipboard-list",
        "recruitment.RecruitmentCycle": "fas fa-calendar-alt",
        "recruitment.Document": "fas fa-file",
        "recruitment.Test": "fas fa-check-square",
        "recruitment.Question": "fas fa-question",
        "recruitment.TestAttempt": "fas fa-laptop-code",
        "recruitment.InterviewSchedule": "fas fa-users",
        "recruitment.InterviewScore": "fas fa-star-half-alt",
        "recruitment.FinalSelection": "fas fa-award",
        "recruitment.Notification": "fas fa-bell",
        "recruitment.AuditLog": "fas fa-shield-alt",
        "recruitment.Province": "fas fa-map-marked-alt",
        "recruitment.District": "fas fa-map-marker-alt",
        "auth.User": "fas fa-user-cog",
    },

    # Branded action buttons
    "button_classes": {
        "add": "btn btn-primary",
        "save": "btn btn-primary",
        "delete": "btn btn-danger",
    },

    # Custom assets
    "custom_css": "recruitment/css/rpngc_admin.css",
    "custom_js": "recruitment/js/admin_overrides.js",

    # Sidebar & search
    "show_sidebar": True,
    "navigation_expanded": True,
    "search_model": "recruitment.ApplicantProfile",  # quick search focus
}
JAZZMIN_SETTINGS["show_ui_builder"] = False

# Compact spacing with the RPNGC navy and gold palette applied by custom CSS.
JAZZMIN_UI_TWEAKS = {
    "theme": "minty",  # base — we override colors via CSS
    "navbar_small_text": True,
    "footer_small_text": True,
    "sidebar_fixed": True,
    "sidebar_nav_small_text": True,
    "sidebar_dark": True,
    "brand_small_text": False,
    "actions_sticky_top": True,
    "default_theme_mode": "light",
}