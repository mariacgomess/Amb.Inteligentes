import time
import datetime
import requests
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate(r"C:\\Users\\helen\\Desktop\\Mestrado\\2Semestre\\Ambientes Inteligentes\\TPg\\aims-tp1-firebase-adminsdk-fbsvc-7898f84f90.json")

firebase_admin.initialize_app(cred, {'databaseURL': 'https://aims-tp1-default-rtdb.europe-west1.firebasedatabase.app/'})

# --- CONFIGURAÇÃO GOOGLE FIT ---
CLIENT_ID = ""
CLIENT_SECRET = ""
REFRESH_TOKEN = ""

# --- 2. INICIALIZAÇÃO FIREBASE ---
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://aims-tp1-default-rtdb.europe-west1.firebasedatabase.app/'
    })

def obter_access_token():
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    res = requests.post(token_url, data=token_data).json()
    return res.get("access_token")

def obter_historico_7_dias(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    agora = int(time.time() * 1000)
    inicio_7d = agora - (7 * 24 * 60 * 60 * 1000)
    
    url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
    corpo = {
        "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": inicio_7d,
        "endTimeMillis": agora
    }
    
    res = requests.post(url, headers=headers, json=corpo).json()
    historico = []
    for bucket in res.get('bucket', []):
        ts = int(bucket['startTimeMillis'])
        data_f = datetime.datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d')
        try:
            p = bucket['dataset'][0]['point'][0]['value'][0]['intVal']
        except: p = 0
        historico.append({'data': data_f, 'passos': p})
    return historico

def obter_dados_atuais(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # --- PASSOS DE HOJE ---
    agora = int(time.time() * 1000)
    inicio_dia = int(datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    
    url_p = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
    corpo_p = {
        "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": inicio_dia,
        "endTimeMillis": agora
    }
    res_p = requests.post(url_p, headers=headers, json=corpo_p).json()
    try:
        passos = res_p['bucket'][0]['dataset'][0]['point'][0]['value'][0]['intVal']
    except: passos = 0

    # --- LOCALIZAÇÃO (ÚLTIMOS 30 MIN) ---
    ds = "derived:com.google.location.sample:com.google.android.gms:merged_location"
    agora_ns = int(time.time() * 1000000000)
    janela_ns = agora_ns - (30 * 60 * 1000000000)
    
    url_l = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{ds}/datasets/{janela_ns}-{agora_ns}"
    res_l = requests.get(url_l, headers=headers).json()
    
    lat, lon = 41.5503, -8.4200 # Fallback Braga
    if "point" in res_l and len(res_l["point"]) > 0:
        lat = res_l["point"][-1]["value"][0]["fpVal"]
        lon = res_l["point"][-1]["value"][1]["fpVal"]

    res_l = requests.get(url_l, headers=headers).json()
    print(f"RESPOSTA GPS GOOGLE: {res_l}") # ADICIONA ESTA LINHA
        
    return passos, lat, lon

def buscar_e_enviar():
    print("A iniciar Sistema de Monitorização...")
    
    # 1. Primeira Sincronização: Importar histórico da semana
    token = obter_access_token()
    print("A importar histórico dos últimos 7 dias...")
    hist = obter_historico_7_dias(token)
    db.reference('monitorizacao/utilizador_01/estatisticas_semanais').set(hist)
    
    # 2. Loop de Tempo Real
    ref_hist = db.reference('monitorizacao/utilizador_01/historico')
    ref_atual = db.reference('monitorizacao/utilizador_01/atual')
    
    while True:
        try:
            token = obter_access_token() # Atualiza o token a cada volta
            p, lat, lon = obter_dados_atuais(token)
            
            dados = {
                'passos': p,
                'latitude': lat,
                'longitude': lon,
                'timestamp': time.time(),
                'hora_leitura': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            ref_hist.push(dados)
            ref_atual.set(dados)
            
            print(f"Sincronizado: {p} passos | Lat: {lat:.4f} Lon: {lon:.4f}")
        except Exception as e:
            print(f"Erro: {e}")
            
        time.sleep(60)

if __name__ == "__main__":
    buscar_e_enviar()