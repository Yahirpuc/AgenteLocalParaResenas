import json
import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

class ExtractorUniversal:
    def __init__(self, archivo_salida="reseñas_crudas.json"):
        self.archivo_salida = archivo_salida

    def _guardar_json(self, nuevos_datos: list[dict]):
        datos_existentes = []
        if os.path.exists(self.archivo_salida):
            with open(self.archivo_salida, "r", encoding="utf-8") as f:
                try:
                    datos_existentes = json.load(f)
                except json.JSONDecodeError:
                    datos_existentes = []

        datos_existentes.extend(nuevos_datos)
        with open(self.archivo_salida, "w", encoding="utf-8") as f:
            json.dump(datos_existentes, f, ensure_ascii=False, indent=4)
        print(f"\n💾 Éxito: Se extrajeron {len(nuevos_datos)} reseñas reales.")
        print(f"📊 Total acumulado en archivo: {len(datos_existentes)} elementos.")

    def extraer(self, url: str, scrolls: int = 3):
        print(f"\n🚀 Iniciando navegador universal en modo inteligente...")
        reseñas_raspadas = []
        ruta_perfil = os.path.join(os.getcwd(), "sesion_playwright")

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=ruta_perfil,
                headless=False,
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                print("\n========================================================")
                print("🛑 ¡PAUSA DE CONTROL MANUAL ACTIVADA!")
                print("1. Ve al navegador y busca la sección donde estén los comentarios.")
                print("2. Resuelve captchas, inicia sesión o navega libremente si es necesario.")
                print("3. Deja los comentarios visibles en la pantalla.")
                print("========================================================")
                
                input("\n⌨️ Presiona [ENTER] aquí en la terminal cuando los comentarios estén en pantalla...")

                # CRÍTICO: Esperamos a que el nuevo contexto/página se estabilice tras tus clics manuales
                print("\n🔄 Sincronizando estado de la página...")
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(1000)

                print("\n🔄 Ejecutando scrolls dinámicos para forzar la carga de comentarios ocultos...")
                for i in range(scrolls):
                    print(f"📜 Haciendo scroll de carga {i+1}/{scrolls}...")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    page.wait_for_timeout(2500)

                # --- ALGORITMO HEURÍSTICO UNIVERSAL ---
                # Analiza la estructura semántica de cualquier sitio web al vuelo
                print("[PROCESAMIENTO] Analizando el DOM en busca de patrones de comentarios...")
                
                script_heuristico = """
                () => {
                    let resultados = [];
                    // Buscar elementos de texto que coincidan con etiquetas de reseñas comunes
                    let elementosTexto = document.querySelectorAll('p, span, div.review-text, .comment-text, [class*="comment" i], [class*="review" i]');
                    
                    let index = 0;
                    elementosTexto.forEach(el => {
                        let texto = el.innerText ? el.innerText.trim() : "";
                        // Filtro de longitud para asegurar consistencia de contenido analítico
                        if (texto.length > 25 && texto.length < 1200) {
                            
                            // Intentamos rastrear un contenedor padre inmediato que agrupe la reseña
                            let contenedor = el.closest('article, li, [class*="item" i], [class*="review" i], [class*="comment" i]') || el.parentElement;
                            
                            // Buscar métricas de calificación (estrellas o puntuaciones) en la vecindad del nodo
                            let estrellas = null;
                            let textoContenedor = contenedor ? contenedor.innerText : "";
                            let matchEstrellas = textoContenedor.match(/([1-5])\s*(de|=)?\s*5|★+/g);
                            if (matchEstrellas) {
                                let num = matchEstrav = matchEstrellas[0].match(/[1-5]/);
                                estrellas = num ? parseInt(num[0]) : (matchEstrellas[0].includes('★') ? matchEstrellas[0].length : null);
                            }

                            // Intentamos inferir la identidad del autor
                            let autor = "Comprador Anónimo";
                            let elAutor = contenedor ? contenedor.querySelector('[class*="author" i], [class*="user" i], [class*="name" i]') : null;
                            if (elAutor && elAutor.innerText.trim().length < 50) {
                                autor = elAutor.innerText.trim();
                            }

                            // Filtrar duplicados redundantes del DOM antes de consolidar
                            if (!resultados.some(r => r.texto === texto)) {
                                resultados.push({
                                    "index": index++,
                                    "autor": autor,
                                    "titulo_comentario": "Opinión Extraída",
                                    "texto": texto,
                                    "estrellas": estrellas || 5
                                });
                            }
                        }
                    });
                    return resultados;
                }
                """
                
                opiniones_detectadas = page.evaluate(script_heuristico)
                
                # Deducción dinámica de origen basándose en el dominio de la URL provista
                dominio = url.split("//")[-1].split("/")[0].replace("www.", "")
                plataforma_id = dominio.split(".")[0]

                # --- CONSOLIDACIÓN COMPATIBLE CON TU INDEXADOR ---
                dominio = url.split("//")[-1].split("/")[0].replace("www.", "")
                plataforma_id = dominio.split(".")[0]

                for op in opiniones_detectadas:
                    reseñas_raspadas.append({
                        "id": f"{plataforma_id}_{datetime.now().strftime('%M%S')}_{op['index']}",
                        "autor": op["autor"],
                        "titulo_comentario": op["titulo_comentario"],
                        "texto": op["texto"],
                        "estrellas": op["estrellas"],
                        "fuente": url,
                        "metadatos": {
                            "sentimiento": "Positivo" if op["estrellas"] >= 4 else "Negativo",
                            "categoria": "Rendimiento y Caídas" if op["estrellas"] <= 2 else "Diseño e Interfaz",
                            "fecha_publicacion": datetime.now().strftime("%Y-%m-%d")
                        }
                    })

            except Exception as e:
                print(f"❌ Error durante la extracción universal: {e}")
            finally:
                context.close()

        if reseñas_raspadas:
            self._guardar_json(reseñas_raspadas)
        else:
            print("⚠️ No se detectaron bloques de comentarios legibles en esta estructura web.")