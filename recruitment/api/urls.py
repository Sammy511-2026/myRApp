from django.urls import path

from recruitment.api import views

app_name = "api"

urlpatterns = [
    path("cycles/", views.RecruitmentCycleListAPIView.as_view(), name="cycles"),
    path("me/profile/", views.ApplicantProfileAPIView.as_view(), name="profile"),
    path(
        "me/applications/",
        views.ApplicantApplicationListAPIView.as_view(),
        name="applications",
    ),
    path(
        "me/applications/<int:pk>/",
        views.ApplicantApplicationDetailAPIView.as_view(),
        name="application-detail",
    ),
    path(
        "me/notifications/",
        views.ApplicantNotificationListAPIView.as_view(),
        name="notifications",
    ),
    path(
        "me/notifications/read-all/",
        views.ApplicantNotificationReadAllAPIView.as_view(),
        name="notifications-read-all",
    ),
    path(
        "me/notifications/<int:pk>/",
        views.ApplicantNotificationDetailAPIView.as_view(),
        name="notification-detail",
    ),
]

