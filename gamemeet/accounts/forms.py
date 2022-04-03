""" Account form """
from django.contrib.auth.forms import (
    UserCreationForm, UsernameField, UserChangeForm, AuthenticationForm)
from django.forms.models import ModelForm
from django.forms import (
    CharField, TextInput, PasswordInput)


from .models import User


class UserCreateForm(UserCreationForm):
    """ User creatino form """
    password1 = CharField(max_length=50, min_length=6, widget=PasswordInput)

    class Meta:
        model = User
        fields = ('username',)
        field_classes = {
            'username': UsernameField,
        }
        widgets = {
            'username': TextInput(attrs={'id': 'id_username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['password2']
        self.fields['username'].label = 'ユーザー名'
        self.fields['username'].widget.attrs['class'] = 'uk-input uk-form-width-large'
        self.fields['password1'].label = 'パスワード'
        self.fields['password1'].widget.attrs['class'] = 'uk-input uk-form-width-large'
        self.fields['password1'].help_text = 'パスワードは6文字以上'


class LoginForm(AuthenticationForm):
    """ Login form """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'ユーザー名'
        self.fields['username'].widget.attrs['class'] = 'uk-input uk-form-width-large'
        self.fields['username'].widget.attrs['placeholder'] = 'ユーザー名'
        self.fields['password'].label = 'パスワード'
        self.fields['password'].widget.attrs['class'] = 'uk-input uk-form-width-large'
        self.fields['password'].widget.attrs['placeholder'] = 'パスワード'

    def non_field_errors(self):
        error_messages = super().non_field_errors()
        if error_messages:
            error_messages[0] = 'Incorrect Username or Password'
        return error_messages


class CustomUserChangeForm(UserChangeForm):
    """ User settings change form """
    password = None

    class Meta:
        model = User
        fields = ('username',)
        field_classes = {
            'username': UsernameField,
        }
        widgets = {
            'username': TextInput(attrs={'id': 'id_username'}),
        }


class ProfileForm(ModelForm):
    """ Profile settings form """
    class Meta:
        model = User
        fields = ('username', 'icon_image')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'ユーザー名'
        self.fields['username'].widget.attrs['class'] = 'uk-input uk-form-width-large'
        self.fields['icon_image'].label = 'プロフィール画像'
