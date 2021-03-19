from uuid import uuid4
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model


User = get_user_model()

# Create your models here.

class Room(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    users = models.ManyToManyField(User)

    created_date = models.DateTimeField(_('created date'), default=timezone.now)

    is_active = models.BooleanField(_('active'), default=False)


class MatchingRecord(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    game_name = models.CharField(_('game name'),max_length=255)
    number = models.IntegerField(_('number of users'), default=2)
    submission_time = models.DateTimeField(_('submission time'), default=timezone.now)

    is_active = models.BooleanField(_('is waiting for matching'), default=False)
    is_pending = models.BooleanField(_('is waiting for confirmation'), default=False)
    is_confirmed = models.BooleanField(_('is confirmed'), default=False)