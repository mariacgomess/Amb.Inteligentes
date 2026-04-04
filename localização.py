import time
import requests
from geopy.distance import geodesic
import firebase_admin
from firebase_admin import credentials, db

print("A iniciar o Motor de Regras IoT Dinâmico...")

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
TELEGRAM_TOKEN = "8304489726:AAFUvZpBJ5fJjMvJC07jC3bLbpfDKGqJWTA" 
TELEGRAM_CHAT_ID = "-5142514106" 

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

def enviar_alerta_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except:
        print("Erro ao ligar ao Telegram.")

# ==========================================
# 4. MOTOR DE DECISÃO DINÂMICO
# ==========================================
def processar_dados():
    estados_anteriores = {} 

    while True:
        try:
            monitorizacao = db.reference('monitorizacao').get()
            
            if monitorizacao:
                for user_id, pastas in monitorizacao.items():
                    dados = pastas.get('atual')
                    if not dados or 'latitude' not in dados:
                        continue

                    try:
                        lat_raw = str(dados['latitude']).replace('{', '').replace('}', '')
                        lon_raw = str(dados['longitude']).replace('{', '').replace('}', '')
                        
                        lat = float(lat_raw)
                        lon = float(lon_raw)
                        passos_atuais = int(dados.get('passos', 0))
                    except (ValueError, TypeError) as e:
                        print(f"Erro ao converter coordenadas do {user_id}: {e}")
                        continue
                    
                    # --- NOVO: LÓGICA DE INTENSIDADE E SEDENTARISMO ---
                    dados_antigos = pastas.get('localizacao_tratada', {})
                    passos_anteriores = int(dados_antigos.get('passos', 0))
                    timestamp_anterior = dados_antigos.get('timestamp', time.time() - 5)
                    
                    # Variação de tempo em minutos para cálculo de cadência
                    delta_tempo_min = (time.time() - timestamp_anterior) / 60
                    delta_passos = passos_atuais - passos_anteriores
                    
                    # Cálculo de Cadência (passos por minuto)
                    cadencia = delta_passos / delta_tempo_min if delta_tempo_min > 0 else 0
                    
                    # Classificação da Intensidade
                    if cadencia > 80:
                        intensidade = "Alta (Pressa)"
                    elif cadencia > 20:
                        intensidade = "Moderada (Passeio)"
                    elif cadencia > 0:
                        intensidade = "Baixa (Lento)"
                    else:
                        intensidade = "Repouso"
                        
                    # Contador de Sedentarismo (minutos acumulados sem passos)
                    minutos_inativo = dados_antigos.get('minutos_inativo', 0)
                    if cadencia == 0:
                        minutos_inativo += round(delta_tempo_min, 2)
                    else:
                        minutos_inativo = 0 # Reset se houver movimento
                    
                    # status_ativo para o badge do site
                    status_ativo = "Ativo" if cadencia > 0 else "Inativo"
                    
                    # --- NOME REAL PARA O TELEGRAM ---
                    nome_real = NOMES_UTENTES.get(user_id, user_id)
                    
                    # 2. Cálculo de Distância
                    distancia = geodesic(FENCE_CENTER, (lat, lon)).meters
                    dentro = distancia <= RADIUS_METERS
                    estava_fora = estados_anteriores.get(user_id, False)

                    # 3. Alertas Telegram
                    if not dentro and not estava_fora:
                        map_url = f"https://www.google.com/maps?q={lat},{lon}"
                        msg = (f"🚨 <b>ALERTA: Saída de Zona</b> 🚨\n\n"
                               f"O utente <b>{nome_real}</b> saiu do limite!\n"
                               f"📏 Distância: {round(distancia)}m\n"
                               f"📍 <a href='{map_url}'>Ver no Mapa</a>")
                        enviar_alerta_telegram(msg)
                        estados_anteriores[user_id] = True 
                        print(f"🚨 Alerta enviado para {nome_real}")

                    elif dentro and estava_fora:
                        msg = f"✅ <b>Regresso: {nome_real}</b>\nO utente voltou à zona segura."
                        enviar_alerta_telegram(msg)
                        estados_anteriores[user_id] = False
                        print(f"✅ Regresso registado para {nome_real}")

                    # 4. Grava os dados TRATADOS (Agora com métricas de saúde)
                    db.reference(f'monitorizacao/{user_id}/localizacao_tratada').set({
                        'distancia': round(distancia, 2),
                        'dentro': dentro,
                        'fora_de_zona': not dentro,
                        'lat_atual': lat,
                        'lon_atual': lon,
                        'passos': passos_atuais,
                        'status_ativo': status_ativo,
                        'intensidade': intensidade,          # NOVA MÉTRICA
                        'minutos_inativo': minutos_inativo,  # NOVA MÉTRICA
                        'timestamp': time.time()
                    })
                    
                    status_txt = "SEGURO" if dentro else "FORA"
                    print(f"[{time.strftime('%H:%M:%S')}] {nome_real}: {status_txt} | {intensidade} | Inativo: {round(minutos_inativo, 1)}min")

        except Exception as e:
            print(f"Erro geral no loop: {e}")

        time.sleep(5)

if __name__ == "__main__":
    processar_dados()