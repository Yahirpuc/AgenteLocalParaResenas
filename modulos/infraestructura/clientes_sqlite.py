import sqlite3
import os
import uuid
from llama_index.core.llms import ChatMessage, MessageRole
import json
import time
from datetime import datetime


# Ruta global de la base de datos
RUTA_DB_RELACIONAL = os.path.join("datos", "base_relacional", "historial_sesiones.db")

def inicializar_base_datos():
    """
    Inicializa el esquema relacional para soporte SaaS multiusuario.
    Crea las tablas: usuarios, sesiones y mensajes.
    """
    # Aseguramos que la carpeta exista
    os.makedirs(os.path.dirname(RUTA_DB_RELACIONAL), exist_ok=True)
    
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    
    # IMPORTANTE: SQLite requiere activar el chequeo de llaves foráneas explícitamente
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()

    # ==========================================
    # 1. TABLA: Usuarios
    # ==========================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id TEXT PRIMARY KEY,              -- UUID del usuario
            correo TEXT UNIQUE NOT NULL,      -- Correo para login
            password_hash TEXT NOT NULL,      -- Contraseña encriptada (NUNCA texto plano)
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==========================================
    # 2. TABLA: Sesiones (Los "Chats" en la UI)
    # ==========================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS sesiones (
            id TEXT PRIMARY KEY,              -- UUID de la sesión (ej. a41e63f1)
            usuario_id TEXT NOT NULL,         -- Llave foránea hacia el dueño
            titulo TEXT NOT NULL,             -- Título autogenerado para el Sidebar
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
        )
    ''')

    # ==========================================
    # 3. TABLA: Mensajes (El historial del Agente)
    # ==========================================
    c.execute('''
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id TEXT NOT NULL,          -- Llave foránea hacia la sesión
            rol TEXT NOT NULL,                -- 'user' o 'assistant'
            contenido TEXT NOT NULL,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sesion_id) REFERENCES sesiones (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Esquema relacional SaaS (Usuarios, Sesiones, Mensajes) inicializado correctamente.")

# =====================================================================
# OPERACIONES CRUD PARA EL HISTORIAL DE CHAT
# =====================================================================

def crear_sesion_si_no_existe(sesion_id: str, usuario_id: str = "usuario_default", primer_mensaje: str = None):
    """
    Verifica si la sesión existe. Si no, la crea con un título dinámico estilo ChatGPT.
    """
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    
    # Asegurarnos de que el usuario por defecto exista
    c.execute('''INSERT OR IGNORE INTO usuarios (id, correo, password_hash) 
                 VALUES (?, ?, ?)''', (usuario_id, "admin@test.com", "hash_falso"))
    
    # 📝 Si viene el primer mensaje, generamos el título dinámico
    if primer_mensaje:
        palabras = primer_mensaje.split()
        # Tomamos las primeras 5 palabras y agregamos puntos suspensivos si es largo
        titulo_chat = " ".join(palabras[:5]) + ("..." if len(palabras) > 5 else "")
    else:
        titulo_chat = "Nueva Conversación"
    
    # Insertamos la sesión usando el título dinámico generado
    c.execute('''INSERT OR IGNORE INTO sesiones (id, usuario_id, titulo) 
                 VALUES (?, ?, ?)''', (sesion_id, usuario_id, titulo_chat))
    
    conn.commit()
    conn.close()

def guardar_mensaje(sesion_id: str, rol: str, contenido: str, usuario_id: str = "usuario_default"):
    """Inserta un nuevo mensaje e inicializa la sesión con el título dinámico."""
    # 🚀 Pasamos el contenido si el rol es 'user' (la primera pregunta)
    crear_sesion_si_no_existe(sesion_id, usuario_id, primer_mensaje=contenido if rol == 'user' else None)
    
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    
    c.execute('''INSERT INTO mensajes (sesion_id, rol, contenido) 
                 VALUES (?, ?, ?)''', (sesion_id, rol, contenido))
    
    conn.commit()
    conn.close()
def cargar_historial(sesion_id: str):
    """Recupera el historial y lo formatea para LlamaIndex."""
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    c = conn.cursor()
    
    # Buscamos solo los mensajes de esta sesión específica
    c.execute('SELECT rol, contenido FROM mensajes WHERE sesion_id = ? ORDER BY id ASC', (sesion_id,))
    filas = c.fetchall()
    conn.close()
    
    historial = []
    for rol, contenido in filas:
        if rol == 'user':
            historial.append(ChatMessage(role=MessageRole.USER, content=contenido))
        elif rol == 'assistant':
            historial.append(ChatMessage(role=MessageRole.ASSISTANT, content=contenido))
            
    return historial

# =====================================================================
# OPERACIONES CRUD DE USUARIOS (AUTENTICACIÓN)
# =====================================================================
def crear_usuario(correo: str, password_hash: str) -> str:
    """Inserta un nuevo usuario en la BD y retorna su ID."""
    nuevo_id = str(uuid.uuid4())
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO usuarios (id, correo, password_hash) VALUES (?, ?, ?)', 
                  (nuevo_id, correo, password_hash))
        conn.commit()
        return nuevo_id
    except sqlite3.IntegrityError:
        # Esto ocurre si el correo ya existe (por la restricción UNIQUE)
        return None
    finally:
        conn.close()

def obtener_usuario_por_correo(correo: str):
    """Busca un usuario por su correo. Retorna un diccionario si existe."""
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    c = conn.cursor()
    c.execute('SELECT id, correo, password_hash FROM usuarios WHERE correo = ?', (correo,))
    fila = c.fetchone()
    conn.close()
    
    if fila:
        return {"id": fila[0], "correo": fila[1], "password_hash": fila[2]}
    return None

# =====================================================================
# CONSULTAS DE LECTURA PARA EL FRONTEND (API GET)
# =====================================================================

def obtener_sesiones_por_usuario(usuario_id: str) -> list:
    """Devuelve todas las sesiones de un usuario, ordenadas de la más reciente a la más antigua."""
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    c = conn.cursor()
    
    c.execute('''
        SELECT id, titulo, creado_en 
        FROM sesiones 
        WHERE usuario_id = ? 
        ORDER BY creado_en DESC
    ''', (usuario_id,))
    
    filas = c.fetchall()
    conn.close()
    
    # Formateamos a una lista de diccionarios para que FastAPI lo convierta a JSON fácil
    return [{"id": fila[0], "titulo": fila[1], "creado_en": fila[2]} for fila in filas]

def obtener_mensajes_por_sesion(sesion_id: str, usuario_id: str) -> list:
    """
    Devuelve los mensajes de una sesión. 
    Verifica que la sesión pertenezca al usuario actual por seguridad.
    """
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    c = conn.cursor()
    
    # 1. Capa de seguridad: Validar que el usuario sea el dueño de la sesión
    c.execute('SELECT id FROM sesiones WHERE id = ? AND usuario_id = ?', (sesion_id, usuario_id))
    if not c.fetchone():
        conn.close()
        return None # Retorna None si intenta espiar otra sesión o no existe
        
    # 2. Extraer los mensajes ordenados cronológicamente
    c.execute('''
        SELECT rol, contenido, creado_en 
        FROM mensajes 
        WHERE sesion_id = ? 
        ORDER BY id ASC
    ''', (sesion_id,))
    
    filas = c.fetchall()
    conn.close()
    
    return [{"rol": fila[0], "contenido": fila[1], "creado_en": fila[2]} for fila in filas]

def eliminar_sesion_db(sesion_id: str, usuario_id: str) -> bool:
    """
    Elimina una sesión específica verificando que pertenezca al usuario actual.
    Por la regla ON DELETE CASCADE, esto purga también todos los mensajes asociados.
    """
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    c = conn.cursor()
    
    # Intentamos borrar donde coincidan el ID de la sesión y el dueño
    c.execute('DELETE FROM sesiones WHERE id = ? AND usuario_id = ?', (sesion_id, usuario_id))
    
    # rowcount nos dice cuántas filas fueron afectadas. Si es > 0, se borró con éxito.
    filas_borradas = c.rowcount
    
    conn.commit()
    conn.close()
    
    return filas_borradas > 0

# Añade esta función para que se ejecute cuando inicializas tu base de datos
def crear_tabla_auditoria():
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS auditoria (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            user_prompt TEXT,
            system_response TEXT,
            ttft_ms REAL,
            total_latency_ms REAL,
            tokens_per_second REAL,
            was_blocked BOOLEAN,
            tools_executed TEXT
        )
    ''')
    conn.commit()
    conn.close()

def guardar_registro_auditoria(
    session_id: str, user_prompt: str, system_response: str, 
    ttft_ms: float, total_latency_ms: float, tokens_per_second: float, 
    was_blocked: bool = False, tools_executed: list = []
):
    """Guarda las métricas de rendimiento en la tabla de auditoría."""
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    c = conn.cursor()
    
    registro_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tools_json = json.dumps(tools_executed) # Convertimos la lista de herramientas a JSON
    
    c.execute('''
        INSERT INTO auditoria 
        (id, session_id, timestamp, user_prompt, system_response, ttft_ms, total_latency_ms, tokens_per_second, was_blocked, tools_executed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (registro_id, session_id, timestamp, user_prompt, system_response, ttft_ms, total_latency_ms, tokens_per_second, was_blocked, tools_json))
    
    conn.commit()
    conn.close()

# Puedes ejecutar esto directamente para crear las tablas
if __name__ == "__main__":
    inicializar_base_datos()
    crear_tabla_auditoria()