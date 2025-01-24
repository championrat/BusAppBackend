from rest_framework import permissions
from django.http import JsonResponse
from functools import wraps

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access the view.
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name='admin').exists()


class IsNormalUser(permissions.BasePermission):
    """
    Custom permission to only allow normal users to access the view.
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name='normal').exists()

class IsDriverUser(permissions.BasePermission):
    """
    Custom permission to only allow normal users to access the view.
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name='driver').exists()