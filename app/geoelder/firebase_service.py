import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate(r"C:\Users\saraa\Documents\1ano mestrado\2semestre\ambientes inteligente\keys_trab1\aims-tp1-firebase-adminsdk-fbsvc-7898f84f90.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://aims-tp1-default-rtdb.europe-west1.firebasedatabase.app/'
    })

def get_dados_idoso(user_id):
    ref = db.reference(f'monitorizacao/{user_id}/localizacao_tratada')
    return ref.get()