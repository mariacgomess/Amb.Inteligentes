from django.urls import path
from . import views

urlpatterns=[
    path("",views.login_view, name="login"),
    path("mapa/",views.mapa, name="mapa"),
    path('adicionarvelhinho/', views.criar_idoso, name="novovelhinho"),
]