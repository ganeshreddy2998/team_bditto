from rest_framework.permissions import BasePermission

class PartiallyBlockedPermission(BasePermission):
    """
    Global permission check for partially blocked.
    """

    message = "User is not authorized to perform this request."

    def has_permission(self, request, view):
        try:
            user = request.user
            if user.status == 'Activated':
                return True
            return False
        except:
            return False