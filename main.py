import os
import time
import sys
import gc
import uuid
import sqlite3  # Añadido para el gestor de usuarios y menús
from llama_index.core.tools import FunctionTool
from extractor_especifico import ExtractorEspecifico
from clasificador import ClasificadorReseñas
from asistente import AsistenteAnaliticoHibrido
from indexador import IndexadorRAG

import funciones_locales
# --- SOLUCIÓN AL ERROR ASYNC ---
import nest_asyncio
nest_asyncio.apply()

# ====================================================================
# 🛠️ GESTOR DE USUARIOS Y SESIONES (NUEVO)
# ====================================================================
def inicializar_bd_sesiones():
    """Crea una base de datos paralela solo para organizar a los usuarios y sus chats."""
    conn = sqlite3.connect("registro_usuarios.sqlite")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sesiones 
                 (usuario TEXT, session_id TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def registrar_nueva_sesion(usuario, session_id):
    """Guarda un nuevo chat en el registro del usuario."""
    conn = sqlite3.connect("registro_usuarios.sqlite")
    c = conn.cursor()
    c.execute("SELECT session_id FROM sesiones WHERE session_id=?", (session_id,))
    if not c.fetchone():
        c.execute("INSERT INTO sesiones (usuario, session_id) VALUES (?, ?)", (usuario, session_id))
    conn.commit()
    conn.close()

def listar_sesiones_usuario(usuario):
    """Obtiene todos los chats anteriores de un usuario específico."""
    conn = sqlite3.connect("registro_usuarios.sqlite")
    c = conn.cursor()
    c.execute("SELECT session_id, fecha FROM sesiones WHERE usuario=? ORDER BY fecha DESC", (usuario,))
    filas = c.fetchall()
    conn.close()
    return filas
# ====================================================================


def iniciar_flujo_completo():
    print("=" * 70)
    print("     SISTEMA ENRIQUECIDO DE ANALÍTICA LOCAL (ORQUESTADOR SMART)     ")
    print("=" * 70)
    
    inicializar_bd_sesiones() # Preparamos la base de datos de usuarios

    archivo_crudo = "reseñas_crudas.json"
    archivo_enriquecido = "reseñas_enriquecidas.json"
    ruta_db_local = "chroma_db"
    coleccion_local = "reviews_analizadas"
    
    ejecutar_extraccion = not os.path.exists(os.path.join(ruta_db_local, "chroma.sqlite3"))

    if ejecutar_extraccion:
        print("\n[INFO] No se detectó ninguna base de datos previa. Iniciando configuración inicial...")
    else:
        print("\n[INFO] Base de datos local detectada. Accediendo directamente al asistente...")

    herramientas_fc = [
        FunctionTool.from_defaults(fn=funciones_locales.guardar_reporte_txt, name="guardar_reporte_txt", description="Guarda el reporte en texto."),
        FunctionTool.from_defaults(fn=funciones_locales.exportar_analisis_csv, name="exportar_analisis_csv", description="Exporta a CSV."),
        FunctionTool.from_defaults(fn=funciones_locales.listar_archivos_reportes, name="listar_archivos_reportes", description="Lista reportes."),
        FunctionTool.from_defaults(fn=funciones_locales.calcular_promedio_estrellas),
        FunctionTool.from_defaults(fn=funciones_locales.contar_sentimientos_totales),
        FunctionTool.from_defaults(fn=funciones_locales.obtener_resena_mas_critica, name="obtener_resena_mas_critica"),
        FunctionTool.from_defaults(fn=funciones_locales.obtener_diagnostico_sistema),
        FunctionTool.from_defaults(fn=funciones_locales.limpiar_cache_scraping)
    ]
    
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
                print(f"[ERROR CRÍTICO EN PIPELINE]: {e}")
                ejecutar_extraccion = True
                continue

            print("\n[PASO 2] Sincronizando almacenamiento persistente en ChromaDB...")
            try:
                indexador_instancia = IndexadorRAG(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
                indexador_instancia.construir_indice(archivo_enriquecido=archivo_enriquecido)
                print("[INFO] Éxito: Reseñas inyectadas en ChromaDB.")
                ejecutar_extraccion = False 
            except Exception as e:
                print(f"[ERROR CRÍTICO EN INDEXADOR]: {e}")
                return

            gc.collect()   
            time.sleep(2)  

        print("\n[INFO] Inicializando modelos locales y motores (Vectores + BM25)...")
        try:
            asistente = AsistenteAnaliticoHibrido(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
        except Exception as e:
            if "default_tenant" in str(e):
                print("\n💡 [BLOQUEO DETECTADO] Reinicia el script para entrar directo al chat.\n")
                return 
            else:
                ejecutar_extraccion = True
                continue

        # ====================================================================
        # 🔐 PANTALLA DE INICIO DE SESIÓN Y MENÚ DE CHATS
        # ====================================================================
        print("\n" + "=" * 70)
        print(" 🔐 PANTALLA DE INICIO DE SESIÓN")
        print("=" * 70)
        usuario_actual = input("👤 Ingresa tu nombre de usuario > ").strip().lower()
        if not usuario_actual:
            usuario_actual = "anonimo"

        sesiones_previas = listar_sesiones_usuario(usuario_actual)
        conversation_id = None

        if sesiones_previas:
            print(f"\n[INFO] ¡Hola de nuevo, {usuario_actual}! Tienes {len(sesiones_previas)} chats guardados.")
            print("-" * 60)
            for i, (sid, fecha) in enumerate(sesiones_previas):
                print(f"  [{i+1}] Chat: {sid} (Última vez: {fecha[:16]})")
            print(f"  [ N ] Crear un nuevo chat limpio")
            print("-" * 60)
            
            opcion = input("Elige el número del chat que deseas cargar o 'N' para uno nuevo > ").strip().lower()
            
            if opcion == 'n':
                id_corto = str(uuid.uuid4())[:6]
                conversation_id = f"chat_{id_corto}"
                registrar_nueva_sesion(usuario_actual, conversation_id)
                print(f"\n[NUEVA SESIÓN] Se ha creado el chat: {conversation_id}")
            else:
                try:
                    indice = int(opcion) - 1
                    if indice >= 0 and indice < len(sesiones_previas):
                        conversation_id = sesiones_previas[indice][0]
                        print(f"\n[RECUPERANDO SESIÓN] Cargando base de datos del chat...")
                    else:
                        raise ValueError
                except (ValueError, IndexError):
                    print("[ERROR] Opción inválida. Creando un chat nuevo por seguridad...")
                    id_corto = str(uuid.uuid4())[:6]
                    conversation_id = f"chat_{id_corto}"
                    registrar_nueva_sesion(usuario_actual, conversation_id)
        else:
            print(f"\n[INFO] Bienvenido, {usuario_actual}. No tienes chats previos.")
            id_corto = str(uuid.uuid4())[:6]
            conversation_id = f"chat_{id_corto}"
            registrar_nueva_sesion(usuario_actual, conversation_id)
            print(f"[NUEVA SESIÓN] Se ha creado tu primer chat: {conversation_id}")

        # Inyectamos el ID al asistente para que cargue la memoria de SQLite
        try:
            asistente.iniciar_sesion(conversation_id)
        except AttributeError:
            print("[ADVERTENCIA] El asistente.py aún no tiene configurado el método 'iniciar_sesion'.")

        # ====================================================================
        # 📜 CARGA AUTOMÁTICA DEL HISTORIAL
        # ====================================================================
        historial = asistente.memory.get()
        if historial:
            print("\n" + "=" * 70)
            print(f" 📜 HISTORIAL RECUPERADO DEL CHAT: {conversation_id}")
            print("=" * 70)
            for msg in historial:
                if msg.role.value == "user":
                    print(f"👤 TÚ: {msg.content}")
                else:
                    print(f"🤖 AGENTE: {msg.content}\n")
            print("=" * 70 + "\n")
        else:
            print("\n[INFO] Este chat está nuevo y en blanco. ¡Empieza a preguntar!")

        print(" COMANDOS DE CONTROL GLOBAL:")
        print("  /reiniciar     -> Purga la base vectorial in-place y pide otra URL.")
        print("  salir          -> Cierra la sesión y libera la memoria RAM del sistema.")
        print("-" * 70 + "\n")

        bandera_reinicio = False

        # BUCLE INTERACTIVO DEL CHAT
        while True:
            entrada = input(f"[{usuario_actual} | {conversation_id}] > ").strip()
            
            if entrada.lower() in ["salir", "exit", "quit"]:
                print("[INFO] Finalizando sesión del asistente analítico local.")
                return 
                
            if not entrada:
                continue

            if entrada.startswith("/reiniciar"):
                print("\n[REINICIO] Vaciando índices y preparando entorno para nuevo producto...")
                try:
                    asistente.cerrar_conexion()
                except Exception as e:
                    pass
                if os.path.exists(archivo_crudo): os.remove(archivo_crudo)
                if os.path.exists(archivo_enriquecido): os.remove(archivo_enriquecido)
                print("[INFO] Base de datos limpia con éxito.")
                ejecutar_extraccion = True
                bandera_reinicio = True
                break 

            cat_filtro = None
            sent_filtro = None
            pregunta_final = entrada

            if entrada.startswith("/interfaz"):
                cat_filtro = "Diseño e Interfaz"
                pregunta_final = "Genera reporte sobre estética."
                print(f"[FILTRO APLICADO] Categoría: {cat_filtro}")
            elif entrada.startswith("/funcion"):
                cat_filtro = "Rendimiento y Caídas" 
                pregunta_final = "Genera reporte técnico."
                print(f"[FILTRO APLICADO] Categoría: {cat_filtro}")
            elif entrada.startswith("/negativos"):
                sent_filtro = "Negativo"
                pregunta_final = "Identifica quejas."
                print(f"[FILTRO APLICADO] Sentimiento: {sent_filtro}")

            intentar_fc = any(palabra in entrada.lower() for palabra in ["guardar", "txt", "csv", "exportar", "promedio", "estrellas", "conteo", "sentimientos", "crítica", "peor", "diagnóstico", "sistema", "limpiar", "cache", "archivos", "listar", "lista", "reporte", "reportes"])
            
            try:
                if intentar_fc:
                    respuesta_funcion = asistente.llm.predict_and_call(herramientas_fc, user_msg=entrada, allow_parallel_tool_calls=False)
                    print(f"\n[INTERCEPCIÓN DE FUNCIÓN]\n{respuesta_funcion}\n")
                else:
                    resultado = asistente.consultar(pregunta=pregunta_final, filtro_categoria=cat_filtro, filtro_sentimiento=sent_filtro)
                    print(f"\n🤖 AGENTE: \n{resultado}\n")
            except Exception as e:
                print(f"[ERROR]: {e}\n")
                
            print("-" * 70)

        if bandera_reinicio:
            continue

if __name__ == "__main__":
    iniciar_flujo_completo()