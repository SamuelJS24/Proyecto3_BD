from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Descomente esta línea cuando suba la API a producción (por ejemplo en Render):
client = MongoClient(os.environ["MONGO_URI"]) 

# Para pruebas locales, ponga su URI directamente aquí (y coméntela antes de subir a GitHub):
#client = MongoClient("TU_URI_DE_MONGODB")

# Base de datos del proyecto Dann-Alpes
db = client["ISIS2304F15202610"] 

@app.get("/")
def inicio():
    return {"estado": "API de Dann-Alpes funcionando correctamente"}

# RF4 - Consultar reseñas de un hotel
@app.get('/hoteles/{hotel_id}/resenas')
def get_resenas(hotel_id: int):
    resenas = list(db["resenas"].find({"id_hotel": hotel_id}))
    for r in resenas:
        r["_id"] = str(r["_id"]) 
    return resenas

# RF1 - Crear reseña
@app.post('/hoteles/{hotel_id}/resenas')
def post_resena(hotel_id: int, datos: dict):
    datos['id_hotel'] = hotel_id
    datos['fecha_creacion'] = datetime.now().isoformat()
    datos['votos_utilidad'] = 0 
    
    db["resenas"].insert_one(datos)
    return {'mensaje': 'Reseña guardada exitosamente'}

# RF2 y RF7 - Editar reseña (cliente) o agregar respuesta oficial (administrador)
@app.put('/resenas/{resena_id}')
def put_resena(resena_id: str, datos: dict):
    filtro = {"_id": ObjectId(resena_id)}
    db["resenas"].update_one(filtro, {"$set": datos})
    return {'mensaje': 'Reseña actualizada'}

# RF3 y RF8 - Eliminar reseña
@app.delete('/resenas/{resena_id}')
def delete_resena(resena_id: str):
    filtro = {"_id": ObjectId(resena_id)}
    db["resenas"].delete_one(filtro)
    return {'mensaje': 'Reseña eliminada'}

# RF5 - Marcar reseña como útil
@app.post('/resenas/{resena_id}/votar')
def votar_resena(resena_id: str):
    filtro = {"_id": ObjectId(resena_id)}
    db["resenas"].update_one(filtro, {"$inc": {"votos_utilidad": 1}})
    return {'mensaje': 'Voto de utilidad registrado'}
