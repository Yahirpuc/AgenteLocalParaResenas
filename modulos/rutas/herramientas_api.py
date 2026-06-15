from fastapi import APIRouter, Depends, HTTPException, status
import asyncio

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
    """Genera el archivo CSV con los datos limpios y codificación para Excel."""
    resultado = await asyncio.to_thread(exportar_analisis_csv)
    if "[ERROR]" in resultado or "[FALLO]" in resultado:
        raise HTTPException(status_code=400, detail=resultado)
    return {"estado": "ok", "mensaje": resultado}

@router.get("/metricas/resumen")
async def endpoint_metricas_rapidas():
    """Devuelve un resumen estadístico instantáneo para pintar en el Dashboard de React."""
    promedio = await asyncio.to_thread(calcular_promedio_estrellas)
    sentimientos = await asyncio.to_thread(contar_sentimientos_totales)
    critica = await asyncio.to_thread(obtener_reseña_mas_critica)
    
    return {
        "promedio_estrellas": promedio,
        "distribucion_sentimientos": sentimientos,
        "reseña_destacada": critica
    }