from django import forms
from .models import Velhinho

class VelhinhoForm(forms.ModelForm):
    class Meta:
        model = Velhinho
        # Usamos 'exclude' para o Lar não aparecer no formulário HTML, 
        # já que o preenchemos automaticamente na view.
        exclude = ['lar']