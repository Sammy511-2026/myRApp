from django.contrib import admin
from django.urls import path, include, re_path
from recruitment.admin_site import rpngc_admin
from recruitment.views import protected_media

admin.site.index_template = "admin/rpngc_index.html"
admin.site.login_template = "admin/rpngc_login.html"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("rpngc-admin/", rpngc_admin.urls),
    path("api/v1/", include("recruitment.api.urls")),
    re_path(r"^media/(?P<path>.+)$", protected_media, name="protected-media"),
    path("", include(("recruitment.urls", "recruitment"), namespace="recruitment")),
]
