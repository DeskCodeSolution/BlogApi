from rest_framework.permissions import BasePermission, SAFE_METHODS

class UpdateOwnPosts(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if request.method in SAFE_METHODS:
                return True

            return request.user.id == obj.author.id

        return False


