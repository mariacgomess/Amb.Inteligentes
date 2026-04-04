import time
import datetime
import requests
import firebase_admin
from firebase_admin import credentials, db

# --- CONFIGURAÇÕES E FIREBASE ---
cred_path ="" 

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://aims-tp1-default-rtdb.europe-west1.firebasedatabase.app/'
    })


# --- chaves ----

def obter_access_token():
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": "CLIENT_ID",
        "client_secret": "CLIENT_SECRET",
        "refresh_token": "REFRESH_TOKEN",
        "grant_type": "refresh_token"
    }
    res = requests.post(token_url, data=token_data).json()
    return res.get("access_token")

def obter_historico_7_dias(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # fonte "estimated_steps" que é a que a App Google Fit usa para o gráfico
    ds_estimado = "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
    
    historico = []
    
    for i in range(6, -1, -1):  # De 6 dias atrás até hoje (0)
        data_alvo = datetime.datetime.now() - datetime.timedelta(days=i)
        
        # Define início e fim do dia (meia-noite às 23:59:59)
        inicio_dia = data_alvo.replace(hour=0, minute=0, second=0, microsecond=0)
        fim_dia = data_alvo.replace(hour=23, minute=59, second=59, microsecond=999)
        
        inicio_ns = int(inicio_dia.timestamp() * 1000000000)
        fim_ns = int(fim_dia.timestamp() * 1000000000)
        
        url = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{ds_estimado}/datasets/{inicio_ns}-{fim_ns}"
        
        try:
            res = requests.get(url, headers=headers).json()
            passos_do_dia = 0
            if "point" in res:
                for ponto in res["point"]:
                    passos_do_dia += ponto["value"][0]["intVal"]
            
            data_str = inicio_dia.strftime('%Y-%m-%d')
            historico.append({'data': data_str, 'passos': passos_do_dia})
            print(f" {data_str}: {passos_do_dia} passos (Recuperados)")
            
        except Exception as e:
            print(f" Erro no dia {i}: {e}")
            
    return historico

def obter_passos_atuais(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # fonte de "Passos Estimados" que junta sensores e correções da App
    ds_estimado = "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
    
    agora_ns = int(time.time() * 1000000000)
    # Vai buscar dados desde o início do dia de hoje (meia-noite) até agora
    inicio_dia = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_ns = int(inicio_dia.timestamp() * 1000000000)
    
    url = f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{ds_estimado}/datasets/{inicio_ns}-{agora_ns}"
    
    try:
        res = requests.get(url, headers=headers).json()
        total_passos = 0
        
        # Soma de todos os pontos de passos registados hoje nesta fonte
        if "point" in res:
            for ponto in res["point"]:
                total_passos += ponto["value"][0]["intVal"]
        
        return total_passos
    except Exception as e:
        print(f" Erro ao ler passos reais: {e}")
        return 0

def buscar_e_enviar():
    print(" A iniciar Sistema de Monitorização (Apenas Passos)...")
    
    token = obter_access_token()
    if token:
        print(" A importar histórico semanal...")
        hist = obter_historico_7_dias(token)
        db.reference('monitorizacao/utilizador_01/estatisticas_semanais').set(hist)
    
    ref_hist = db.reference('monitorizacao/utilizador_01/historico')
    ref_atual = db.reference('monitorizacao/utilizador_01/atual')
    
    while True:
        try:
            token = obter_access_token() 
            p = obter_passos_atuais(token)
            
            # update em vez de set para não apagar a latitude/longitude que o telemóvel está a enviar em paralelo
            dados = {
                'passos': p,
                'timestamp': time.time(),
                'hora_leitura': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            ref_atual.update(dados)
            # Para o histórico, guarda o registo dos passos
            ref_hist.push(dados)
            
            print(f" Passos Sincronizados: {p}")
            
        except Exception as e:
            print(f" Erro no loop: {e}")
            
        time.sleep(600)

if __name__ == "__main__":
    buscar_e_enviar()