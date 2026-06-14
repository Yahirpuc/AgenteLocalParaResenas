
import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

class ExtractorEspecifico:
    # Corrección de inicialización por defecto para asegurar la persistencia cruda
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
        print(f"\n💾 [ÉXITO] Se extrajeron {len(nuevos_datos)} reseñas legítimas en bruto.")
        print(f"📊 Archivo generado con éxito en: '{self.archivo_salida}' ({len(datos_existentes)} elementos).")

    def extraer(self, url: str, scrolls: int = 3):
        print(f"\n🚀 Lanzando navegador automatizado para extracción específica...")
        reseñas_raspadas = []
        ruta_perfil = os.path.join(os.getcwd(), "sesion_playwright")

        # Detectar la plataforma según la URL
        if "amazon" in url.lower():
            plataforma = "amazon"
            print("📦 Plataforma detectada de forma automática: AMAZON")
        elif "mercadolibre" in url.lower():
            plataforma = "mercadolibre"
            print("💛 Plataforma detectada de forma automática: MERCADO LIBRE")
        else:
            print("⚠️ [ERROR] URL no soportada. Este extractor solo procesa Amazon y Mercado Libre.")
            return

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
                print("🛑 ¡PAUSA CONTROLADA DE NAVEGACIÓN MANUAL!")
                print("1. Ve a la pantalla del navegador.")
                print("2. IMPORTANTE: Entra a la sección exclusiva de opiniones.")
                print("   (Dale clic a 'Ver todas las opiniones' o 'Ver más opiniones').")
                print("3. Asegúrate de que las reseñas extendidas se vean en pantalla.")
                print("========================================================")
                
                input("\n⌨️ Presiona [ENTER] aquí en la terminal cuando estés parado en la sección de opiniones...")

                print("\n🔄 Sincronizando e interactuando con los elementos de la página...")
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(1500)

                # --- INTERACCIÓN ESPECÍFICA PARA MERCADO LIBRE ---
                if plataforma == "mercadolibre":
                    print("[MERCADO LIBRE] Buscando y expandiendo botones 'Leer más' ocultos...")
                    try:
                         botones_leer_mas = page.query_selector_all('text="Leer más"')
                         for boton in botones_leer_mas:
                             if boton.is_visible():
                                 boton.click(timeout=1000)
                                 page.wait_for_timeout(200)
                         print(f"✨ Se expandieron {len(botones_leer_mas)} comentarios largos.")
                    except Exception:
                        pass

                print("\n🔄 Ejecutando scrolls dinámicos de carga profunda...")
                for i in range(scrolls):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    page.wait_for_timeout(2000)

                # --- EXTRACCIÓN MEDIANTE SELECTORES CSS NATIVOS BLINDADOS ---
                print("[PROCESAMIENTO] Ejecutando consultas estructuradas sobre el DOM...")
                
                if plataforma == "amazon":
                    script_extractor = """
                    () => {
                        let data = [];
                        let bloques = document.querySelectorAll('[data-hook="review"]');
                        
                        bloques.forEach((bloque, i) => {
                            let elAutor = bloque.querySelector('.a-profile-name');
                            let elTitulo = bloque.querySelector('[data-hook="review-title"]');
                            let elTexto = bloque.querySelector('[data-hook="review-body"]');
                            let elEstrellas = bloque.querySelector('.a-icon-alt');

                            let autor = elAutor ? elAutor.innerText.trim() : "Comprador Anónimo";
                            let titulo = elTitulo ? elTitulo.innerText.trim() : "Opinión Extraída";
                            let texto = elTexto ? elTexto.innerText.trim() : "";
                            
                            if (titulo.includes("de 5 estrellas")) {
                                titulo = titulo.split("\\n").pop();
                            }

                            let estrellas = 5;
                            if (elEstrellas) {
                                let match = elEstrellas.innerText.match(/([1-5])/);
                                if (match) estrellas = parseInt(match[0]);
                            }

                            if (texto.length > 5) {
                                data.push({
                                    "index": i,
                                    "autor": autor,
                                    "titulo_comentario": titulo,
                                    "texto": texto,
                                    "estrellas": estrellas
                                });
                            }
                        });
                        return data;
                    }
                    """
                
                elif plataforma == "mercadolibre":
                    script_extractor = """
                    () => {
                        let data = [];
                        let bloques = document.querySelectorAll('.ui-review-capability-comments__comment, [class*="comment-container" i], article');
                        
                        let index = 0;
                        bloques.forEach((bloque) => {
                            let elTexto = bloque.querySelector('p, .ui-review-capability-comments__comment__content');
                            if (!elTexto) return;
                            
                            let texto = elTexto.innerText.trim();
                            
                            let estrellas = 5;
                            let elEstrellas = bloque.querySelector('[class*="rating" i], [aria-label*="estrellas" i]');
                            if (elEstrellas) {
                                let label = elEstrellas.getAttribute('aria-label') || elEstrellas.innerText;
                                let match = label.match(/([1-5])/);
                                if (match) estrellas = parseInt(match[0]);
                            }

                            let autor = "Comprador de Mercado Libre";

                            if (texto.length > 5 && !texto.toUpperCase().includes("ÚTIL")) {
                                data.push({
                                    "index": index++,
                                    "autor": autor,
                                    "titulo_comentario": "Opinión de Mercado Libre",
                                    "texto": texto,
                                    "estrellas": estrellas
                                });
                            }
                        });
                        return data;
                    }
                    """

                opiniones_detectadas = page.evaluate(script_extractor)

                for op in opiniones_detectadas:
                    reseñas_raspadas.append({
                        "id": f"{plataforma}_{datetime.now().strftime('%M%S')}_{op['index']}",
                        "autor": op["autor"],
                        "titulo_comentario": op["titulo_comentario"],
                        "texto": op["texto"],
                        "estrellas": op["estrellas"],
                        "fuente": url,
                        "fecha_publicacion": datetime.now().strftime("%Y-%m-%d")
                    })

            except Exception as e:
                print(f"❌ Error crítico durante la extracción estructurada: {e}")
            finally:
                context.close()

        if reseñas_raspadas:
            self._guardar_json(reseñas_raspadas)
        else:
            print("⚠️ [ADVERTENCIA] No se capturaron reseñas. Asegúrate de estar parado en la página de comentarios completa.")

if __name__ == "__main__":
    url_test = input("Ingresa URL de prueba (Amazon/MercadoLibre): ").strip()
    if url_test:
        ex = ExtractorEspecifico()
        ex.extraer(url_test)