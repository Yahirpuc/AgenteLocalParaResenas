from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import os
import shutil
import asyncio
import time
import gc

# Importaciones de tu arquitectura
from modulos.procesamiento.extractor import ExtractorEspecifico
from modulos.procesamiento.clasificador import ClasificadorReseñas
from modulos.procesamiento.indexador import IndexadorRAG
from modulos.agente.asistente import AsistenteAnaliticoHibrido
from modulos.seguridad.autenticacion import obtener_usuario_actual

router = APIRouter(
    prefix="/api/producto",
    tags=["Gestión de Productos"],
    dependencies=[Depends(obtener_usuario_actual)]
)

class PeticionNuevoProducto(BaseModel):
    url: str

@router.post("/cargar")
async def cargar_nuevo_producto(peticion: PeticionNuevoProducto, request: Request):
    url_objetivo = peticion.url.strip()
    
    # ---------------------------------------------------------
    # TRUCO PARA WINDOWS: Liberar el archivo bloqueado (WinError 32)
    # ---------------------------------------------------------
    request.app.state.asistente = None # Desconectamos el agente actual
    gc.collect()                       # Forzamos a Python a limpiar la memoria
    await asyncio.sleep(1.5)           # Le damos a Windows 1.5 seg para soltar el archivo
    # ---------------------------------------------------------

    # Definir rutas
    archivo_crudo = os.path.join("datos", "crudos", "reseñas_crudas.json")
    archivo_enriquecido = os.path.join("datos", "procesados", "reseñas_enriquecidas.json")
    ruta_db_local = os.path.join("datos", "base_vectorial")
    coleccion_local = "reviews_analizadas"

    def ejecutar_pipeline_completo():
        print("[PIPELINE] 1. Limpiando datos del producto anterior...")
        if os.path.exists(archivo_crudo): os.remove(archivo_crudo)
        if os.path.exists(archivo_enriquecido): os.remove(archivo_enriquecido)
        
        # Intento seguro de borrado con reintentos para Windows
        if os.path.exists(ruta_db_local):
            for intento in range(4):
                try:
                    shutil.rmtree(ruta_db_local)
                    print("[PIPELINE] Base vectorial anterior eliminada con éxito.")
                    break
                except PermissionError:
                    print(f"[PIPELINE] Archivo bloqueado por Windows. Reintentando ({intento+1}/3)...")
                    time.sleep(1.5) # Espera y reintenta
        
        # Recrear carpetas si no existen
        os.makedirs(os.path.join("datos", "crudos"), exist_ok=True)
        os.makedirs(os.path.join("datos", "procesados"), exist_ok=True)
        os.makedirs(ruta_db_local, exist_ok=True)

        print(f"[PIPELINE] 2. Iniciando extracción desde: {url_objetivo}")
        extractor = ExtractorEspecifico(archivo_salida=archivo_crudo)
        extractor.extraer(url_objetivo, scrolls=3)

        print("[PIPELINE] 3. Clasificando reseñas extraídas...")
        clasificador = ClasificadorReseñas()
        clasificador.procesar_pipeline(archivo_entrada=archivo_crudo, archivo_salida=archivo_enriquecido)

        print("[PIPELINE] 4. Indexando nueva base vectorial...")
        indexador = IndexadorRAG(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
        indexador.construir_indice(archivo_enriquecido=archivo_enriquecido)

    try:
        # Ejecutamos el pipeline pesado
        await asyncio.to_thread(ejecutar_pipeline_completo)
        
        # Reconectamos el nuevo agente a la API global
        print("[PIPELINE] 5. Reiniciando el cerebro del Agente con el nuevo producto...")
        nuevo_asistente = AsistenteAnaliticoHibrido(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
        request.app.state.asistente = nuevo_asistente
        
        return {"estado": "ok", "mensaje": "Nuevo producto cargado, analizado e indexado correctamente."}
        
    except Exception as e:
        print(f"[ERROR PIPELINE] {e}")
        # En caso de error crítico, intentamos levantar el agente anterior para no dejar la app caída
        try:
            request.app.state.asistente = AsistenteAnaliticoHibrido(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Ocurrió un error al procesar el producto: {str(e)}")