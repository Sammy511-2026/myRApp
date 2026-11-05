from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "recruitment"

urlpatterns = [
    path("", views.landing, name="landing"),

    # Auth
    path("login/", views.RoleBasedLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="recruitment:landing"), name="logout"),
    path("register/", views.register_view, name="register"),
    path("profile/edit/", views.applicant_profile_edit, name="profile_edit"),
    path("staff/profile/edit/", views.staff_profile_edit, name="staff_profile_edit"),
    path("locations/districts/", views.district_choices, name="district_choices"),

    # Applicant
    path("dashboard/", views.applicant_dashboard, name="applicant_dashboard"),
    path("profile/photo/", views.profile_photo_update, name="profile_photo_update"),

    # Application
    path("application/form/", views.application_form_view, name="application_form"),
    path("application/print/", views.application_print, name="application_print"),
    path("application/<int:pk>/delete/", views.application_delete, name="application_delete"),
    path("application/status/", views.application_status_view, name="application_status"),
    path("application/status/print/", views.application_status_print, name="application_status_print"),
    path("application/status/pdf/", views.application_status_pdf, name="application_status_pdf"),

    # Notifications
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("notifications/mark-all-seen/", views.notifications_mark_all_seen, name="mark_all_seen"),
    path("notifications/<int:pk>/seen/", views.notification_mark_seen, name="notification_seen"),

    # Staff
    path("staff/", views.staff_dashboard, name="staff_dashboard"),
    path("interview/", views.interview_schedule_list, name="interview_schedule_list"),
    path("tests/", views.tests_list, name="tests_list"),
    path("cycles/", views.cycles_list, name="cycles_list"),
    path("eligibility/", views.eligibility_list, name="eligibility_list"),
]
