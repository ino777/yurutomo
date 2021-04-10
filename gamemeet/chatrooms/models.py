from uuid import uuid4
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model


User = get_user_model()

# Create your models here.

class Tag(models.Model):
    name = models.CharField(_('tag name'), max_length=255)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def clean(self):
        """
        name から空白をなくす
        """
        if self.name:
            self.name = "".join(self.name.split())

class Topic(models.Model):
    name = models.CharField(_('topic name'), max_length=255)
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def clean(self):
        """
        name から空白をなくす
        """
        if self.name:
            self.name = "".join(self.name.split())

class Room(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    users = models.ManyToManyField(User)

    created_date = models.DateTimeField(_('created date'), default=timezone.now)

    is_active = models.BooleanField(_('active'), default=False)


class MatchingRecord(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=True)
    number = models.IntegerField(_('number of users'), default=2)
    submission_time = models.DateTimeField(_('submission time'), default=timezone.now)

    is_active = models.BooleanField(_('is waiting for matching'), default=False)
    is_pending = models.BooleanField(_('is waiting for confirmation'), default=False)
    is_confirmed = models.BooleanField(_('is confirmed'), default=False)