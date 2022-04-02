""" Account views """
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.views import generic
from django.core.signing import dumps, loads, SignatureExpired, BadSignature
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string


from .forms import UserCreateForm, LoginForm, CustomUserChangeForm, ProfileForm


User = get_user_model()


# Create your views here.
class SignUpView(generic.CreateView):
    """
    User creation view\n
    Send authentication email to registered email address
    User's is_active param is still False here
    """
    form_class = UserCreateForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('chatrooms:index')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        self.object = user
        return HttpResponseRedirect(self.get_success_url())
    
    def form_invalid(self, form):
        messages.warning(self.request, 'form invalid!!')
        return super().form_invalid(form)


class Login(LoginView):
    """ Login view"""
    form_class = LoginForm
    template_name = 'accounts/login.html'


class Logout(LoginRequiredMixin, LogoutView):
    """Logout view"""
    pass


class ChangeSettingsView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    """ Change user settings view"""
    login_url = reverse_lazy('accounts:login')
    model = User
    form_class = CustomUserChangeForm
    template_name = 'accounts/settings.html'

    def test_func(self):
        current_user = self.request.user
        page_user = get_object_or_404(self.model, pk=self.kwargs['pk'])
        return current_user.pk == page_user.pk or current_user.is_superuser

    def get_success_url(self):
        return reverse_lazy('chatrooms:index')

    def form_valid(self, form):
        messages.success(self.request, 'saved successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.warning(self.request, 'not saved - alert!')
        return super().form_invalid(form)


class ProfileUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    """ Change user profile view """
    login_url = reverse_lazy('accounts:login')
    model = User
    form_class = ProfileForm
    template_name = 'accounts/profile_settings.html'

    def test_func(self):
        current_user = self.request.user
        page_user = get_object_or_404(self.model, pk=self.kwargs['pk'])
        return current_user.pk == page_user.pk or current_user.is_superuser

    def get_success_url(self):
        return reverse_lazy('chatrooms:index')

    def form_valid(self, form):
        messages.success(self.request, 'saved successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.warning(self.request, 'not saved - alert!')
        return super().form_invalid(form)