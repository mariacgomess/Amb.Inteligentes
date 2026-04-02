import time
from geopy.distance import geodesic
import firebase_admin
from firebase_admin import credentials, db

print("A iniciar o Motor de Regras IoT (Processamento em background)...")

# ==========================================
# 1. CONFIGURAÇÃO FIREBASE 
# ==========================================
cred = credentials.Certificate(r"C:\Users\helen\Desktop\Mestrado\2Semestre\Ambientes Inteligentes\TPg\aims-tp1-firebase-adminsdk-fbsvc-7898f84f90.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://aims-tp1-default-rtdb.europe-west1.firebasedatabase.app/'
    })

ref_gps_bruto = db.reference('monitorizacao/utilizador_01/atual')
ref_tratado = db.reference('monitorizacao/utilizador_01/localizacao_tratada')


# ==========================================
# 2. DEFINIÇÕES DA GEOFENCE 
# ==========================================
FENCE_CENTER = [41.5607, -8.3972]
RADIUS_METERS = 500


# ==========================================
# 3. MOTOR DE DECISÃO (Loop Contínuo)
# ==========================================
def processar_dados():
    while True:
        try:
            # 1. Lê os dados "crus" vindos do telemóvel
            dados = ref_gps_bruto.get()
            
            if dados and 'latitude' in dados and 'longitude' in dados:
                lat = dados['latitude']
                lon = dados['longitude']
                passos = dados.get('passos', 0)
                
                # 2. Faz a Matemática Pesada (Cálculo da Geofence)
                user_coords = (lat, lon)
                distance = geodesic(FENCE_CENTER, user_coords).meters
                dentro = distance <= RADIUS_METERS
                
                # 3. Escreve os dados TRATADOS no Firebase
                ref_tratado.set({
                    'distancia': round(distance, 2),
                    'dentro': dentro,
                    'fora_de_zona': not dentro,
                    'lat': lat,
                    'lng': lon,
                    'passos': passos,
                    'timestamp': time.time()
                })
                
                estado_str = "SEGURO" if dentro else "FORA DE ZONA!"
                print(f"[{time.strftime('%H:%M:%S')}] Dados processados: Distância {round(distance, 2)}m -> {estado_str}")
            
            else:
                print(f"[{time.strftime('%H:%M:%S')}] A aguardar dados crus do telemóvel...")

        except Exception as e:
            print(f"Erro no processamento: {e}")

        # Espera 5 segundos antes de verificar novamente
        time.sleep(5)

if __name__ == "__main__":
    processar_dados()