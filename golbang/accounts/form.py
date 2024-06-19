from django import forms
from .models import User

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['phone_number', 'address', 'dob', 'handicap', 'student_id']
