from fastapi import APIRouter, Depends, HTTPException, status
import asyncio
import os
import glob
import csv
from fastapi.responses import FileResponse
import sqlite3
import json

ruta_db = os.path.join("datos", "base_relacional", "historial_sesiones.db")

# Importamos las herramientas físicas
from modulos.agente.herramientas import (
    obtener_diagnostico_sistema,
    listar_archivos_reportes,
    limpiar_cache_scraping,
    exportar_analisis_csv,
    calcular_promedio_estrellas,
    contar_sentimientos_totales,
    obtener_reseña_mas_critica
)

# Importamos el guardia de seguridad para que nadie sin login pueda usar las herramientas
from modulos.seguridad.autenticacion import obtener_usuario_actual

# Creamos el mini-orquestador para estas rutas específicas
router = APIRouter(
    prefix="/api/herramientas",
    tags=["Panel de Control y Herramientas"],
    dependencies=[Depends(obtener_usuario_actual)] # Protege TODAS las rutas de este archivo
)

@router.get("/diagnostico")
async def endpoint_diagnostico():
    """Devuelve el estado actual del servidor local."""
    resultado = await asyncio.to_thread(obtener_diagnostico_sistema)
    return {"estado": "ok", "mensaje": resultado}

@router.get("/reportes")
async def endpoint_listar_reportes():
    """Lista todos los archivos generados en el servidor."""
    resultado = await asyncio.to_thread(listar_archivos_reportes)
    return {"estado": "ok", "mensaje": resultado}

@router.post("/limpiar-cache")
async def endpoint_limpiar_cache():
    """Purga los archivos temporales JSON."""
    resultado = await asyncio.to_thread(limpiar_cache_scraping)
    if "[ERROR]" in resultado:
        raise HTTPException(status_code=500, detail=resultado)
    return {"estado": "ok", "mensaje": resultado}

@router.post("/exportar-csv")
async def endpoint_exportar_csv():
    """Genera el archivo CSV y envía los bytes directamente al frontend."""
    resultado = await asyncio.to_thread(exportar_analisis_csv)
    
    if "[ERROR]" in resultado or "[FALLO]" in resultado:
        raise HTTPException(status_code=400, detail=resultado)
    
    # 1. Buscamos dónde guardó el archivo tu función. 
    # Asumo que se guarda en la carpeta 'datos' o 'reportes'.
    # Buscaremos el CSV más reciente generado en tu proyecto:
    rutas_posibles = glob.glob("**/*.csv", recursive=True)
    
    if not rutas_posibles:
        raise HTTPException(status_code=404, detail="Se generó el CSV pero no se pudo localizar en el servidor.")
    
    # Obtenemos el archivo más nuevo (el que se acaba de crear)
    archivo_reciente = max(rutas_posibles, key=os.path.getctime)
    
    # 2. Retornamos el archivo físicamente
    return FileResponse(
        path=archivo_reciente, 
        filename="Analisis_Resenas.csv", # Este es el nombre por defecto que verá el navegador
        media_type="text/csv"
    )

@router.get("/metricas/resumen")
async def endpoint_metricas_rapidas():
    """Devuelve un resumen estadístico instantáneo para pintar en el Dashboard de React con el nombre del producto incluido."""
    
    # 1. Ejecutamos tus cálculos asíncronos actuales
    promedio = await asyncio.to_thread(calcular_promedio_estrellas)
    sentimientos = await asyncio.to_thread(contar_sentimientos_totales)
    critica = await asyncio.to_thread(obtener_reseña_mas_critica)
    
    # 2. Extraemos de forma segura el nombre del producto actual desde el JSON
    producto_nombre = "Ningún producto analizado"
    archivo_enriquecido = os.path.join("datos", "procesados", "reseñas_enriquecidas.json")
    
    if os.path.exists(archivo_enriquecido):
        try:
            # Abrimos el archivo en un hilo secundario para no bloquear el bucle de eventos si es muy grande
            def leer_producto():
                with open(archivo_enriquecido, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    if datos and len(datos) > 0:
                        return datos[0].get("producto", "Producto sin nombre asignado")
                return "Sin datos disponibles"
            
            producto_nombre = await asyncio.to_thread(leer_producto)
        except Exception:
            producto_nombre = "Error al obtener el nombre del producto"

    # 3. Retornamos todo junto al Frontend de React
    return {
        "producto": producto_nombre,  # 🚨 NUEVO CAMPO DISPONIBLE EN EL DASHBOARD
        "promedio_estrellas": promedio,
        "distribucion_sentimientos": sentimientos,
        "reseña_destacada": critica
    }
@router.get("/metricas/ultima")
def obtener_ultima_metrica():
    try:
        conn = sqlite3.connect(ruta_db)
        c = conn.cursor()
        c.execute('''
            SELECT user_prompt, ttft_ms, total_latency_ms, tokens_per_second 
            FROM auditoria 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        registro = c.fetchone()
        conn.close()

        if not registro:
            raise HTTPException(status_code=404, detail="Sin registros aún")

        return {
            "prompt": registro[0],
            "ttft_ms": registro[1],
            "total_latency_ms": registro[2],
            "tokens_per_second": registro[3]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))