from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _

from .models import User


class CustomUserChangeForm(UserChangeForm):
    """ User settings change form """
    class Meta:
        model = User
        fields = '__all__'


class CustomUserCreationForm(UserCreationForm):
    """ User creation form """
    class Meta:
        model = User
        fields = '__all__'

class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('uuid', 'password')}),
        (_('Personal info'), {
            'fields': ('username', 'icon_image')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_guest', 'groups', 'user_permissions')
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'reg_date')
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )
    readonly_fields = ('uuid', 'last_login', 'reg_date')

    # form = CustomUserChangeForm
    # add_form = CustomUserCreationForm
    list_display = ('username', 'reg_date', 'last_login', 'is_active', 'is_staff', 'is_guest')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_guest', 'groups')
    search_fields = ('username',)
    ordering = ('username',)

admin.site.register(User, CustomUserAdmin)