from django.urls import path
from . import views

urlpatterns=[
    path("",views.login_view, name="login"),
    path("mapa/",views.mapa, name="mapa"),
    path("api/localizacoes/", views.get_localizacoes, name="api_localizacoes"),
    path('adicionarvelhinho/', views.criar_idoso, name="novovelhinho"),
    path('perfil/<int:id_idoso>/', views.perfil_idoso, name='perfil_idoso'),
]
