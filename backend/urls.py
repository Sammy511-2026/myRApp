from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from recruitment.admin_site import rpngc_admin

admin.site.index_template = "admin/rpngc_index.html"
admin.site.login_template = "admin/rpngc_login.html"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("rpngc-admin/", rpngc_admin.urls),
    path("api/v1/", include("recruitment.api.urls")),
    path("", include(("recruitment.urls", "recruitment"), namespace="recruitment")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
