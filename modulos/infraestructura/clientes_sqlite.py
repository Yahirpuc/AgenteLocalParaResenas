import sqlite3
import os
import uuid
from llama_index.core.llms import ChatMessage, MessageRole


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

def crear_sesion_si_no_existe(sesion_id: str, usuario_id: str = "usuario_default"):
    """
    Verifica si la sesión existe. Si no, la crea.
    Por ahora usamos un 'usuario_default' hasta conectar el Login.
    """
    conn = sqlite3.connect(RUTA_DB_RELACIONAL)
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    
    # 1. Asegurarnos de que el usuario por defecto exista (Para que no falle la llave foránea)
    c.execute('''INSERT OR IGNORE INTO usuarios (id, correo, password_hash) 
                 VALUES (?, ?, ?)''', (usuario_id, "admin@test.com", "hash_falso"))
    
    # 2. Crear la sesión si no existe
    c.execute('''INSERT OR IGNORE INTO sesiones (id, usuario_id, titulo) 
                 VALUES (?, ?, ?)''', (sesion_id, usuario_id, "Nueva Conversación"))
    
    conn.commit()
    conn.close()

def guardar_mensaje(sesion_id: str, rol: str, contenido: str, usuario_id: str = "usuario_default"):
    """Inserta un nuevo mensaje y lo ata al usuario real."""
    # Le pasamos el usuario_id real a la creación de la sesión
    crear_sesion_si_no_existe(sesion_id, usuario_id)
    
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

# Puedes ejecutar esto directamente para crear las tablas
if __name__ == "__main__":
    inicializar_base_datos()