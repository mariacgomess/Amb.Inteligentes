import time
import requests
from geopy.distance import geodesic
import firebase_admin
from firebase_admin import credentials, db

# ==========================================
# CONFIGURAÇÕES
# ==========================================
TELEGRAM_TOKEN = "8304489726:AAFUvZpBJ5fJjMvJC07jC3bLbpfDKGqJWTA" 
TELEGRAM_CHAT_ID = "-5142514106" 

WEATHER_API_KEY = "4fa221e40fa0935eb478acfd7ea2c6f4" 

NOMES_UTENTES = {
    "utilizador_01": "Sara Pinto",
    "utilizador_02": "Helena Oliveira"
}

cred = credentials.Certificate(r"C:\Users\helen\Desktop\Mestrado\2Semestre\Ambientes Inteligentes\TPg\aims-tp1-firebase-adminsdk-fbsvc-7898f84f90.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://aims-tp1-default-rtdb.europe-west1.firebasedatabase.app/'
    })

FENCE_CENTER = [41.5607, -8.3972]
RADIUS_METERS = 500

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except:
        print("Erro ao ligar ao Telegram.")

def obter_clima_perigoso():
    """Verifica se está a chover em Braga"""
    lat, lon = FENCE_CENTER
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    try:
        res = requests.get(url).json()
        clima_main = res['weather'][0]['main'].lower()
        # Lista de condições consideradas perigosas para idosos na rua
        if any(keyword in clima_main for keyword in ["rain", "thunderstorm", "drizzle", "snow"]):
            return True, res['weather'][0]['description']
        return False, "Bom tempo"
    except:
        return False, "Erro API Clima"

# ==========================================
# MOTOR DE DECISÃO DINÂMICO
# ==========================================
def processar_dados():
    estados_anteriores = {} 
    ultimo_alerta_clima = {} # Para não bombardear com alertas de chuva

    print("A iniciar o Motor de Regras IoT Dinâmico...")

    while True:
        try:
            # Verifica clima global do lar (Braga)
            chuva_detetada, descricao_clima = obter_clima_perigoso()
            
            monitorizacao = db.reference('monitorizacao').get()
            
            if monitorizacao:
                for user_id, pastas in monitorizacao.items():
                    dados = pastas.get('atual')
                    if not dados or 'latitude' not in dados:
                        continue

                    # Conversão de coordenadas
                    try:
                        lat_raw = str(dados['latitude']).replace('{', '').replace('}', '')
                        lon_raw = str(dados['longitude']).replace('{', '').replace('}', '')
                        lat, lon = float(lat_raw), float(lon_raw)
                        passos_atuais = int(dados.get('passos', 0))
                    except: continue
                    
                    # Cálculos de Intensidade e Sedentarismo
                    dados_antigos = pastas.get('localizacao_tratada', {})
                    passos_anteriores = int(dados_antigos.get('passos', 0))
                    timestamp_anterior = dados_antigos.get('timestamp', time.time() - 5)
                    
                    delta_tempo_min = (time.time() - timestamp_anterior) / 60
                    delta_passos = passos_atuais - passos_anteriores
                    cadencia = delta_passos / delta_tempo_min if delta_tempo_min > 0 else 0
                    
                    if cadencia > 80: intensidade = "Alta (Pressa)"
                    elif cadencia > 20: intensidade = "Moderada (Passeio)"
                    elif cadencia > 0: intensidade = "Baixa (Lento)"
                    else: intensidade = "Repouso"
                        
                    minutos_inativo = dados_antigos.get('minutos_inativo', 0)
                    minutos_inativo = (minutos_inativo + round(delta_tempo_min, 2)) if cadencia == 0 else 0
                    status_ativo = "Ativo" if cadencia > 0 else "Inativo"
                    nome_real = NOMES_UTENTES.get(user_id, user_id)
                    
                    # Verificação de Distância (Geofence)
                    distancia = geodesic(FENCE_CENTER, (lat, lon)).meters
                    dentro = distancia <= RADIUS_METERS
                    estava_fora = estados_anteriores.get(user_id, False)

                    # --- LÓGICA DE ALERTAS TELEGRAM ---

                    # Alerta de Saída/Entrada de Zona
                    if not dentro and not estava_fora:
                        map_url = f"https://www.google.com/maps?q={lat},{lon}"
                        msg = (f"🚨 <b>ALERTA: Saída de Zona</b> 🚨\n\n"
                               f"O utente <b>{nome_real}</b> saiu do limite!\n"
                               f"📏 Distância: {round(distancia)}m\n"
                               f"📍 <a href='{map_url}'>Ver no Mapa</a>")
                        enviar_alerta_telegram(msg)
                        estados_anteriores[user_id] = True 

                    elif dentro and estava_fora:
                        msg = f"✅ <b>Regresso: {nome_real}</b>\nO utente voltou à zona segura."
                        enviar_alerta_telegram(msg)
                        estados_anteriores[user_id] = False

                    # Alerta Combinado: Fora de Zona + Chuva
                    if not dentro and chuva_detetada:
                        agora = time.time()
                        ultima_vez = ultimo_alerta_clima.get(user_id, 0)
                        
                        # Manda alerta se passarem 20 min (1200s) para não ser repetitivo
                        if agora - ultima_vez > 1200:
                            msg = (f"⚠️ <b>ALERTA AMBIENTAL: {nome_real}</b> ⚠️\n\n"
                                   f"O utente está fora da zona e detetamos <b>{descricao_clima}</b>!\n"
                                   f"Por favor, verifique a segurança do utente.")
                            enviar_alerta_telegram(msg)
                            ultimo_alerta_clima[user_id] = agora

                    # Grava dados tratados no Firebase
                    db.reference(f'monitorizacao/{user_id}/localizacao_tratada').set({
                        'distancia': round(distancia, 2),
                        'dentro': dentro,
                        'fora_de_zona': not dentro,
                        'lat_atual': lat, 'lon_atual': lon,
                        'passos': passos_atuais,
                        'status_ativo': status_ativo,
                        'intensidade': intensidade,
                        'minutos_inativo': minutos_inativo,
                        'chuva_no_local': chuva_detetada, 
                        'timestamp': time.time()
                    })

        except Exception as e:
            print(f"Erro geral no loop: {e}")

        time.sleep(10) #  10s para poupar pedidos à API

if __name__ == "__main__":
    processar_dados()