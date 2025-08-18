# forms.py
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import UserProfile

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture',
            'phone_number',
            'department',
            'student_id',
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': '+254700000000'}),
            'department': forms.TextInput(attrs={'placeholder': 'e.g. Computer Science'}),
            'student_id': forms.TextInput(attrs={'placeholder': 'e.g. RGU2023001'}),
        }

class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'email_notifications',
            'sms_notifications',
            'push_notifications',
            'election_reminders',
            'results_announcements',
        ]
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={'class': 'switch-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'switch-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'switch-input'}),
            'election_reminders': forms.CheckboxInput(attrs={'class': 'switch-input'}),
            'results_announcements': forms.CheckboxInput(attrs={'class': 'switch-input'}),
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        
        validate_password(password2, self.user)
        
        return password2