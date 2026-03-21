import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("CAMINHO_PARA_KEY.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://TEU_URL.firebaseio.com/'
    })

def get_dados_idoso(user_id):
    ref = db.reference(f'monitorizacao/{user_id}/atual')
    return ref.get()