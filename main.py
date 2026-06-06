import os
import time
import sys
import gc
from llama_index.core.tools import FunctionTool
from extractor_especifico import ExtractorEspecifico  # Nuevo extractor por selectores nativos
from clasificador import ClasificadorReseñas          # Cerebro de clasificación IA local
from asistente import AsistenteAnaliticoHibrido
from indexador import IndexadorRAG

# IMPORTACIÓN MODULAR DEL CATÁLOGO DE FUNCIONES (Fase 2)
import funciones_locales

def iniciar_flujo_completo():
    print("=" * 70)
    print("     SISTEMA ENRIQUECIDO DE ANALÍTICA LOCAL (ORQUESTADOR SMART)     ")
    print("=" * 70)
    
    # SEPARACIÓN REAL DE ARCHIVOS: Flujo crudo vs enriquecido con metadatos de IA
    archivo_crudo = "reseñas_crudas.json"
    archivo_enriquecido = "reseñas_enriquecidas.json"
    ruta_db_local = "chroma_db"
    coleccion_local = "reviews_analizadas"
    
    # Condición inicial: Verifica si existe el archivo de base de datos físico de SQLite
    ejecutar_extraccion = not os.path.exists(os.path.join(ruta_db_local, "chroma.sqlite3"))

    if ejecutar_extraccion:
        print("\n[INFO] No se detectó ninguna base de datos previa. Iniciando configuración inicial...")
    else:
        print("\n[INFO] Base de datos local detectada. Accediendo directamente al asistente...")

    # BUCLE PRINCIPAL DE CONTROL (Mantiene el orquestador vivo para iterar múltiples URLs)
    while True:
        if ejecutar_extraccion:
            url_objetivo = input("\nIntroduce la URL del producto para analizar > ").strip()
            
            if not url_objetivo:
                print("[ERROR] No introdujiste una URL válida. Cancelando proceso.")
                return

            print("\n[PASO 1] Lanzando navegador automatizado de extracción específica...")
            # Limpieza preventiva para evitar colisiones de registros viejos
            if os.path.exists(archivo_crudo): os.remove(archivo_crudo)
            if os.path.exists(archivo_enriquecido): os.remove(archivo_enriquecido)

            # 1. Extracción de textos planos estructurados por CSS
            extractor = ExtractorEspecifico(archivo_salida=archivo_crudo)
            extractor.extraer(url_objetivo, scrolls=3)

            if not os.path.exists(archivo_crudo) or os.path.getsize(archivo_crudo) == 0:
                print("[ERROR] El proceso de extracción no generó datos. Intente de nuevo.")
                ejecutar_extraccion = True
                continue

            # 2. Inferencia y Enriquecimiento Semántico mediante Ollama local
            print("\n[PASO 1.5] Enriqueciendo reseñas con inteligencia artificial (Ollama)...")
            try:
                clasificador = ClasificadorReseñas()
                clasificador.procesar_pipeline(archivo_entrada=archivo_crudo, archivo_salida=archivo_enriquecido)
            except Exception as e:
                print(f"[ERROR CRÍTICO EN PIPELINE DE CLASIFICACIÓN]: {e}")
                ejecutar_extraccion = True
                continue

            print("\n[PASO 2] Sincronizando almacenamiento persistente en ChromaDB...")
            try:
                # El indexador lee formalmente el archivo generado por el clasificador
                indexador_instancia = IndexadorRAG(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
                indexador_instancia.construir_indice(archivo_enriquecido=archivo_enriquecido)
                print("[INFO] Éxito: Reseñas procesadas e inyectadas en ChromaDB.")
                ejecutar_extraccion = False # Transición exitosa hacia el entorno de chat
            except Exception as e:
                print(f"[ERROR CRÍTICO EN EL INDEXADOR]: {e}")
                return

            # --- PARCHE DE SEGURIDAD INTERMEDIO PARA WINDOWS ---
            print("\n⏳ Liberando descriptores de archivos y limpiando subprocesos...")
            gc.collect()   # Purgamos referencias de memoria muertas
            time.sleep(3)  # Pausa de sincronización física de disco duro para SQLite

        # [PASO 3] Inicialización de modelos locales y motores indexados (Vectores + BM25)
        print("\n[INFO] Inicializando modelos locales y motores (Vectores + BM25)...")
        
        try:
            asistente = AsistenteAnaliticoHibrido(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
        except Exception as e:
            if "default_tenant" in str(e):
                print("\n" + "-"*70)
                print("💡 [BLOQUEO DE HILOS DETECTADO EN WINDOWS]")
                print(" Las reseñas ya fueron extraídas e indexadas con absoluto éxito en 'chroma_db'.")
                print(" Para evitar el bloqueo de SQLite, el script se cerrará automáticamente.")
                print(" SOLUCIÓN: Vuelve a ejecutar 'python main.py' para entrar directo al chat.")
                print("-"*70 + "\n")
                return # Cierre controlado para liberar los recursos de disco
            else:
                print(f"[ERROR CRÍTICO AL INICIAR ASISTENTE]: {e}")
                print("Forzando reconfiguración integral...")
                ejecutar_extraccion = True
                continue

        print("\n" + "="*70)
        print("ENTORNO HÍBRIDO ACTIVO CON INTERCEPCIÓN DETERMINISTA (FASE 2)")
        print("="*70)
        print(" FILTROS RAG (PREFIJOS DIRECTOS):")
        print("  /interfaz      -> Aísla la categoría de Diseño y Estética del producto.")
        print("  /funcion       -> Filtra el Rendimiento Técnico y fallas de hardware.")
        print("  /negativos     -> Enfoca el contexto únicamente en opiniones críticas.")
        print("-" * 70)
        print(" CATÁLOGO DE ACCIONES DISPONIBLES (EJECUCIÓN DIRECTA):")
        print("  1. 'Guarda el reporte en un archivo txt' (Ejecuta guardar_reporte_txt)")
        print("  2. 'Exporta las opiniones a CSV'        (Ejecuta exportar_analisis_csv)")
        print("  3. 'Muestra la lista de reportes'       (Ejecuta listar_archivos_reportes)")
        print("  4. 'Calcula el promedio de estrellas'   (Ejecuta calcular_promedio_estrellas)")
        print("  5. 'Cuenta los sentimientos totales'    (Ejecuta contar_sentimientos_totales)")
        print("  6. 'Muestra la reseña más crítica'      (Ejecuta obtener_reseña_mas_critica)")
        print("  7. 'Dame el diagnóstico del sistema'    (Ejecuta obtener_diagnostico_sistema)")
   
        print("-" * 70)
        print(" COMANDOS DE CONTROL GLOBAL:")
        print("  /reiniciar     -> Purga la base vectorial in-place y pide otra URL.")
        print("  salir          -> Cierra la sesión y libera la memoria RAM del sistema.")
        print("="*70 + "\n")

        bandera_reinicio = False
        
        # Inicializamos el respaldo del reporte en la sesión actual
        ultimo_informe_rag = "No se ha generado ningún informe en esta sesión todavía. Realiza una consulta analítica primero."

        # UN SOLO BUCLE INTERACTIVO DEL CHAT CONTROLADO
        while True:
            entrada = input("Pregunta sobre las reseñas...> ").strip()
            
            if entrada.lower() in ["salir", "exit", "quit"]:
                print("[INFO] Finalizando sesión del asistente analítico local.")
                return # Cierre absoluto de la aplicación
                
            if not entrada:
                continue

            # SOLUCIÓN CONTROLADA PARA REINICIOS
            if entrada.startswith("/reiniciar"):
                print("\n" + "-" * 70)
                print("[REINICIO] Vaciando índices y preparando entorno para nuevo producto...")
                print("-" * 70)
                try:
                    asistente.cerrar_conexion()
                except Exception as e:
                    print(f"[ADVERTENCIA] Error en la rutina de limpieza: {e}")
                
                if os.path.exists(archivo_crudo): os.remove(archivo_crudo)
                if os.path.exists(archivo_enriquecido): os.remove(archivo_enriquecido)
                
                print("[INFO] Base de datos e historial limpios con éxito.")
                ejecutar_extraccion = True
                bandera_reinicio = True
                break 

            cat_filtro = None
            sent_filtro = None
            pregunta_final = entrada

            # Enrutamiento lógico de comandos por metadatos (Filtros rápidos)
            if entrada.startswith("/interfaz"):
                cat_filtro = "Diseño e Interfaz"
                pregunta_final = "Genera un reporte analítico sobre la percepción visual, ergonomía, estética y acabados del producto."
                print(f"[FILTRO APLICADO] Categoría: {cat_filtro}")
                
            elif entrada.startswith("/funcion"):
                cat_filtro = "Rendimiento y Caídas" 
                pregunta_final = "Genera un reporte técnico enfocado en el rendimiento operativo, conectividad y fallas mecánicas/lógicas."
                print(f"[FILTRO APLICADO] Categoría: {cat_filtro}")
                
            elif entrada.startswith("/negativos"):
                sent_filtro = "Negativo"
                pregunta_final = "Identifica de forma detallada la totalidad de quejas e inconformidades reportadas."
                print(f"[FILTRO APLICADO] Sentimiento: {sent_filtro}")

            print("[PROCESAMIENTO] Analizando intención (RAG Híbrido vs Local Interception)...")
            entrada_lower = entrada.lower()
            
            try:
                # ─── EVALUACIÓN DETERMINISTA DE FUNCIONES LOCALES (FASE 2) ───
                
                # [ACCIÓN 1] GUARDAR REPORTE EN TXT
                if any(p in entrada_lower for p in ["guardar", "txt", "guardar reporte"]) or entrada_lower == "1":
                    nombre_out = input("Introduce el nombre del archivo (por defecto: reporte_analisis.txt) > ").strip()
                    if not nombre_out: 
                        nombre_out = "reporte_analisis.txt"
                    
                    resultado_funcion = funciones_locales.guardar_reporte_txt(
                        contenido=str(ultimo_informe_rag), 
                        nombre_archivo=nombre_out
                    )
                    print(f"\n[INTERCEPCIÓN] Ejecutando guardar_reporte_txt de forma local:\n{resultado_funcion}\n")

                # [ACCIÓN 2] EXPORTAR OPINIONES A CSV
                elif any(p in entrada_lower for p in ["csv", "exportar", "opiniones a csv"]) or entrada_lower == "2":
                    resultado_funcion = funciones_locales.exportar_analisis_csv()
                    print(f"\n[INTERCEPCIÓN] Ejecutando exportar_analisis_csv:\n{resultado_funcion}\n")

                # [ACCIÓN 3] LISTAR ARCHIVOS DE REPORTES
                elif any(p in entrada_lower for p in ["lista de reportes", "listar", "archivos", "mostrar reportes"]) or entrada_lower == "3":
                    resultado_funcion = funciones_locales.listar_archivos_reportes()
                    print(f"\n[INTERCEPCIÓN] Ejecutando listar_archivos_reportes:\n{resultado_funcion}\n")

                # [ACCIÓN 4] CALCULAR PROMEDIO DE ESTRELLAS
                elif any(p in entrada_lower for p in ["promedio", "estrellas", "calcular promedio"]) or entrada_lower == "4":
                    resultado_funcion = funciones_locales.calcular_promedio_estrellas()
                    print(f"\n[INTERCEPCIÓN] Ejecutando calcular_promedio_estrellas:\n{resultado_funcion}\n")

                # [ACCIÓN 5] CONTAR SENTIMIENTOS TOTALES
                elif any(p in entrada_lower for p in ["sentimientos", "conteo", "sentimientos totales"]) or entrada_lower == "5":
                    resultado_funcion = funciones_locales.contar_sentimientos_totales()
                    print(f"\n[INTERCEPCIÓN] Ejecutando contar_sentimientos_totales:\n{resultado_funcion}\n")

                # [ACCIÓN 6] MOSTRAR LA RESEÑA MÁS CRÍTICA
                elif any(p in entrada_lower for p in ["crítica", "peor", "mas critica", "reseña critica"]) or entrada_lower == "6":
                    resultado_funcion = funciones_locales.obtener_reseña_mas_critica()
                    print(f"\n[INTERCEPCIÓN] Ejecutando obtener_reseña_mas_critica:\n{resultado_funcion}\n")

                # [ACCIÓN 7] DAME EL DIAGNÓSTICO DEL SISTEMA
                elif any(p in entrada_lower for p in ["diagnóstico", "sistema", "diagnostico"]) or entrada_lower == "7":
                    resultado_funcion = funciones_locales.obtener_diagnostico_sistema()
                    print(f"\n[INTERCEPCIÓN] Ejecutando obtener_diagnostico_sistema:\n{resultado_funcion}\n")

                # [ACCIÓN 8] LIMPIAR CACHE DE SCRAPING
                elif any(p in entrada_lower for p in ["limpiar", "cache", "scraping"]) or entrada_lower == "8":
                    resultado_funcion = funciones_locales.limpiar_cache_scraping()
                    print(f"\n[INTERCEPCIÓN] Ejecutando limpiar_cache_scraping:\n{resultado_funcion}\n")

                # ─── FLUJO REGULAR DEL RAG HÍBRIDO (SI NO ES NINGUNA FUNCIÓN) ───
                else:
                    resultado = asistente.consultar(
                        pregunta=pregunta_final, 
                        filtro_categoria=cat_filtro, 
                        filtro_sentimiento=sent_filtro
                    )
                    # Respaldamos la respuesta generada para la Acción 1
                    ultimo_informe_rag = resultado 
                    print(f"\n[INFORME GENERADO POR RAG]\n{resultado}\n")
                    
            except Exception as e:
                print(f"[ERROR] Estado de ejecución controlado: {e}\n")
                
            print("-" * 70)

        # Si rompimos el ciclo por orden de /reiniciar, regresa arriba a pedir la nueva URL
        if bandera_reinicio:
            continue

if __name__ == "__main__":
    iniciar_flujo_completo()