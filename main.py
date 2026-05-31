import os
from extractor import ExtractorUniversal
from asistente import AsistenteAnaliticoHibrido
from indexador import IndexadorRAG

def iniciar_flujo_completo():
    print("=" * 70)
    print("     SISTEMA ENRIQUECIDO DE ANALÍTICA LOCAL (ORQUESTADOR SMART)     ")
    print("=" * 70)
    
    archivo_crudo = "reseñas_enriquecidas.json"
    ruta_db_local = "chroma_db"
    coleccion_local = "reviews_analizadas"
    
    # Condición inicial estricta: Si la BD no existe, se activa la extracción obligatoria
    ejecutar_extraccion = not os.path.exists(ruta_db_local)

    if ejecutar_extraccion:
        print("\n[INFO] No se detectó ninguna base de datos previa. Iniciando configuración inicial...")
    else:
        print("\n[INFO] Base de datos local detectada. Accediendo directamente al asistente...")

    # BUCLE PRINCIPAL DE CONTROL (Mantiene el orquestador vivo para iterar múltiples URLs)
    while True:
        if ejecutar_extraccion:
            url_objetivo = input("\nIntroduce la URL del producto para analizar (Cualquier sitio web) > ").strip()
            
            if not url_objetivo:
                print("[ERROR] No introdujiste una URL válida. Cancelando proceso.")
                return

            print("\n[PASO 1] Lanzando navegador universal inteligente...")
            # Limpieza preventiva del JSON para evitar colisiones de registros viejos
            if os.path.exists(archivo_crudo):
                os.remove(archivo_crudo)

            extractor = ExtractorUniversal(archivo_salida=archivo_crudo)
            extractor.extraer(url_objetivo, scrolls=3)

            if not os.path.exists(archivo_crudo) or os.path.getsize(archivo_crudo) == 0:
                print("[ERROR] El proceso de extracción no generó datos. Intente de nuevo.")
                ejecutar_extraccion = True
                continue

            print("\n[PASO 2] Sincronizando almacenamiento persistente en ChromaDB...")
            try:
                indexador_instancia = IndexadorRAG(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
                indexador_instancia.construir_indice(archivo_enriquecido=archivo_crudo)
                print("[INFO] Éxito: Reseñas procesadas e inyectadas en ChromaDB.")
                ejecutar_extraccion = False # Transición exitosa hacia el entorno de chat
            except Exception as e:
                print(f"[ERROR CRÍTICO EN EL INDEXADOR]: {e}")
                return

        # [PASO 3] Inicialización de modelos locales y motores indexados (Vectores + BM25)
        print("\n[INFO] Inicializando modelos locales y motores (Vectores + BM25)...")
        try:
            asistente = AsistenteAnaliticoHibrido(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
        except Exception as e:
            print(f"[ERROR CRÍTICO AL INICIAR ASISTENTE]: {e}")
            print("Forzando reconfiguración integral...")
            ejecutar_extraccion = True
            continue

        print("\n" + "="*70)
        print("ENTORNO HÍBRIDO ACTIVO - ENTIENDE CONTEXTOS Y PALABRAS CLAVE")
        print("="*70)
        print("Filtros: /interfaz, /funcion, /negativos")
        print("Comando especial: /reiniciar (Para vaciar datos y meter otra URL)")
        print("Para cerrar la sesión por completo, escribe 'salir'.")
        print("="*70 + "\n")

        bandera_reinicio = False

        # BUCLE INTERACTIVO DEL CHAT
        while True:
            entrada = input("Pregunta sobre las reseñas...> ").strip()
            
            if entrada.lower() in ["salir", "exit", "quit"]:
                print("[INFO] Finalizando sesión del asistente analítico local.")
                return # Cierre absoluto de la aplicación
                
            if not entrada:
                continue

            # SOLUCOÓN RADICAL CONTROLADA PARA WINDOWS: Vaciado in-place sin eliminar directorios
            if entrada.startswith("/reiniciar"):
                print("\n" + "-" * 70)
                print("[REINICIO] Vaciando índices y preparando entorno para nuevo producto...")
                print("-" * 70)
                
                # 1. Forzamos a ChromaDB a purgar la colección internamente
                try:
                    asistente.cerrar_conexion()
                except Exception as e:
                    print(f"[ADVERTENCIA] Error en la rutina de limpieza: {e}")
                
                # 2. Eliminación física del JSON viejo para arrancar limpios
                if os.path.exists(archivo_crudo):
                    os.remove(archivo_crudo)
                
                print("[INFO] Base de datos e historial limpios con éxito.")
                ejecutar_extraccion = True
                bandera_reinicio = True
                break # Rompe este bucle interno y nos regresa a la solicitud de URL

            cat_filtro = None
            sent_filtro = None
            pregunta_final = entrada

            # Enrutamiento lógico de comandos por metadatos estructurados
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

            print("[PROCESAMIENTO] Consultando índices híbridos y generando respuesta...")
            
            try:
                resultado = asistente.consultar(
                    pregunta=pregunta_final, 
                    filtro_categoria=cat_filtro, 
                    filtro_sentimiento=sent_filtro
                )
                print(f"\n[INFORME GENERADO]\n{resultado}\n")
            except Exception as e:
                print(f"[ERROR] Ocurrió una excepción durante la ejecución: {e}\n")
                
            print("-" * 70)

        # Si el chat se rompió por orden de reinicio, el ciclo principal continúa y pide la nueva URL
        if bandera_reinicio:
            continue

if __name__ == "__main__":
    iniciar_flujo_completo()