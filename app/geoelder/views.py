from django.shortcuts import render, redirect
from django.http import JsonResponse
from geopy.distance import geodesic
from django.contrib.auth import authenticate, login
from .models import Velhinho
from .forms import VelhinhoForm
from .firebase_service import get_dados_idoso
from django.contrib.auth.decorators import login_required
from geopy.distance import geodesic # Se não tiveres: pip install geopy
import requests

@login_required
def get_localizacoes(request):
    try:
        lar = request.user.lar
        idosos = Velhinho.objects.filter(lar=lar)
    except Exception:
        idosos = Velhinho.objects.all()
        lar = None

    resultado = []

    for i in idosos:
        dados = get_dados_idoso(f'utilizador_0{i.id}') 
        
        if dados:
            # === CORREÇÃO AQUI: Ler os nomes EXATOS que estão no Firebase ===
            lat = dados.get('lat_atual')
            lng = dados.get('lon_atual')
            distancia = dados.get('distancia', 0)
            passos = dados.get('passos', 0) # Não está na imagem, mas default para 0 protege o erro
            
            # Como o Firebase tem 'fora_de_zona: true', o 'dentro' é o inverso!
            fora_de_zona = dados.get('fora_de_zona', False)
            dentro = not fora_de_zona
            # ================================================================
        else:
            lat = lar.center_lat if lar else 41.5607
            lng = lar.center_lng if lar else -8.3972
            passos = 0
            distancia = 0
            dentro = True

        resultado.append({
            "id": i.id,
            "nome": i.nome,
            "lat": lat,
            "lng": lng,
            "distancia": distancia,    
            "dentro": dentro,          
            "passos": passos
        })

    return JsonResponse(resultado, safe=False)

from django.shortcuts import render

@login_required
def mapa(request):
    # 1. Obter Clima (OpenWeather)
    api_key = "4fa221e40fa0935eb478acfd7ea2c6f4"
    city_name = "Braga"
    url = f"http://api.openweathermap.org/data/2.5/weather?appid={api_key}&q={city_name}&units=metric&lang=pt"
    
    clima = {"temp": 0, "desc": "Sem Dados", "chuva": False, "icone_url": ""}
    try:
        res = requests.get(url).json()
        clima = {
            "temp": round(res["main"]["temp"]),
            "desc": res["weather"][0]["description"],
            # Deteta palavras de chuva em inglês ou português
            "chuva": any(palavra in res["weather"][0]["description"].lower() for palavra in ["rain", "drizzle", "chuva", "chuvisco", "trovoada"]),
            "humidade": res["main"]["humidity"],
            "vento": round(res["wind"]["speed"] * 3.6),
            "icone_url": f"http://openweathermap.org/img/wn/{res['weather'][0]['icon']}@2x.png"
        }
    except Exception as e: 
        print("Erro no OpenWeather:", e)

    # 2. Tentar obter o lar do utilizador logado de forma SEGURA
    try:
        lar_user = request.user.lar
        idosos = Velhinho.objects.filter(lar=lar_user)
    except Exception:
        # Se der erro (ex: é o Admin e não tem Lar), mostra todos para não crashar!
        lar_user = None
        idosos = Velhinho.objects.all()

    notificacoes = []

    # 3. Gerar Notificações dinâmicas
    for i in idosos:
        # Substitui pela tua função real que vai ler ao Firebase
        dados = get_dados_idoso(f'utilizador_0{i.id}') 
        
        if dados:
            passos = dados.get('passos', 0)
            lat = dados.get('latitude')
            lng = dados.get('longitude')
            
            # Usar os dados do lar do próprio idoso (protege contra o erro anterior)
            centro_lat = i.lar.center_lat if i.lar else 41.5607
            centro_lng = i.lar.center_lng if i.lar else -8.3972
            raio = i.lar.radius if i.lar else 500

            distancia = dados.get('distancia', 0)
            fora_de_zona = dados.get('fora_de_zona', False)

            # --- REGRAS DE NOTIFICAÇÃO ---
            
            # REGRA 1: FORA DE ZONA (Sempre que sair, independentemente do tempo!)
            if fora_de_zona:
                if clima.get("chuva"):
                    notificacoes.append({
                        "nivel": "danger",
                        "titulo": "PERIGO CRÍTICO",
                        "msg": f"{i.nome} está FORA da zona e está a CHOVER! Risco elevado.",
                        "icon": "fa-cloud-showers-heavy"
                    })
                else:
                    notificacoes.append({
                        "nivel": "danger",
                        "titulo": "ALERTA DE FUGA",
                        "msg": f"Atenção! {i.nome} saiu da área de segurança.",
                        "icon": "fa-exclamation-triangle"
                    })

            # REGRA 2: PASSOS A MENOS (Sedentarismo)
            if passos < (i.daily_step_goal * 0.1):
                notificacoes.append({
                    "nivel": "warning",
                    "titulo": "Baixa Atividade",
                    "msg": f"O(a) utente {i.nome} apresenta níveis de movimento muito baixos hoje.",
                    "icon": "fa-bed"
                })

            # REGRA 3: PASSOS A MAIS (Exaustão)
            if passos > (i.daily_step_goal * 1.5):
                notificacoes.append({
                    "nivel": "info",
                    "titulo": "Esforço Elevado",
                    "msg": f"{i.nome} já superou em 50% a meta de passos. Vigiar fadiga.",
                    "icon": "fa-running"
                })

    # REGRA 4: PREVENTIVA DE TEMPO (Aparece se estiver a chover)
    if clima["chuva"]:
        notificacoes.append({
            "nivel": "secondary",
            "titulo": "Aviso Meteorológico",
            "msg": "Tempo chuvoso na região. Recomendado evitar saídas ao exterior.",
            "icon": "fa-umbrella"
        })

    context = {
        'clima': clima,
        'notificacoes': notificacoes,
        'total_notificacoes': len(notificacoes)
    }
    
    return render(request, 'mapa.html', context)

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


from django.shortcuts import get_object_or_404

@login_required
def perfil_idoso(request, id_idoso):
    # Vai buscar o velhinho à base de dados ou dá erro 404 se não existir
    idoso = get_object_or_404(Velhinho, id=id_idoso)
    
    # Vamos também buscar os dados em tempo real ao Firebase para mostrar na página!
    dados_tempo_real = get_dados_idoso(f'utilizador_0{idoso.id}')
    
    contexto = {
        'idoso': idoso,
        'dados': dados_tempo_real
    }
    
    return render(request, 'perfil.html', contexto)