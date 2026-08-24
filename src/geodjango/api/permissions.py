from rest_framework.permissions import BasePermission


class IsEditor(BasePermission):
    message = 'Se requiere rol de editor para esta acción.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name='editor').exists()
            )
        )
