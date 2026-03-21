from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from geopy.distance import geodesic
import uvicorn
import firebase_admin
from firebase_admin import credentials, db
import time

app = FastAPI(title="Geofencing API Visual - Firebase Idoso")

# ==========================================
# 1. CONFIGURAÇÃO FIREBASE (Do teu projeto)
# ==========================================
# 1. Coloca o caminho exato que tens no telemovel.py
cred = credentials.Certificate(r"C:\Users\saraa\Documents\1ano mestrado\2semestre\ambientes inteligente\keys_trab1\aims-tp1-firebase-adminsdk-fbsvc-7898f84f90.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://aims-tp1-default-rtdb.europe-west1.firebasedatabase.app/'
    })

# 2. ALTERAÇÃO AQUI: Ler do sítio onde o telemovel.py escreve!
ref_gps_bruto = db.reference('monitorizacao/utilizador_01/atual')

# (Opcional) Podes manter esta pasta para guardar os resultados tratados, ou mudar para dentro da pasta do utilizador_01
ref_tratado = db.reference('monitorizacao/utilizador_01/localizacao_tratada')


# ==========================================
# 2. DEFINIÇÕES DA GEOFENCE (Da aula / Teu)
# ==========================================
# Usando as tuas coordenadas da UMinho (Gualtar)
FENCE_CENTER = [41.5607, -8.3972]
RADIUS_METERS = 500


# ==========================================
# 3. INTERFACE VISUAL (HTML/Mapa)
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def get_map():
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monitorização Idoso - Geofence</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #map {{ height: 600px; width: 100%; }}
            body {{ font-family: sans-serif; margin: 0; padding: 20px; }}
            .info {{ position: absolute; top: 10px; right: 10px; z-index: 1000; background: white; padding: 15px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2); font-size: 16px; }}
            .status-dentro {{ color: green; font-weight: bold; }}
            .status-fora {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="info" id="status">A aguardar dados do Firebase...</div>
        <div id="map"></div>
        
        <script>
            var centerLatLng = {FENCE_CENTER};
            var map = L.map('map').setView(centerLatLng, 15);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

            // Desenha o Raio de 500m
            L.circle(centerLatLng, {{ color: 'red', fillColor: '#f03', fillOpacity: 0.3, radius: {RADIUS_METERS} }}).addTo(map);
            L.marker(centerLatLng).addTo(map).bindPopup("UMinho (Centro da Geofence)").openPopup();

            var idosoMarker;

            // Função que vai ler do backend em vez do click do rato
            function fetchLocation() {{
                // Fazemos um GET porque agora a API vai ler do Firebase, e não do body do request
                fetch('/check-geofence')
                .then(res => {{
                    if (!res.ok) return res.json().then(err => {{ throw err; }});
                    return res.json();
                }})
                .then(data => {{
                    // Remove o pino antigo e coloca na nova posição lida do Firebase
                    if (idosoMarker) map.removeLayer(idosoMarker);
                    idosoMarker = L.marker([data.lat, data.lng]).addTo(map).bindPopup("Posição do Idoso");
                    
                    // Atualiza o painel de info
                    var statusColor = data.dentro ? "status-dentro" : "status-fora";
                    var statusText = data.dentro ? "DENTRO DA ZONA" : "FORA DA ZONA";
                    
                    document.getElementById('status').innerHTML = 
                        `Distância: <b>${{data.distancia}}m</b><br>
                         Estado: <span class="${{statusColor}}">${{statusText}}</span>`;
                }})
                .catch(err => {{
                    document.getElementById('status').innerHTML =
                        `<b>Erro a ler dados:</b><br>${{err.detail || 'Sem dados'}}`;
                }});
            }}

            // Chama logo a primeira vez...
            fetchLocation();
            // ...e depois repete a cada 5 segundos automaticamente!
            setInterval(fetchLocation, 5000);
        </script>
    </body>
    </html>
    """

# ==========================================
# 4. ENDPOINT DA API (Lê Firebase, processa, devolve)
# ==========================================
@app.get("/check-geofence") # Passou a GET porque já não recebe dados do rato
async def check_location():
    # 1. Vai buscar a localização "bruta" enviada pelo telemóvel ao Firebase
    dados = ref_gps_bruto.get()
    
    if not dados or 'latitude' not in dados or 'longitude' not in dados:
        raise HTTPException(
            status_code=404,
            detail="Não há dados de GPS do idoso no Firebase."
        )
        
    lat = dados['latitude']
    lon = dados['longitude']
    
    # 2. Calcula a distância (usando geodesic da aula em vez de contas manuais)
    user_coords = (lat, lon)
    distance = geodesic(FENCE_CENTER, user_coords).meters
    dentro = distance <= RADIUS_METERS
    
    # 3. Escreve os dados tratados de volta no Firebase (para o teu Motor de Decisão)
    ref_tratado.set({
        'distancia': round(distance, 2),
        'fora_de_zona': not dentro,
        'timestamp': time.time(),
        'lat_atual': lat,
        'lon_atual': lon
    })

    # 4. Devolve os dados para o mapa (HTML) atualizar o visual
    return {
        "lat": lat,
        "lng": lon,
        "distancia": round(distance, 2),
        "dentro": dentro
    }


if __name__ == "__main__":
    print("A iniciar servidor FastAPI com integração Firebase...")
    # Inicia o servidor na porta 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)