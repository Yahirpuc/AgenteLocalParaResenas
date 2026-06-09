import os
import time
import sys
import gc
import uuid
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

    # Registro y empaquetamiento modular a herramientas de LlamaIndex (Fase 2)
    herramientas_fc = [
        FunctionTool.from_defaults(
            fn=funciones_locales.guardar_reporte_txt,
            name="guardar_reporte_txt",
            description="Útil para guardar o exportar el reporte actual en un archivo de texto (.txt). Ejecuta esta función sin argumentos si el usuario no proporciona detalles adicionales."
        ),
        FunctionTool.from_defaults(
            fn=funciones_locales.exportar_analisis_csv,
            name="exportar_analisis_csv",
            description="Exporta las opiniones a un archivo CSV. Llama a esta función SIN argumentos."
        ),
        FunctionTool.from_defaults(
            fn=funciones_locales.listar_archivos_reportes,
            name="listar_archivos_reportes",
            description="Muestra la lista de reportes o archivos generados. Llama a esta función SIN argumentos."
        ),
        FunctionTool.from_defaults(fn=funciones_locales.calcular_promedio_estrellas),
        FunctionTool.from_defaults(fn=funciones_locales.contar_sentimientos_totales),
        FunctionTool.from_defaults(
            fn=funciones_locales.obtener_resena_mas_critica, 
            name="obtener_resena_mas_critica",
            description="Busca y devuelve la reseña más crítica o peor evaluada. Llama a esta función SIN argumentos."
        ),
        FunctionTool.from_defaults(fn=funciones_locales.obtener_diagnostico_sistema),
        FunctionTool.from_defaults(fn=funciones_locales.limpiar_cache_scraping)
    ]
    
    # BUCLE PRINCIPAL DE CONTROL 
    while True:
        if ejecutar_extraccion:
            url_objetivo = input("\nIntroduce la URL del producto para analizar> ").strip()
            
            if not url_objetivo:
                print("[ERROR] No introdujiste una URL válida. Cancelando proceso.")
                return

            print("\n[PASO 1] Lanzando navegador automatizado de extracción específica...")
            if os.path.exists(archivo_crudo): os.remove(archivo_crudo)
            if os.path.exists(archivo_enriquecido): os.remove(archivo_enriquecido)

            extractor = ExtractorEspecifico(archivo_salida=archivo_crudo)
            extractor.extraer(url_objetivo, scrolls=3)

            if not os.path.exists(archivo_crudo) or os.path.getsize(archivo_crudo) == 0:
                print("[ERROR] El proceso de extracción no generó datos. Intente de nuevo.")
                ejecutar_extraccion = True
                continue

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
                indexador_instancia = IndexadorRAG(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
                indexador_instancia.construir_indice(archivo_enriquecido=archivo_enriquecido)
                print("[INFO] Éxito: Reseñas procesadas e inyectadas en ChromaDB.")
                ejecutar_extraccion = False 
            except Exception as e:
                print(f"[ERROR CRÍTICO EN EL INDEXADOR]: {e}")
                return

            print("\n⏳ Liberando descriptores de archivos y limpiando subprocesos...")
            gc.collect()   
            time.sleep(3)  

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
                return 
            else:
                print(f"[ERROR CRÍTICO AL INICIAR ASISTENTE]: {e}")
                print("Forzando reconfiguración integral...")
                ejecutar_extraccion = True
                continue

        print("\n" + "="*70)
        print("ENTORNO HÍBRIDO ACTIVO CON LLAMADAS A FUNCIÓN (FASE 2)")
        print("="*70)
        
        # --- [AÑADIDO] LÓGICA DE IDENTIFICACIÓN DE SESIÓN (PUNTOS A y B) ---
        print("\n" + "-" * 70)
        print(" GESTIÓN DE SESIONES Y MEMORIA PERSISTENTE")
        print("-" * 70)
        opcion_sesion = input("Introduce un ID de sesión anterior (o presiona ENTER para crear uno nuevo) > ").strip()
        
        if not opcion_sesion:
            conversation_id = str(uuid.uuid4())[:8]
            print(f"[NUEVA SESIÓN] Tu identificador de hilo es: {conversation_id}")
        else:
            conversation_id = opcion_sesion
            print(f"[RECUPERANDO SESIÓN] Cargando historial de: {conversation_id}")

        # Inyectamos el ID al asistente para que cargue la memoria de SQLite
        try:
            asistente.iniciar_sesion(conversation_id)
        except AttributeError:
            print("[ADVERTENCIA] El asistente.py aún no tiene configurado el método 'iniciar_sesion'.")

        print("-" * 70)
        print(" FILTROS RAG (PREFIJOS DIRECTOS):")
        print("  /interfaz      -> Aísla la categoría de Diseño y Estética del producto.")
        print("  /funcion       -> Filtra el Rendimiento Técnico y fallas de hardware.")
        print("  /negativos     -> Enfoca el contexto únicamente en opiniones críticas.")
        print("-" * 70)
        print(" CATÁLOGO DE ACCIONES DISPONIBLES (FUNCTION CALLING INTERCEPTADO):")
        print("  1. 'Guarda el reporte en un archivo txt' (Ejecuta guardar_reporte_txt)")
        print("  2. 'Exporta las opiniones a CSV'        (Ejecuta exportar_analisis_csv)")
        print("  3. 'Muestra la lista de reportes'       (Ejecuta listar_archivos_reportes)")
        print("  4. 'Calcula el promedio de estrellas'   (Ejecuta calcular_promedio_estrellas)")
        print("  5. 'Cuenta los sentimientos totales'    (Ejecuta contar_sentimientos_totales)")
        print("  6. 'Muestra la resena más crítica'      (Ejecuta obtener_reseña_mas_critica)")
        print("  7. 'Dame el diagnóstico del sistema'    (Ejecuta obtener_diagnostico_sistema)")
        print("  8. 'Limpia el cache de scraping'        (Ejecuta limpiar_cache_scraping)")
        print("-" * 70)
        print(" COMANDOS DE CONTROL GLOBAL:")
        print("  /reiniciar     -> Purga la base vectorial in-place y pide otra URL.")
        print("  salir          -> Cierra la sesión y libera la memoria RAM del sistema.")
        print("="*70 + "\n")

        bandera_reinicio = False

        # BUCLE INTERACTIVO DEL CHAT
        while True:
            # [AÑADIDO] Muestra el ID de sesión en el prompt
            entrada = input(f"[{conversation_id}] Pregunta sobre las reseñas...> ").strip()
            
            if entrada.lower() in ["salir", "exit", "quit"]:
                print("[INFO] Finalizando sesión del asistente analítico local.")
                return 
                
            if not entrada:
                continue

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

            print("[PROCESAMIENTO] Analizando intención (RAG Híbrido vs Tool Selection)...")
            
            # Mantenemos tu lógica original de intercepción
            intentar_fc = any(palabra in entrada.lower() for palabra in ["guardar", "txt", "csv", "exportar", "promedio", "estrellas", "conteo", "sentimientos", "crítica", "peor", "diagnóstico", "sistema", "limpiar", "cache", "archivos", "listar", "lista", "reporte", "reportes"])
            
            try:
                if intentar_fc:
                    # El LLM evalúa los metadatos expuestos, intercepta la ejecución y procesa localmente
                    respuesta_funcion = asistente.llm.predict_and_call(
                        herramientas_fc, 
                        user_msg=entrada,
                        allow_parallel_tool_calls=False
                    )
                    print(f"\n[INTERCEPCIÓN DE FUNCIÓN EJECUTADA EN BACKEND]\n{respuesta_funcion}\n")
                else:
                    # Flujo regular del RAG Híbrido (Ahora con memoria stateful)
                    resultado = asistente.consultar(
                        pregunta=pregunta_final, 
                        filtro_categoria=cat_filtro, 
                        filtro_sentimiento=sent_filtro
                    )
                    print(f"\n[INFORME GENERADO POR RAG]\n{resultado}\n")
            except Exception as e:
                print(f"[ERROR] Estado de ejecución controlado: {e}\n")
                
            print("-" * 70)

        if bandera_reinicio:
            continue

if __name__ == "__main__":
    iniciar_flujo_completo()