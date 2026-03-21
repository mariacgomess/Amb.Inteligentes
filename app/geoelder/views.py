from django.shortcuts import render, redirect
from django.http import JsonResponse
from geopy.distance import geodesic
from django.contrib.auth import authenticate, login
from .models import Velhinho
from .forms import VelhinhoForm
from .firebase_service import get_dados_idoso


def get_localizacoes(request):
    lar = request.user.lar
    idosos = Velhinho.objects.filter(lar=lar)

    resultado = []

    for i in idosos:
        dados = get_dados_idoso(f'utilizador_{i.id}')
        
        if not dados:
            continue
        
        lat = dados['latitude']
        lng = dados['longitude']
        passos = dados.get('passos', 0)

        distancia = geodesic(
            (i.center_lat, i.center_lng),
            (lat, lng)
        ).meters

        dentro = distancia <= i.radius

        resultado.append({
            "id": i.id,
            "nome": i.nome,
            "lat": lat,
            "lng": lng,
            "passos": passos,
            "distancia": round(distancia, 2),
            "dentro": dentro
        })

    return JsonResponse(resultado, safe=False)

from django.shortcuts import render

def mapa(request):
    return render(request, 'mapa.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            return redirect('/mapa/')
    
    return render(request, 'login.html')

def criar_idoso(request):
    if request.method == 'POST':
        form = VelhinhoForm(request.POST)
    if form.is_valid():
        idoso = form.save(commit=False)
        idoso.lar = request.user.lar
        idoso.save()
    else:
        form = VelhinhoForm()
    
    return render(request, 'criar_idoso.html', {'form': form})