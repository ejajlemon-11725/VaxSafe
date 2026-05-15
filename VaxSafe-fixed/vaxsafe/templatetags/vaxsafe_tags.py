# vaxsafe/templatetags/vaxsafe_tags.py
from django import template
from vaxsafe.models import Notification
register = template.Library()
@register.simple_tag(takes_context=True)
def get_unread_notifications(context):
    """
    Navbar-এ unread notification count দেখানোর জন্য।
    Usage: {% get_unread_notifications as unread_count %}
    """
    request = context.get('request')
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
    return 0
@register.simple_tag(takes_context=True)
def get_area_pending_count(context):

    request = context.get('request')
    if not (request and request.user.is_authenticated and
            (request.user.is_staff or request.user.is_superuser)):
        return 0
    try:
        from vaxsafe.models import AreaAdmin, VaccineRequest
        aa = request.user.area_admin  # ✅ correct related_name
        if request.user.is_superuser:
            return VaccineRequest.objects.filter(status='Pending').count()
        return VaccineRequest.objects.filter(
            assigned_admin=request.user, status='Pending'
        ).count()
    except Exception:
        return 0