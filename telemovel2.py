import time
import datetime
import requests
import firebase_admin
from firebase_admin import credentials, db

# ==========================================
# 1. CONFIGURAÇÃO FIREBASE (IGUAL PARA TODOS)
# ==========================================
# Se o ficheiro .json estiver na mesma pasta do script, podes usar apenas o nome
cred = credentials.Certificate("C:\\Users\\helen\\Desktop\\Mestrado\\2Semestre\\Ambientes Inteligentes\\TPg\\aims-tp1-firebase-adminsdk-fbsvc-7898f84f90.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://aims-tp1-default-rtdb.europe-west1.firebasedatabase.app/'
    })

# ==========================================
# 2. CONFIGURAÇÃO GOOGLE FIT (AS TUAS CREDENCIAIS)
# ==========================================
CLIENT_ID = ""
CLIENT_SECRET = ""
REFRESH_TOKEN = ""

# MUDANÇA AQUI: Define quem és tu no Firebase (ex: utilizador_02)
MEU_ID_USUARIO = "utilizador_02" 

def obter_dados_reais():
    # 1. Obter novo Access Token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    
    try:
        token_res = requests.post(token_url, data=token_data).json()
        access_token = token_res.get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}

        # --- 2. BUSCAR PASSOS ---
        fit_url_passos = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
        agora = int(datetime.datetime.now().timestamp() * 1000)
        inicio_dia = int(datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        
        corpo_passos = {
            "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
            "bucketByTime": {"durationMillis": 86400000},
            "startTimeMillis": inicio_dia,
            "endTimeMillis": agora
        }
        res_passos_json = requests.post(fit_url_passos, headers=headers, json=corpo_passos).json()
        
        try:
            passos = res_passos_json['bucket'][0]['dataset'][0]['point'][0]['value'][0]['intVal']
        except (KeyError, IndexError):
            passos = 0

        # --- 3. BUSCAR COORDENADAS REAIS ---
        data_source = "derived:com.google.location.sample:com.google.android.gms:merged_location"
        agora_ns = int(time.time() * 1000000000)
        cinco_min_atras_ns = agora_ns - (5 * 60 * 1000000000)
        
        loc_url = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{data_source}/datasets/{cinco_min_atras_ns}-{agora_ns}"
        res_loc = requests.get(loc_url, headers=headers).json()
        
        lat, lon = 0.0, 0.0
        try:
            if "point" in res_loc and len(res_loc["point"]) > 0:
                ultimo_ponto = res_loc["point"][-1]
                lat = ultimo_ponto["value"][0]["fpVal"]
                lon = ultimo_ponto["value"][1]["fpVal"]
            else:
                lat, lon = 41.5503, -8.4200 
        except (KeyError, IndexError):
            lat, lon = 41.5503, -8.4200
            
        return passos, lat, lon

    except Exception as e:
        print(f"Erro ao ligar ao Google Fit: {e}")
        return 0, 41.5503, -8.4200

def buscar_e_enviar():
    # Referências agora usam o teu MEU_ID_USUARIO (utilizador_02)
    ref_historico = db.reference(f'monitorizacao/{MEU_ID_USUARIO}/historico')
    ref_atual = db.reference(f'monitorizacao/{MEU_ID_USUARIO}/atual')

    print(f"Sistema iniciado para o {MEU_ID_USUARIO}! A enviar dados...")
    
    while True:
        try:
            p, latitude, longitude = obter_dados_reais()
            
            dados = {
                'passos': p,
                'latitude': latitude,
                'longitude': longitude,
                'timestamp': time.time(),
                'hora_leitura': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Adiciona ao teu histórico e ao teu atual
            ref_historico.push(dados)
            ref_atual.set(dados)
            
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Dados enviados para {MEU_ID_USUARIO}: {p} passos.")
            
        except Exception as e:
            print(f"Erro no loop: {e}")
            
        # Espera 30 segundos
        time.sleep(30)

if __name__ == "__main__":
    buscar_e_enviar()