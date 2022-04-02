""" Account form """
from django.contrib.auth.forms import (
    UserCreationForm, UsernameField, UserChangeForm, AuthenticationForm)
from django.forms.models import ModelForm
from django.forms import (
    CharField, EmailField, TextInput, EmailInput, PasswordInput)


from .models import User


class UserCreateForm(UserCreationForm):
    """ User creatino form """
    password1 = CharField(max_length=50, min_length=6, widget=PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'email')
        field_classes = {
            'username': UsernameField,
            'email': EmailField
        }
        widgets = {
            'username': TextInput(attrs={'id': 'id_username'}),
            'email': EmailInput(attrs={'id': 'id_email'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['password2']
        self.fields['username'].label = 'Username'
        self.fields['username'].widget.attrs['class'] = 'uk-input uk-form-width-large'
        self.fields['email'].label = 'Email'
        self.fields['email'].widget.attrs['class'] = 'uk-input uk-form-width-large'
        self.fields['password1'].label = 'Password'
        self.fields['password1'].widget.attrs['class'] = 'uk-input uk-form-width-large'
        self.fields['password1'].help_text = 'Make sure it\'s at least 6 characters.'

    def clean_email(self):
        email = self.cleaned_data['email']
        return email


class LoginForm(AuthenticationForm):
    """ Login form """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Username'
        self.fields['username'].widget.attrs['class'] = 'uk-input uk-form-width-large'
        self.fields['password'].label = 'Password'
        self.fields['password'].widget.attrs['class'] = 'uk-input uk-form-width-large'

    
    def non_field_errors(self):
        error_messages = super().non_field_errors()
        if error_messages:
            error_messages[0] = 'Incorrect Email address or Password'
        return error_messages



class CustomUserChangeForm(UserChangeForm):
    """ User settings change form """
    password = None

    class Meta:
        model = User
        fields = ('username', 'email')
        field_classes = {
            'username': UsernameField,
            'email': EmailField
        }
        widgets = {
            'username': TextInput(attrs={'id': 'id_username'}),
            'email': EmailInput(attrs={'id': 'id_email'}),
        }


class ProfileForm(ModelForm):
    """ Profile settings form """
    class Meta:
        model = User
        fields = ('icon_image',)