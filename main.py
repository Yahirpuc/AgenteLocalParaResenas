import os
import time
import gc
import sqlite3
import uuid
import asyncio

from llama_index.core.tools import FunctionTool

# =====================================================================
# IMPORTACIONES DE LA NUEVA ARQUITECTURA MODULAR
# =====================================================================
from modulos.procesamiento.extractor import ExtractorEspecifico
from modulos.procesamiento.clasificador import ClasificadorReseñas
from modulos.procesamiento.indexador import IndexadorRAG
from modulos.agente.asistente import AsistenteAnaliticoHibrido
import modulos.agente.herramientas as funciones_locales

# Importaciones de infraestructura
from modulos.infraestructura.clientes_sqlite import ( 
    inicializar_base_datos, 
    guardar_mensaje as db_guardar_mensaje, 
    cargar_historial as db_cargar_historial
)

# =====================================================================
# RUTAS DE DATOS GLOBALES
# =====================================================================
RUTA_DB_RELACIONAL = os.path.join("datos", "base_relacional", "historial_sesiones.db")

# =====================================================================
# PERSISTENCIA ASÍNCRONA DE SESIONES
# =====================================================================

# Wrappers asíncronos limpios en tu main.py o api.py
async def inicializar_db_chat():
    await asyncio.to_thread(inicializar_base_datos)

async def cargar_historial(session_id):
    return await asyncio.to_thread(db_cargar_historial, session_id)

async def guardar_mensaje(session_id, role, content, usuario_id="usuario_default"):
    await asyncio.to_thread(db_guardar_mensaje, session_id, role, content, usuario_id)

# =====================================================================
# EVENT LOOP - CICLO DE CONVERSACIÓN ASÍNCRONO
# =====================================================================
async def ciclo_de_chat(agente, session_id):
    print("\n" + "="*70)
    print(f" AGENTE ASÍNCRONO EN LÍNEA - ID DE SESIÓN: {session_id} ")
    print("="*70 + "\n")

    while True:
        entrada = input(f"[{session_id}] Usuario > ").strip()
        
        if entrada.lower() in ["salir", "exit", "quit"]:
            print("[INFO] Finalizando flujo de ejecución. Historial guardado de forma segura.")
            break
            
        if not entrada:
            continue

        await guardar_mensaje(session_id, 'user', entrada)

        try:
            print("[AGENTE PROCESANDO EVENTOS Y RAZONANDO...]")
            
            # EJECUCIÓN ASÍNCRONA NATIVA (LlamaIndex 0.13+ Workflows)
            respuesta_agente = await agente.run(entrada)
            
            await guardar_mensaje(session_id, 'assistant', str(respuesta_agente))
            
            print(f"\n[ASISTENTE]\n{respuesta_agente}\n")
            
        except Exception as e:
            print(f"\n[ERROR CONTROLADO EN EVENT LOOP] {e}\n")

# =====================================================================
# ORQUESTADOR PRINCIPAL ASÍNCRONO
# =====================================================================
async def iniciar_flujo_completo():
    print("=" * 70)
    print(" SISTEMA RAG ASÍNCRONO - ARQUITECTURA MODULAR ")
    print("=" * 70)
    
    # Rutas actualizadas a la nueva arquitectura
    archivo_crudo = os.path.join("datos", "crudos", "reseñas_crudas.json")
    archivo_enriquecido = os.path.join("datos", "procesados", "reseñas_enriquecidas.json")
    ruta_db_local = os.path.join("datos", "base_vectorial")
    coleccion_local = "reviews_analizadas"
    
    await inicializar_db_chat()
    
    session_id = input("\n[SESIÓN] Ingresa tu ID de conversación (ENTER para nueva) > ").strip()
    
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
        print(f"[INFO] Nueva sesión de chat inicializada. ID asignado: {session_id}")
        historial_cargado = []
    else:
        historial_cargado = await cargar_historial(session_id)
        print(f"[INFO] Estado de sesión recuperado. Mensajes encontrados: {len(historial_cargado)}")

    ejecutar_extraccion = not os.path.exists(os.path.join(ruta_db_local, "chroma.sqlite3"))

    if ejecutar_extraccion:
        print("\n[INFO] Almacenamiento vectorial no detectado. Iniciando pipeline...")
        url_objetivo = input("\nIntroduce la URL del producto para analizar > ").strip()
        if not url_objetivo: 
            return

        if os.path.exists(archivo_crudo): os.remove(archivo_crudo)
        if os.path.exists(archivo_enriquecido): os.remove(archivo_enriquecido)

        extractor = ExtractorEspecifico(archivo_salida=archivo_crudo)
        extractor.extraer(url_objetivo, scrolls=3)

        print("\n[PIPELINE] Clasificando y extrayendo metadatos estructurados...")
        clasificador = ClasificadorReseñas()
        clasificador.procesar_pipeline(archivo_entrada=archivo_crudo, archivo_salida=archivo_enriquecido)

        print("\n[PIPELINE] Reconstruyendo índices vectoriales en ChromaDB...")
        indexador_instancia = IndexadorRAG(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
        indexador_instancia.construir_indice(archivo_enriquecido=archivo_enriquecido)
        
        gc.collect()
        time.sleep(1)
    else:
        print("\n[INFO] Almacenamiento indexado legítimo detectado. Saltando extracción de entorno web.")

    herramientas_fc = [
        FunctionTool.from_defaults(fn=funciones_locales.guardar_reporte_txt),
        FunctionTool.from_defaults(fn=funciones_locales.exportar_analisis_csv),
        FunctionTool.from_defaults(fn=funciones_locales.listar_archivos_reportes),
        FunctionTool.from_defaults(fn=funciones_locales.calcular_promedio_estrellas),
        FunctionTool.from_defaults(fn=funciones_locales.contar_sentimientos_totales),
        FunctionTool.from_defaults(fn=funciones_locales.obtener_reseña_mas_critica),
        FunctionTool.from_defaults(fn=funciones_locales.obtener_diagnostico_sistema),
        FunctionTool.from_defaults(fn=funciones_locales.limpiar_cache_scraping)
    ]
    
    asistente = AsistenteAnaliticoHibrido(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
    asistente.herramientas_agente.extend(herramientas_fc)
    
    agente = asistente.iniciar_sesion_agente(historial_cargado=historial_cargado)

    await ciclo_de_chat(agente, session_id)

if __name__ == "__main__":
    asyncio.run(iniciar_flujo_completo())