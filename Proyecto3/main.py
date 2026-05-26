from fastapi import FastAPI, HTTPException, Query
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

# RFC1: TOP 10 HOTELES
@app.get('/rfc1')
def get_top_hoteles(fechaInicio: str, fechaFin: str):
    try:
        pipeline = [
            {"$match": {
                "fecha_creacion": {
                    "$gte": datetime.fromisoformat(fechaInicio),
                    "$lte": datetime.fromisoformat(fechaFin)
                },
                "estado": "publicada",
                "calificacion": {"$exists": True, "$ne": "", "$ne": None}  # ← AGREGAR ESTO
            }},
            {"$group": {
                "_id": "$id_hotel",
                "calificacion_promedio": {"$avg": "$calificacion"}
            }},
            {"$sort": {"calificacion_promedio": -1}},
            {"$limit": 10}
        ]
        return list(db["resenas"].aggregate(pipeline))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# RFC2: EVOLUCIÓN MENSUAL
@app.get('/rfc2/{hotel_id}')
def get_evolucion(hotel_id: int, anio: int = Query(2026)):
    try:
        pipeline = [
            {"$match": {
                "id_hotel": hotel_id,
                "fecha_creacion": {
                    "$gte": f"{anio}-01-01T00:00:00",
                    "$lte": f"{anio}-12-31T23:59:59"
                }
            }},
            {"$addFields": {
                "fecha_obj": { "$dateFromString": { "dateString": "$fecha_creacion" } }
            }},
            {"$group": {
                "_id": {"$month": "$fecha_obj"},
                "calificacion_promedio_mes": {"$avg": {"$toDouble": "$calificacion"}}
            }},
            {"$sort": {"_id": 1}}
        ]
        return list(db["resenas"].aggregate(pipeline))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# RFC3: COMPARATIVO CIUDAD
@app.get('/rfc3')
def get_comparativo_ciudad(ciudad: str = Query(...)):
    try:
        mapeo = {
            "bogota": [1, 2, 3], 
            "medellin": [4, 5], 
            "cali": [6], 
            "cartagena": [7]
        }
        
        ciudad_limpia = ciudad.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        ids_hoteles = mapeo.get(ciudad_limpia, [])

        pipeline = [
            {"$match": {
                "id_hotel": {"$in": ids_hoteles}
            }},
            {"$group": {
                "_id": "$id_hotel",
                "calificacion_promedio_general": {"$avg": {"$toDouble": "$calificacion"}},
                "total_reseñas": {"$sum": 1},
                "reseñas_con_respuesta": {
                    "$sum": {"$cond": [{"$ifNull": ["$respuesta", False]}, 1, 0]}
                },
                "reseñas_destacadas": {
                    "$sum": {"$cond": [{"$eq": ["$destacada", True]}, 1, 0]}
                }
            }}
        ]
        return list(db["resenas"].aggregate(pipeline))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
