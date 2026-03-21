from django import forms
from .models import Velhinho

class VelhinhoForm(forms.ModelForm):
    class Meta:
        model = Velhinho
        fields = '__all__'