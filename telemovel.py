import time
import datetime
import requests
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate(r"C:\Users\saraa\Documents\1ano mestrado\2semestre\ambientes inteligente\keys_trab1\aims-tp1-firebase-adminsdk-fbsvc-7898f84f90.json")

firebase_admin.initialize_app(cred, {'databaseURL': 'https://aims-tp1-default-rtdb.europe-west1.firebasedatabase.app/'})

# --- CONFIGURAÇÃO GOOGLE FIT ---
CLIENT_ID = ""
CLIENT_SECRET = ""
REFRESH_TOKEN = ""

def obter_dados_reais():
    # 1. Obter novo Access Token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
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
            # Fallback se não houver pontos recentes (Braga)
            lat, lon = 41.5503, -8.4200 
    except (KeyError, IndexError):
        lat, lon = 41.5503, -8.4200
    
    return passos, lat, lon

def buscar_e_enviar():
    # Referência para a pasta onde vamos guardar a lista de medições
    ref_historico = db.reference('monitorizacao/utilizador_01/historico')
    
    # Referência para o valor "atual" (opcional, apenas para saber o último valor rápido)
    ref_atual = db.reference('monitorizacao/utilizador_01/atual')

    print("Sistema iniciado! A guardar histórico...")
    
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
            
            # --- AQUI ESTÁ A MUDANÇA ---
            # .push() adiciona à lista sem apagar o que lá estava
            ref_historico.push(dados)
            
            # .set() no "atual" apenas para termos o último valor num sítio fixo
            ref_atual.set(dados)
            
            print(f"Novo registo guardado no histórico! Passos: {p}")
            
        except Exception as e:
            print(f"Erro no loop: {e}")
            
        # Espera 1 minuto (ou o tempo que o grupo definir)
        time.sleep(30)

if __name__ == "__main__":
    buscar_e_enviar()