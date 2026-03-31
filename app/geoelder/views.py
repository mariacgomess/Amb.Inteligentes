from django.shortcuts import render, redirect
from django.http import JsonResponse
from geopy.distance import geodesic
from django.contrib.auth import authenticate, login
from .models import Velhinho
from .forms import VelhinhoForm
from .firebase_service import get_dados_idoso
from django.contrib.auth.decorators import login_required
from geopy.distance import geodesic # Se não tiveres: pip install geopy

@login_required
def get_localizacoes(request):
    try:
        # 1. Tentar obter o lar do utilizador logado
        lar = request.user.lar
        idosos = Velhinho.objects.filter(lar=lar)
    except Exception:
        # 2. Se o user (ex: admin) não tiver Lar, mostra todos para não ficar vazio
        idosos = Velhinho.objects.all()
        lar = None

    resultado = []

    for i in idosos:
        # 3. Tentar ir ao Firebase buscar dados reais
        # Substitui pela tua função real de buscar ao Firebase
        dados = get_dados_idoso(f'utilizador_0{i.id}') 
        
        if dados:
            lat = dados.get('latitude')
            lng = dados.get('longitude')
            passos = dados.get('passos', 0)
        else:
            # 4. Se não houver dados no Firebase, usamos a posição do Lar
            # Assim a bolinha aparece no mapa e não fica invisível
            lat = lar.center_lat if lar else 41.5607
            lng = lar.center_lng if lar else -8.3972
            passos = 0

        # 5. Calcular se está dentro ou fora
        distancia = 0
        dentro = True
        
        if lar and lat and lng:
            distancia = geodesic((lar.center_lat, lar.center_lng), (lat, lng)).meters
            dentro = distancia <= lar.radius

        resultado.append({
            "id": i.id,
            "nome": i.nome,
            "lat": lat,
            "lng": lng,
            "distancia": round(distancia, 2),
            "dentro": dentro,
            "passos": passos
        })

    return JsonResponse(resultado, safe=False)

from django.shortcuts import render

def mapa(request):
    return render(request, 'mapa.html')

from django.contrib import messages  # Importante importar isto!

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('/mapa/')
        else:
            # Aqui é onde "disparas" o aviso
            messages.error(request, "Utilizador ou password incorretos. Tenta de novo!")
    
    return render(request, 'login.html')

def criar_idoso(request):
    if request.method == 'POST':
        form = VelhinhoForm(request.POST)
        if form.is_valid():
            idoso = form.save(commit=False)
            # Isto associa o velhinho ao Lar do utilizador que está logado
            idoso.lar = request.user.lar 
            idoso.save()
            return redirect('mapa') # Redireciona de volta para o mapa após salvar
    else:
        # Se entrar na página pela primeira vez (GET), cria o form vazio
        form = VelhinhoForm()
    
    # Este return tem de estar fora do 'if' e do 'else' para ser sempre executado
    return render(request, 'novovelhinho.html', {'form': form})