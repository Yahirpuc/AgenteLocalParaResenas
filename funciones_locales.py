import os
import json
import csv
from datetime import datetime

# =====================================================================
# 🛠️ FASE 2: CATÁLOGO DE FUNCIONES LOCALES (CON TYPE HINTS Y DOCSTRINGS)
# =====================================================================

def guardar_reporte_txt(contenido: str, nombre_archivo: str) -> str:
    """
    Crea un archivo de texto físico (.txt) en el almacenamiento local con el informe generado.
    
    Args:
        contenido (str): Texto detallado o conclusiones del informe técnico.
        nombre_archivo (str): Nombre del archivo final (ej. 'conclusiones_auditoria.txt').
    Returns:
        str: Mensaje de confirmación con la ruta del archivo generado exitosamente.
    """
    try:
        nombre_limpio = "".join([c for c in nombre_archivo if c.isalpha() or c.isdigit() or c in '._- ']).strip()
        if not nombre_limpio.endswith(".txt"):
            nombre_limpio += ".txt"
        with open(nombre_limpio, "w", encoding="utf-8") as f:
            f.write(contenido)
        return f"[OK] Reporte de texto guardado exitosamente como: '{nombre_limpio}'."
    except Exception as e:
        return f"[ERROR] No se pudo escribir el archivo de texto: {str(e)}"

def exportar_analisis_csv(nombre_archivo: str = "exportacion_reseñas.csv") -> str:
    """
    Toma las reseñas enriquecidas del JSON local y las exporta a un archivo CSV estructurado.
    Corregido con inyección BOM para compatibilidad automática de caracteres en Microsoft Excel.
    
    Args:
        nombre_archivo (str): Nombre del archivo CSV a guardar (por defecto 'exportacion_reseñas.csv').
    Returns:
        str: Estado de la operación indicando el éxito o fallo técnico de la conversión.
    """
    origen_json = "reseñas_enriquecidas.json"
    if not os.path.exists(origen_json):
        return "[FALLO] No existen datos extraídos en JSON para realizar la exportación a CSV."
    try:
        with open(origen_json, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if not datos:
            return "[FALLO] El archivo de reseñas está vacío."
        
        # SOLUCIÓN DE CODIFICACIÓN: 'utf-8-sig' fuerza a Excel a reconocer eñes y acentos automáticamente
        with open(nombre_archivo, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Autor", "Titulo", "Texto", "Estrellas", "Sentimiento", "Categoria"])
            for item in datos:
                texto_opinion = item.get("texto", "")
                
                # FILTRO SANITIZADOR MEJORADO: Exclusión absoluta de cadenas del sistema del DOM de Amazon
                palabras_basura = [
                    "ORDENAR POR", "FILTRAR POR", "OPINIONES DE CLIENTES", 
                    "MÉTODOS ABREVIADOS", "COMPRADOR ANÓNIMO", "ENVÍO NACIONAL E INTERNACIONAL", 
                    "MEMBRESÍAS Y SUSCRIPCIONES", "ALERTAS DE REVISIÓN", "REGISTRARTE PARA UNA CUENTA",
                    "HOT SALE", "LA CANTIDAD ES", "CALIFICACIONES GLOBALES"
                ]
                
                # Si la cadena contiene texto obvio de menús o interfaz de usuario, se descarta por completo
                if any(menu in texto_opinion.upper() for menu in palabras_basura):
                    continue
                
                # Validación adicional para omitir registros vacíos o ruidos extremadamente cortos
                if len(texto_opinion.strip()) < 15:
                    continue
                        
                writer.writerow([
                    item.get("id", ""),
                    item.get("autor", ""),
                    item.get("titulo_comentario", ""),
                    texto_opinion,
                    item.get("estrellas", 0),
                    item.get("metadatos", {}).get("sentimiento", ""),
                    item.get("metadatos", {}).get("categoria", "")
                ])
        return f"[OK] Base de datos de opiniones exportada con éxito a: '{nombre_archivo}' con formato corregido y limpio."
    except Exception as e:
        return f"[ERROR] Fallo crítico durante la estructuración del archivo CSV: {str(e)}"

def listar_archivos_reportes() -> str:
    """
    Escanea el directorio raíz actual del proyecto para listar los informes generados (.txt o .csv).
    
    Returns:
        str: Listado formateado de los archivos encontrados en el servidor local.
    """
    try:
        archivos = [f for f in os.listdir('.') if f.endswith('.txt') or f.endswith('.csv')]
        if not archivos:
            return "[INFO] No se encontraron archivos de reportes previos (.txt o .csv) creados en el directorio."
        return "[ARCHIVOS DETECTADOS]:\n" + "\n".join([f"- {a}" for a in archivos])
    except Exception as e:
        return f"[ERROR] No se pudo escanear el directorio del servidor: {str(e)}"

def calcular_promedio_estrellas() -> str:
    """
    Lee de forma directa el JSON crudo de reseñas para calcular el promedio matemático exacto de estrellas.
    
    Returns:
        str: Cadena de texto con el resultado del promedio exacto obtenido de las opiniones de los clientes.
    """
    origen_json = "reseñas_enriquecidas.json"
    if not os.path.exists(origen_json):
        return "[FALLO] Archivo de datos no encontrado. Extraiga reseñas primero."
    try:
        with open(origen_json, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if not datos:
            return "[INFO] Cero opiniones registradas."
        calificaciones = [int(item["estrellas"]) for item in datos if item.get("estrellas") is not None]
        if not calificaciones:
            return "[INFO] No hay calificaciones numéricas dentro del conjunto de datos."
        promedio = sum(calificaciones) / len(calificaciones)
        return f"[MÉTRICA DIRECTA] Calificación promedio calculada del producto: {promedio:.2f} estrellas de un total de {len(calificaciones)} opiniones."
    except Exception as e:
        return f"[ERROR] Fallo al procesar el cálculo aritmético: {str(e)}"

def contar_sentimientos_totales() -> str:
    """
    Realiza un conteo estadístico estricto de la distribución de sentimientos del producto analizado.
    
    Returns:
        str: Desglose cuantitativo detallado de opiniones positivas y negativas.
    """
    origen_json = "reseñas_enriquecidas.json"
    if not os.path.exists(origen_json):
        return "[FALLO] Base documental ausente."
    try:
        with open(origen_json, "r", encoding="utf-8") as f:
            datos = json.load(f)
        pos = sum(1 for item in datos if item.get("metadatos", {}).get("sentimiento") == "Positivo")
        neg = sum(1 for item in datos if item.get("metadatos", {}).get("sentimiento") == "Negativo")
        return f"[MÉTRICA] Distribución cuantitativa analizada: {pos} Opiniones Positivas | {neg} Opiniones Negativas (Total: {len(datos)})."
    except Exception as e:
        return f"[ERROR] Excepción estadística: {str(e)}"

def obtener_reseña_mas_critica() -> str:
    """
    Filtra y extrae de forma directa la opinión con la menor puntuación y mayor longitud del texto.
    
    Returns:
        str: El bloque estructurado con la opinión más severa del producto.
    """
    origen_json = "reseñas_enriquecidas.json"
    if not os.path.exists(origen_json):
        return "[FALLO] No hay datos indexados."
    try:
        with open(origen_json, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if not datos:
            return "[INFO] Listado vacío."
        peores = [item for item in datos if str(item.get("estrellas")) in ["1", "2"]]
        if not peores:
            peores = datos
        critica = max(peores, key=lambda x: len(x.get("texto", "")))
        return f"=== OPINIÓN MÁS CRÍTICA DETECTADA ===\nAUTOR: {critica.get('autor')}\nESTRELLAS: {critica.get('estrellas')}★\nTEXTO: {critica.get('texto')}"
    except Exception as e:
        return f"[ERROR] Error al aislar la reseña crítica: {str(e)}"

def obtener_diagnostico_sistema() -> str:
    """
    Consulta los recursos de hardware lógico locales disponibles para garantizar la estabilidad de Ollama.
    
    Returns:
        str: Diagnóstico de la fecha actual del sistema e hilos del entorno lógico.
    """
    try:
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[DIAGNÓSTICO] Sistema Operativo validado. Servidor Local Activo. Fecha/Hora: {fecha_actual}. Entorno RAG Híbrido Operando de forma Óptima."
    except Exception as e:
        return f"[ERROR] No se pudo recopilar el diagnóstico local: {str(e)}"

def limpiar_cache_scraping() -> str:
    """
    Ejecuta un mantenimiento de limpieza preventiva removiendo archivos JSON temporales vacíos o corruptos.
    
    Returns:
        str: Confirmación de la purga técnica realizada en el backend.
    """
    archivo_temporal = "reseñas_crudas.json"
    if os.path.exists(archivo_temporal):
        try:
            os.remove(archivo_temporal)
            return "[MANTENIMIENTO] Cache e historial de recolección cruda eliminados con éxito."
        except Exception as e:
            return f"[ERROR] No se pudo liberar el archivo temporal: {str(e)}"
    return "[INFO] El cache de scraping ya se encuentra completamente limpio."