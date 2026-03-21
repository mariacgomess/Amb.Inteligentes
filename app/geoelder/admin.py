from django.contrib import admin
from . models import Velhinho, Lar, Localizacao
# Register your models here.
admin.site.regsiter(Velhinho)
admin.site.register(Lar)
admin.site.register(Localizacao)