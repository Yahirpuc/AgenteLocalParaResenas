import json
import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

class ExtractorUniversal:
    def __init__(self, archivo_salida="reseñas_crudas.json"):
        self.archivo_salida = archivo_salida
        
        # Selectores optimizados para Amazon y Mercado Libre
        self.configuraciones_web = {
            "mercadolibre": {
                "contenedor": "article.ui-review-view",
                "autor": ".ui-review-view__author",
                "titulo": "h3.ui-review-view__title",
                "texto": "p.ui-review-view__description",
                "estrellas": "p.ui-review-view__rating",
            },
            "amazon": {
                "contenedor": "[data-hook='review'], .review",
                "autor": ".a-profile-name",
                "titulo": "[data-hook='review-title'], .review-title-content",
                "texto": "[data-hook='review-body'], .review-text-content",
                "estrellas": ".a-icon-alt",
            }
        }

    def _detectar_plataforma(self, url: str) -> str:
        if "mercadolibre" in url:
            return "mercadolibre"
        elif "amazon" in url:
            return "amazon"
        return "genérico"

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
        plataforma = self._detectar_plataforma(url)
        if plataforma == "genérico":
            print("⚠️ Plataforma no soportada.")
            return

        config = self.configuraciones_web[plataforma]
        print(f"\n🚀 Iniciando navegador persistente para {plataforma.upper()}...")
        reseñas_raspadas = []

        # Carpeta local que guardará tus cookies e inicios de sesión de Amazon/ML
        ruta_perfil = os.path.join(os.getcwd(), "sesion_playwright")

        with sync_playwright() as p:
            # Lanzamos el navegador visible para que puedas interactuar
            context = p.chromium.launch_persistent_context(
                user_data_dir=ruta_perfil,
                headless=False,  # OBLIGATORIO en False para que veas la pantalla
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                # 1. Vamos primero a la URL objetivo
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # 2. 🛑 PAUSA INTERACTIVA MÁGICA
                print("\n========================================================")
                print("🛑 ¡PAUSA DE CONTROL MANUAL ACTIVADA!")
                print("1. Ve a la ventana del navegador que se acaba de abrir.")
                print("2. Inicia sesión si te lo pide, o resuelve el captcha de Amazon.")
                print("3. Asegúrate de estar viendo las reseñas en la pantalla.")
                print("========================================================")
                
                # El script se congela aquí hasta que des ENTER en la terminal de VS Code
                input("\n⌨️ Presiona [ENTER] aquí en la terminal CUANDO YA ESTÉS LISTO para raspar las reseñas...")
                
                print("\n🔄 Continuando de forma autónoma. Realizando scrolls...")
                # Lógica de scrolls dinámicos tras tu banderazo de salida
                for i in range(scrolls):
                    print(f"📜 Haciendo scroll de carga {i+1}/{scrolls}...")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    page.wait_for_timeout(2000)

                # 3. Captura e Ingesta de datos
                bloques = page.query_selector_all(config["contenedor"])
                print(f"🎯 Bloques reales detectados en el DOM: {len(bloques)}")

                for index, bloque in enumerate(bloques):
                    el_texto = bloque.query_selector(config["texto"])
                    texto = el_texto.inner_text().strip() if el_texto else ""

                    if not texto:
                        continue

                    el_titulo = bloque.query_selector(config["titulo"])
                    titulo = el_titulo.inner_text().strip() if el_titulo else "Opinión general"

                    el_autor = bloque.query_selector(config["autor"])
                    autor = el_autor.inner_text().strip() if el_autor else "Comprador Anónimo"

                    el_estrellas = bloque.query_selector(config["estrellas"])
                    estrellas_txt = el_estrellas.inner_text().strip() if el_estrellas else "0"
                    numeros = re.findall(r'\d+', estrellas_txt)
                    estrellas = int(numeros[0]) if numeros else None

                    reseñas_raspadas.append({
                        "id_origen": f"{plataforma}_{datetime.now().strftime('%M%S')}_{index}",
                        "autor": autor,
                        "titulo_comentario": titulo,
                        "texto": texto,
                        "estrellas": estrellas,
                        "fecha_publicacion": datetime.now().strftime("%Y-%m-%d"),
                        "fuente": url
                    })

            except Exception as e:
                print(f"❌ Error durante la extracción: {e}")
            finally:
                context.close()

        if reseñas_raspadas:
            self._guardar_json(reseñas_raspadas)
        else:
            print("⚠️ No se pudieron guardar datos. Verifica que las reseñas fueran visibles al dar ENTER.")

if __name__ == "__main__":
    extractor = ExtractorUniversal()
    
    # URL de opiniones del control de PS5 en Amazon
    url_opiniones = "https://www.amazon.com.mx/Control-Inalámbrico-DualSenseTM-Galactic-Garantía/product-reviews/B0CQKL27GN/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews"
    
    extractor.extraer(url_opiniones, scrolls=3)