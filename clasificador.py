import json
import os
import re
import time
from llama_index.llms.ollama import Ollama

class ClasificadorReseñas:
    def __init__(self, modelo="qwen2.5:1.5b"):
        """
        Inicializa el clasificador configurando el modelo local de Ollama
        con el formato JSON nativo activo para garantizar costo cero.
        """
        self.llm = Ollama(
            model=modelo, 
            request_timeout=60.0, 
            additional_kwargs={"format": "json"}
        )

    def _generar_prompt(self, titulo: str, cuerpo: str) -> str:
        """Genera un prompt con instrucciones estrictas y delimitadores claros."""
        return f"""
Analiza la siguiente opinión de un comprador para determinar su sentimiento y su categoría analítica precisa.

DATOS DE LA OPINIÓN:
- Título/Asunto: "{titulo}"
- Comentario Completo: "{cuerpo}"

INSTRUCCIONES DE CLASIFICACIÓN:
1. "sentimiento": Evalúa el tono emocional dominante o el balance de la reseña. Debe ser únicamente uno de estos tres valores: "Positivo", "Negativo" o "Neutral".

2. "categoria": Identifica el núcleo temático principal de la opinión. Si la reseña menciona satisfacción general pero incluye una queja o inconformidad explícita sobre envíos, componentes o empaques, prioriza la categoría de la queja para control de daños. Debe ser únicamente uno de estos valores específicos:
   - "Rendimiento y Caídas" (Bugs, congelamientos, lentitud, desconexiones, sobrecalentamiento o fallas críticas de hardware/software).
   - "Diseño e Interfaz" (Estética, color, comodidad, ergonomía, acabados visuales o apariencia del producto).
   - "Materiales y Durabilidad" (Calidad de los plásticos, resistencia a golpes, desgaste prematuro o componentes que se sienten frágiles).
   - "Logística y Envío" (Tiempos de entrega, retrasos, velocidad de paquetería, distribución o problemas con el despacho de la orden).
   - "Embalaje del Producto" (Estado de la caja original, sellos de autenticidad rotos, protección interna o falta de accesorios/cables dentro de la caja).
   - "Precio y Valor" (Relación calidad-precio, costo, ofertas, si es caro/barato o si vale la pena la inversión económica).
   - "Soporte Técnico" (Atención al cliente, garantías, cambios, devoluciones, reembolsos o experiencia directa con el vendedor).
   - "Funcionalidad" (Si cumple o no con las características técnicas básicas prometidas en la descripción de venta, emparejamiento o controles de uso).
   - "General" (Únicamente si es una opinión ambigua, vacía o extremadamente corta que no encaja en ninguna de las clasificaciones anteriores).

RESTRICCIÓN ABSOLUTA:
Devuelve EXCLUSIVAMENTE un objeto JSON válido con las llaves "sentimiento" y "categoria". No agregues texto explicativo adicional ni antes ni después del objeto.

Ejemplo de salida estricta:
{{"sentimiento": "Negativo", "categoria": "Logística y Envío"}}
""".strip()

    def _limpiar_y_parsear_json(self, texto_crudo: str) -> dict:
        """
        Limpia de forma agresiva cualquier residuo de texto o marcas de Markdown
        para aislar el objeto JSON puro y parsearlo de forma segura.
        """
        texto_limpio = texto_crudo.strip()
        
        # Eliminar bloques de código markdown como ```json ... ``` o ``` ... ```
        texto_limpio = re.sub(r"^```json\s*", "", texto_limpio, flags=re.IGNORECASE)
        texto_limpio = re.sub(r"^```\s*", "", texto_limpio, flags=re.IGNORECASE)
        texto_limpio = re.sub(r"\s*```$", "", texto_limpio, flags=re.IGNORECASE)
        texto_limpio = texto_limpio.strip()
        
        # Intentar encontrar el primer '{' y el último '}' si el LLM incluyó texto extra
        match = re.search(r'\{.*\}', texto_limpio, re.DOTALL)
        if match:
            texto_limpio = match.group(0)
            
        return json.loads(texto_limpio)

    def clasificar_reseña_con_reintentos(self, titulo: str, texto: str, max_reintentos: int = 3) -> dict:
        """
        Intenta clasificar una reseña. Si el JSON falla, reintenta de forma automática
        aplicando una pausa ligera para permitir que Ollama de forma local estabilice el hilo.
        """
        prompt = self._generar_prompt(titulo, texto)
        
        # Diccionario de mapeo extendido para estandarizar respuestas del LLM local
        categorias_validas = {
            "Rendimiento y Caídas", "Diseño e Interfaz", "Materiales y Durabilidad",
            "Logística y Envío", "Embalaje del Producto", "Precio y Valor", 
            "Soporte Técnico", "Funcionalidad", "General"
        }
        
        for intento in range(max_reintentos):
            try:
                respuesta = self.llm.complete(prompt).text
                datos_ia = self._limpiar_y_parsear_json(respuesta)
                
                if "sentimiento" in datos_ia and "categoria" in datos_ia:
                    # Formateo estricto de valores para evitar inconsistencias en base de datos
                    sentimiento = str(datos_ia["sentimiento"]).strip().capitalize()
                    categoria = str(datos_ia["categoria"]).strip()
                    
                    # Corrección en caso de ligeras variaciones de capitalización o formato del LLM
                    categoria_corregida = next(
                        (c for c in categorias_validas if c.lower() == categoria.lower()), 
                        "General"
                    )
                    
                    if sentimiento not in ["Positivo", "Negativo", "Neutral"]:
                        sentimiento = "Neutral"
                        
                    return {"sentimiento": sentimiento, "categoria": categoria_corregida}
                    
                raise KeyError("El JSON devuelto no contiene las llaves requeridas.")
                
            except Exception as e:
                print(f"[REINTENTO] Intento {intento + 1}/{max_reintentos} fallido. [Detalle: {e}]")
                time.sleep(1)
                
        raise RuntimeError("No se pudo obtener un JSON estructurado válido tras los reintentos.")

    def procesar_pipeline(self, archivo_entrada="reseñas_crudas.json", archivo_salida="reseñas_enriquecidas.json"):
        """
        Lee el archivo de la fase de scraping, ejecuta la clasificación por lotes
        y genera el dataset final enriquecido para el RAG.
        """
        if not os.path.exists(archivo_entrada):
            print(f"[ERROR CRÍTICO] No existe el archivo '{archivo_entrada}'. Primero ejecuta tu extractor.")
            return

        with open(archivo_entrada, "r", encoding="utf-8") as f:
            reseñas_crudas = json.load(f)

        print(f"[OLLAMA ACTIVADO] Procesando {len(reseñas_crudas)} reseñas reales del archivo crudo...")
        reseñas_enriquecidas = []

        for index, item in enumerate(reseñas_crudas):
            autor = item.get("autor", "Anónimo")
            print(f"[PROCESANDO] [{index + 1}/{len(reseñas_crudas)}] Analizando opinión de: {autor}")
            
            titulo = item.get("titulo_comentario", "Sin título")
            cuerpo_texto = item.get("texto", "")
            
            try:
                datos_ia = self.clasificar_reseña_con_reintentos(titulo, cuerpo_texto)
                sentimiento_final = datos_ia["sentimiento"]
                categoria_final = datos_ia["categoria"]
                
            except Exception:
                print(f"[FALLO SEGURO] No se pudo estructurar el elemento. Aplicando valores por defecto.")
                sentimiento_final = "Neutral"
                categoria_final = "General"

            # Reconstrucción manteniendo el ID de origen si existe de forma intacta
            id_final = item.get("id", item.get("id_origen", f"amazon_0735_{index}"))

            item_enriquecido = {
                "id": id_final,
                "autor": autor,
                "titulo_comentario": titulo,
                "texto": cuerpo_texto,
                "estrellas": item.get("estrellas", None),
                "fuente": item.get("fuente", "Desconocida"),
                "metadatos": {
                    "sentimiento": sentimiento_final,
                    "categoria": categoria_final,
                    "fecha_publicacion": item.get("fecha_publicacion", "")
                }
            }
            reseñas_enriquecidas.append(item_enriquecido)

        with open(archivo_salida, "w", encoding="utf-8") as f:
            json.dump(reseñas_enriquecidas, f, ensure_ascii=False, indent=4)
            
        print(f"\n[PIPELINE COMPLETADO]")
        print(f"[INFO] Dataset enriquecido guardado con éxito en: '{archivo_salida}'")

if __name__ == "__main__":
    analizador = ClasificadorReseñas()
    analizador.procesar_pipeline()