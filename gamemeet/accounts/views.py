""" Account views """
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpResponseBadRequest
from django.views import generic
from django.core.signing import dumps, loads, SignatureExpired, BadSignature
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
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
    # WARNING: Set email settings in settings.py
    form_class = UserCreateForm
    template_name = 'accounts/signup.html'

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        current_site = get_current_site(self.request)
        domain = current_site.domain
        context = {
            'protocol': self.request.scheme,
            'domain': domain,
            'token': dumps(user.pk),
            'user': user,
        }

        subject = render_to_string('accounts/mail_templates/signup/subject.txt', context)
        message = render_to_string('accounts/mail_templates/signup/message.txt', context)

        user.email_user(subject, message)
        return redirect('accounts:signup_done')


class SignUpDoneView(generic.TemplateView):
    """ Sign up done view"""
    template_name = 'accounts/signup_done.html'


class SignUpCompleteView(generic.TemplateView):
    """
    Sign up complete view\n
    User should click authentication url in sended email text
    User's is_active param become True
    """
    template_name = 'accounts/signup_complete.html'
    timeout_seconds = getattr(settings, 'ACTIVATION_TIMEOUT_SECONDS', 60*60*24)

    def get(self, request, **kwargs):
        token = kwargs.get('token')
        try:
            user_pk = loads(token, max_age=self.timeout_seconds)

        except SignatureExpired:
            return HttpResponseBadRequest()

        except BadSignature:
            return HttpResponseBadRequest()

        else:
            try:
                user = User.objects.get(pk=user_pk)
            except User.DoesNotExist:
                return HttpResponseBadRequest()
            else:
                if not user.is_active:
                    user.is_active = True
                    user.save()
                    return super().get(request, **kwargs)

        return HttpResponseBadRequest()


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