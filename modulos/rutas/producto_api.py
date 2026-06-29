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
        print("[PIPELINE] 1. Desconectando motor vectorial y liberando hilos...")
        
        # 🚨 PASO DE ORO: Si el asistente existe en la app, matamos sus hilos persistentes
        asistente_actual = getattr(request.app.state, "asistente", None)
        if asistente_actual and hasattr(asistente_actual, "db_cliente"):
            try:
                asistente_actual.db_cliente._system.stop() # Cierra SQLite y ChromaDB de golpe
                print("[PIPELINE] Conexión de ChromaDB cerrada de forma segura.")
            except Exception as ex:
                print(f"[WARN] No se pudo apagar Chroma explícitamente: {ex}")
        
        # Quitamos la referencia y forzamos la limpieza en memoria
        request.app.state.asistente = None
        gc.collect() 
        time.sleep(2.0) # Le damos 2 segundos completos a Windows para liberar los archivos

        print("[PIPELINE] 2. Purgando datos del producto anterior de forma física...")
        
        # 🚨 CORRECCIÓN: Ahora borramos los archivos JSON con ciclo de reintentos
        for archivo in [archivo_crudo, archivo_enriquecido]:
            if os.path.exists(archivo):
                for intento in range(3):
                    try:
                        os.remove(archivo)
                        print(f"[PIPELINE] Archivo eliminado con éxito: {archivo}")
                        break
                    except PermissionError:
                        print(f"[PIPELINE] Archivo {archivo} retenido. Reintentando borrado...")
                        time.sleep(1.0)

        # Intento seguro de borrado de la carpeta completa de ChromaDB
        if os.path.exists(ruta_db_local):
            for intento in range(4):
                try:
                    shutil.rmtree(ruta_db_local)
                    print("[PIPELINE] Base vectorial anterior eliminada por completo (ChromaDB purgado).")
                    break
                except PermissionError:
                    print(f"[PIPELINE] Carpeta bloqueada por Windows. Reintentando purga ({intento+1}/4)...")
                    time.sleep(1.5)
        
        # Recrear la estructura de carpetas completamente vacías
        os.makedirs(os.path.join("datos", "crudos"), exist_ok=True)
        os.makedirs(os.path.join("datos", "procesados"), exist_ok=True)
        os.makedirs(ruta_db_local, exist_ok=True)

        print(f"[PIPELINE] 3. Iniciando extracción desde: {url_objetivo}")
        extractor = ExtractorEspecifico(archivo_salida=archivo_crudo)
        extractor.extraer(url_objetivo, scrolls=3)

        print("[PIPELINE] 4. Clasificando reseñas extraídas en paralelo...")
        clasificador = ClasificadorReseñas()
        asyncio.run(clasificador.procesar_pipeline(archivo_entrada=archivo_crudo, archivo_salida=archivo_enriquecido))

        print("[PIPELINE] 5. Indexando nueva base vectorial desde cero...")
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