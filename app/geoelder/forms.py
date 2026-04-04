from django import forms
from .models import Velhinho

class VelhinhoForm(forms.ModelForm):
    class Meta:
        model = Velhinho
        # é utilizado 'exclude' para o Lar não aparecer no formulário HTML, já que é preenchido automaticamente na view.
        exclude = ['lar']