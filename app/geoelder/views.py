from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from .models import Velhinho
from .forms import VelhinhoForm
from .firebase_service import get_dados_idoso
from django.contrib.auth.decorators import login_required
from geopy.distance import geodesic # Se não tiveres: pip install geopy
import requests
from firebase_admin import db
from datetime import datetime
from datetime import date


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
            lat = dados.get('lat_atual')
            lng = dados.get('lon_atual')
            distancia = dados.get('distancia', 0)
            passos = dados.get('passos', 0)
            fora_de_zona = dados.get('fora_de_zona', False)
            dentro = not fora_de_zona
            
            # --- NOVO: Obter Clima Real para este Idoso ---
            # Chamamos a tua função enviando a lat/lng do Firebase
            clima_data = consultar_clima_dinamico(lat, lng) 
        else:
            lat = lar.center_lat if lar else 41.5607
            lng = lar.center_lng if lar else -8.3972
            passos = 0
            distancia = 0
            dentro = True
            clima_data = None

        # Montamos o objeto de clima para o JSON
        clima_json = {
            "temp": clima_data.get("temp") if clima_data else "--",
            "desc": clima_data.get("desc") if clima_data else "Sem dados",
            "icone_url": clima_data.get("icone_url") if clima_data else "",
            "humidade": clima_data.get("humidade") if clima_data else 0,
            "vento": clima_data.get("vento") if clima_data else 0,
            "cidade": clima_data.get("cidade_atual") if clima_data else "Desconhecido",
            "qualidade_ar": clima_data.get("qualidade_ar") if clima_data else "Boa"
        }

        resultado.append({
            "id": i.id,
            "nome": i.nome,
            "lat": lat,
            "lng": lng,
            "distancia": distancia,    
            "dentro": dentro,          
            "passos": passos,
            "clima": clima_json  # Enviamos o pacote de clima para o JS
        })

    return JsonResponse(resultado, safe=False)

def consultar_clima_dinamico(lat, lon):
    api_key = "4fa221e40fa0935eb478acfd7ea2c6f4"
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt"
    
    try:
        response = requests.get(url, timeout=3)
        x = response.json()

        if x["cod"] == 200:
            desc = x["weather"][0]["description"].lower() # Pegamos a descrição
            return {
                "temp": round(x["main"]["temp"]),
                "feels_like": round(x["main"]["feels_like"]),
                "humidade": x["main"]["humidity"],
                "vento": round(x["wind"]["speed"] * 3.6),
                "desc": desc,
                "icone_url": f"http://openweathermap.org/img/wn/{x['weather'][0]['icon']}@2x.png",
                "cidade_atual": x.get("name", "Localização Remota"),
                # ADICIONA ESTA LINHA ABAIXO:
                "chuva": any(p in desc for p in ["chuva", "rain", "chuvisco", "drizzle", "trovoada"])
            }
    except Exception as e:
        print(f"Erro no clima: {e}")
    return None

def mapa(request):
    try:
        lar_user = request.user.lar
        idosos = Velhinho.objects.filter(lar=lar_user)
    except:
        lar_user = None
        idosos = Velhinho.objects.all()

    # 1. Tentar obter o clima baseado na posição do PRIMEIRO idoso
    clima = {"temp": "--", "desc": "Sem Dados", "chuva": False} # Valor padrão
    
    
    if idosos.exists():
        primeiro_idoso = idosos.first()
        dados_fb = get_dados_idoso(f'utilizador_0{primeiro_idoso.id}')
        
        if dados_fb and 'lat_atual' in dados_fb:
            # CHAMADA DINÂMICA: Clima de onde o idoso está mesmo!
            clima_real = consultar_clima_dinamico(dados_fb['lat_atual'], dados_fb['lon_atual'])
            if clima_real:
                clima = clima_real

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

    # No final da função mapa:
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

import json # Adiciona isto no topo do ficheiro se não tiveres

@login_required
def perfil(request, id):
    idoso = get_object_or_404(Velhinho, id=id)
    
    # 1. Dados em Tempo Real
    ref_atual = db.reference(f'monitorizacao/utilizador_0{idoso.id}/atual').get() or {}
    ref_tratado = db.reference(f'monitorizacao/utilizador_0{idoso.id}/localizacao_tratada').get() or {}
    
    # Injetar dados vivos no objeto que vai para o HTML
    ref_tratado['hora_leitura'] = ref_atual.get('hora_leitura', "---")
    ref_tratado['status_ativo'] = ref_atual.get('status', "Inativo") # Novo campo real!

    # 2. Dados Históricos (Estatísticas)
    ref_semanal = db.reference(f'monitorizacao/utilizador_0{idoso.id}/estatisticas_semanais').get()
    
    passos_semana = [0, 0, 0, 0, 0, 0, 0]
    total_passos_semana = 0
    dias_com_dados = 0
    
    from datetime import date, datetime
    hoje = date.today()
    
    if ref_semanal:
        lista_dados = ref_semanal.values() if isinstance(ref_semanal, dict) else ref_semanal
        for item in lista_dados:
            if item and isinstance(item, dict) and 'data' in item:
                try:
                    data_registo = datetime.strptime(item['data'], '%Y-%m-%d').date()
                    diff = (hoje - data_registo).days
                    if 0 <= diff <= 6:
                        idx = 6 - diff
                        val = item.get('passos', 0)
                        passos_semana[idx] = val
                        total_passos_semana += val
                        if val > 0: dias_com_dados += 1
                except: pass

    # Cálculos Reais para o Perfil
    media_semanal = round(total_passos_semana / dias_com_dados) if dias_com_dados > 0 else 0
    recorde_semana = max(passos_semana)

    context = {
        'idoso': idoso,
        'dados': ref_tratado,
        'passos_semana': json.dumps(passos_semana),
        'media_semanal': media_semanal, # Manda para o HTML
        'recorde_semana': recorde_semana, # Manda para o HTML
        'total_semana': total_passos_semana
    }
    return render(request, 'perfil.html', context)