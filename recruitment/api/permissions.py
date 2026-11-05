from rest_framework.permissions import BasePermission

from recruitment.models import User


class IsApplicant(BasePermission):
    message = "Applicant access is required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Roles.APPLICANT
        )

