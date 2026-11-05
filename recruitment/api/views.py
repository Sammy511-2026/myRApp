from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from recruitment.models import (
    ApplicantProfile,
    Application,
    Notification,
    RecruitmentCycle,
)
from recruitment.api.permissions import IsApplicant
from recruitment.api.serializers import (
    ApplicantProfileSerializer,
    ApplicationSerializer,
    NotificationSerializer,
    RecruitmentCycleSerializer,
)


class ApplicantAPIView:
    permission_classes = (IsAuthenticated, IsApplicant)


class RecruitmentCycleListAPIView(ApplicantAPIView, generics.ListAPIView):
    serializer_class = RecruitmentCycleSerializer

    def get_queryset(self):
        return RecruitmentCycle.objects.filter(is_active=True).order_by(
            "-intake_year", "-start_date"
        )


class ApplicantProfileAPIView(ApplicantAPIView, generics.RetrieveUpdateAPIView):
    serializer_class = ApplicantProfileSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return get_object_or_404(ApplicantProfile, user=self.request.user)


class ApplicantApplicationListAPIView(ApplicantAPIView, generics.ListAPIView):
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        return Application.objects.filter(
            applicant__user=self.request.user
        ).select_related("cycle")


class ApplicantApplicationDetailAPIView(
    ApplicantAPIView, generics.RetrieveAPIView
):
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        return Application.objects.filter(
            applicant__user=self.request.user
        ).select_related("cycle")


class ApplicantNotificationListAPIView(ApplicantAPIView, generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class ApplicantNotificationDetailAPIView(
    ApplicantAPIView, generics.RetrieveUpdateAPIView
):
    serializer_class = NotificationSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class ApplicantNotificationReadAllAPIView(ApplicantAPIView, APIView):
    def post(self, request):
        updated_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return Response(
            {"updated": updated_count},
            status=status.HTTP_200_OK,
        )

