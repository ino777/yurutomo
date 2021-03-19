""" Account model """
from uuid import uuid4
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill


# Default user icon image ( /media/DEFAULT_USER_ICON_IMAGE )
DEFAULT_USER_ICON_IMAGE = 'default-user-icon.png'

# Create your models here.
class UserManager(BaseUserManager):
    """ User manager """
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        if not email:
            raise ValueError('The given email must be set.')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """ User model """
    username_validator = UnicodeUsernameValidator()

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    username = models.CharField(
        _('username'),
        max_length=20,
        validators=[username_validator],
    )
    email = models.EmailField(
        _('email address'),
        max_length=100,
        unique=True,
        error_messages={
            'unique': _('This email address is already registered in other account')
        }
    )

    icon_image = ProcessedImageField(
        upload_to=settings.USER_ICON_UPLOAD_DIR,
        processors=[ResizeToFill(200, 200)],
        format='JPEG',
        options={'quality': 60},
        default=DEFAULT_USER_ICON_IMAGE
    )

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
    )

    reg_date = models.DateTimeField(_('registration date'), default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user"""
        send_mail(subject, message, from_email, [self.email], **kwargs)