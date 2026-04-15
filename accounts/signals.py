from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_logged_in)
def _update_last_login_at(sender, request, user, **kwargs):
    User = get_user_model()
    User.objects.filter(pk=user.pk).update(last_login_at=timezone.now())

