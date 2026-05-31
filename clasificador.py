from datetime import datetime
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
        """Genera un prompt estructurado bajo formato Few-Shot para Qwen."""
        return f"""
Analiza la siguiente opinión de un comprador para determinar su sentimiento y su categoría analítica precisa.

DATOS DE LA OPINIÓN:
- Título/Asunto: "{titulo}"
- Comentario Completo: "{cuerpo}"

INSTRUCCIONES DE CLASIFICACIÓN:
1. "sentimiento": Debe ser únicamente uno de estos tres valores: "Positivo", "Negativo" o "Neutral".
2. "categoria": Identifica el núcleo temático principal. Valores específicos válidos:
   - "Rendimiento y Caídas" (Bugs, congelamientos, lentitud, fallas de hardware/software).
   - "Diseño e Interfaz" (Estética, color, comodidad, ergonomía, acabados visuales).
   - "Materiales y Durabilidad" (Calidad de plásticos, resistencia a golpes, desgaste).
   - "Logística y Envío" (Tiempos de entrega, retrasos, paquetería).
   - "Embalaje del Producto" (Estado de la caja original, sellos rotos, falta de accesorios).
   - "Precio y Valor" (Relación calidad-precio, costo, si vale la pena la inversión).
   - "Soporte Técnico" (Atención al cliente, garantías, cambios, devoluciones).
   - "Funcionalidad" (Si cumple con las características básicas prometidas en la descripción).
   - "General" (Opiniones ambiguas, vacías o extremadamente cortas).

RESTRICCIÓN ABSOLUTA:
Devuelve EXCLUSIVAMENTE un objeto JSON válido con las llaves "sentimiento" y "categoria". No agregues texto adicional.

EJEMPLO DE SALIDA ESTRICTA:
{{"sentimiento": "Negativo", "categoria": "Rendimiento y Caídas"}}
""".strip()

    def _limpiar_y_parsear_json(self, texto_crudo: str) -> dict:
        """Aisla el objeto JSON puro y lo parsea de forma segura."""
        texto_limpio = texto_crudo.strip()
        
        texto_limpio = re.sub(r"^```json\s*", "", texto_limpio, flags=re.IGNORECASE)
        texto_limpio = re.sub(r"^```\s*", "", texto_limpio, flags=re.IGNORECASE)
        texto_limpio = re.sub(r"\s*```$", "", texto_limpio, flags=re.IGNORECASE)
        texto_limpio = texto_limpio.strip()
        
        match = re.search(r'\{.*\}', texto_limpio, re.DOTALL)
        if match:
            texto_limpio = match.group(0)
            
        return json.loads(texto_limpio)

    def clasificar_reseña_con_reintentos(self, titulo: str, texto: str, max_reintentos: int = 3) -> dict:
        """Intenta clasificar una reseña mitigando caídas de Ollama."""
        prompt = self._generar_prompt(titulo, texto)
        
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
                    sentimiento = str(datos_ia["sentimiento"]).strip().capitalize()
                    categoria = str(datos_ia["categoria"]).strip()
                    
                    categoria_corregida = next(
                        (c for c in categorias_validas if c.lower() == categoria.lower()), 
                        "General"
                    )
                    
                    if sentimiento not in ["Positivo", "Negativo", "Neutral"]:
                        sentimiento = "Neutral"
                        
                    # CORRECCIÓN DE SINTAXIS: Se removió la variable fantasma en inglés 'category_corregida'
                    return {"sentimiento": sentimiento, "categoria": categoria_corregida}
                
                raise KeyError("Estructura JSON incompleta.")
                
            except Exception as e:
                print(f"[REINTENTO] {intento + 1}/{max_reintentos} fallido. [Error: {e}]")
                time.sleep(1)
                
        raise RuntimeError("Inferencia fallida tras reintentos continuos.")

    def procesar_pipeline(self, archivo_entrada="reseñas_crudas.json", archivo_salida="reseñas_enriquecidas.json"):
        """Estructura y enriquece el dataset vinculando de forma segura las llaves del Extractor."""
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
                print(f"[FALLO SEGURO] Aplicando valores por defecto.")
                sentimiento_final = "Neutral"
                categoria_final = "General"

            # CORRECCIÓN LÓGICA: Jalamos prioritariamente la fecha capturada por el extractor específico
            id_final = item.get("id", item.get("id_origen", f"local_{index}"))
            fecha_final = item.get("fecha_publicacion", datetime.now().strftime("%Y-%m-%d"))

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
                    "fecha_publicacion": fecha_final
                }
            }
            reseñas_enriquecidas.append(item_enriquecido)

        with open(archivo_salida, "w", encoding="utf-8") as f:
            json.dump(reseñas_enriquecidas, f, ensure_ascii=False, indent=4)
            
        print(f"\n[PIPELINE COMPLETADO] Dataset enriquecido guardado con éxito en: '{archivo_salida}'")

if __name__ == "__main__":
    analizador = ClasificadorReseñas()
    analizador.procesar_pipeline()