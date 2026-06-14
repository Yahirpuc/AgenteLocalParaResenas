import os
import uuid
import asyncio
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse

# Importaciones de tu arquitectura modular
from modulos.agente.asistente import AsistenteAnaliticoHibrido
from main import inicializar_db_chat, cargar_historial, guardar_mensaje
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends
from modulos.seguridad.autenticacion import obtener_hash_password, verificar_password, crear_token_acceso

from modulos.infraestructura.clientes_sqlite import (
    crear_usuario, 
    obtener_usuario_por_correo,
    obtener_sesiones_por_usuario,
    obtener_mensajes_por_sesion   
)

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt

# Importamos las variables y funciones de tu módulo de seguridad
from modulos.seguridad.autenticacion import (
    obtener_hash_password, 
    verificar_password, 
    crear_token_acceso,
    SECRET_KEY,      # Importamos la llave para poder desencriptar
    ALGORITHM        # Importamos el algoritmo
)

# Contenedor global para el cerebro del asistente
aplicacion_estado = {}

@asynccontextmanager
async def ciclo_vida_api(app: FastAPI):
    """
    Manejador de ciclo de vida (Lifespan). 
    Carga los modelos en memoria y conecta las bases de datos una sola vez al iniciar,
    evitando retrasos de I/O en cada petición HTTP.
    """
    print("\n[STARTUP] Inicializando componentes globales del sistema...")
    try:
        # 1. Asegurar persistencia relacional
        await inicializar_db_chat()
        
        # 2. Instanciar el cerebro híbrido (Carga Ollama y ChromaDB)
        ruta_db_local = os.path.join("datos", "base_vectorial")
        coleccion_local = "reviews_analizadas"
        
        asistente = AsistenteAnaliticoHibrido(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
        
        # Guardamos la instancia en el estado global de la aplicación
        aplicacion_estado["asistente"] = asistente
        print("[STARTUP] Componentes listos. Servidor listo para recibir peticiones.\n")
    except Exception as e:
        print(f"[STARTUP ERROR] Falló la inicialización: {e}")
        raise e
        
    yield
    # Limpieza al apagar el servidor (si fuera necesaria)
    print("\n[SHUTDOWN] Cerrando recursos del sistema.")
    aplicacion_estado.clear()

# Inicialización de FastAPI con su configuración de ciclo de vida
app = FastAPI(
    title="API de Analítica de Reseñas RAG",
    version="1.0.0",
    description="Microservicio asíncrono para la gestión de agentes de IA y análisis de opiniones.",
    lifespan=ciclo_vida_api
)

# Configuración de CORS para permitir la futura conexión con el Frontend (React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # En producción se cambia por el dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# MODELOS DE DATOS (PYDANTIC)
# =====================================================================
class PeticionMensaje(BaseModel):
    id_sesion: str | None = None
    mensaje: str

class RespuestaAgente(BaseModel):
    id_sesion: str
    respuesta: str

class UsuarioRegistro(BaseModel):
    correo: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


# Le decimos a FastAPI dónde está la ruta para obtener el token (para la documentación de Swagger)
esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def obtener_usuario_actual(token: str = Depends(esquema_oauth2)):
    """
    Función Guardia: Intercepta el Token, lo desencripta y verifica si es válido.
    Retorna el ID del usuario (sub) para usarlo en el endpoint.
    """
    excepcion_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales o el token ha expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Intentamos abrir el candado del JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id: str = payload.get("sub")
        
        if usuario_id is None:
            raise excepcion_credenciales
            
        return usuario_id
        
    except JWTError:
        # Si el token es inventado, fue alterado o ya caducó, lanzamos el error
        raise excepcion_credenciales

# =====================================================================
# ENDPOINTS DE AUTENTICACIÓN
# =====================================================================
@app.post("/api/auth/registro", status_code=status.HTTP_201_CREATED)
async def registrar_usuario(usuario: UsuarioRegistro):
    """Registra un nuevo usuario encriptando su contraseña."""
    hash_pw = obtener_hash_password(usuario.password)
    nuevo_id = await asyncio.to_thread(crear_usuario, usuario.correo, hash_pw)
    
    if not nuevo_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado."
        )
    return {"mensaje": "Usuario creado exitosamente", "id": nuevo_id}

@app.post("/api/auth/login", response_model=Token)
async def iniciar_sesion(credenciales: OAuth2PasswordRequestForm = Depends()):
    """Verifica credenciales y devuelve un JSON Web Token (JWT)."""
    
    # IMPORTANTE: OAuth2PasswordRequestForm siempre usa el campo 'username', 
    # así que mapeamos tu 'correo' a ese campo.
    usuario_db = await asyncio.to_thread(obtener_usuario_por_correo, credenciales.username)
    
    if not usuario_db or not verificar_password(credenciales.password, usuario_db["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_jwt = crear_token_acceso(data={"sub": usuario_db["id"]})
    return {"access_token": token_jwt, "token_type": "bearer"}

# =====================================================================
# ENDPOINTS DE HISTORIAL (Para la interfaz del usuario)
# =====================================================================

@app.get("/api/sesiones")
async def listar_sesiones(usuario_id: str = Depends(obtener_usuario_actual)):
    """
    Endpoint para el Sidebar.
    Devuelve la lista de chats previos del usuario autenticado.
    """
    sesiones = await asyncio.to_thread(obtener_sesiones_por_usuario, usuario_id)
    return {"sesiones": sesiones}

@app.get("/api/sesiones/{sesion_id}/mensajes")
async def obtener_historial_chat(
    sesion_id: str, 
    usuario_id: str = Depends(obtener_usuario_actual)
):
    """
    Endpoint para la ventana principal.
    Devuelve toda la conversación de un chat en específico.
    """
    mensajes = await asyncio.to_thread(obtener_mensajes_por_sesion, sesion_id, usuario_id)
    
    if mensajes is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La sesión no existe o no tienes permisos para verla."
        )
        
    return {"sesion_id": sesion_id, "mensajes": mensajes}

# =====================================================================
# ENDPOINTS / RUTAS DE LA API
# =====================================================================

@app.post("/api/chat")
async def procesar_conversacion(
    peticion: PeticionMensaje,
    usuario_id: str = Depends(obtener_usuario_actual) 
):
    """
    Endpoint de conversación compatible con LlamaIndex v0.14+ (Workflows).
    Implementa Server-Sent Events (SSE) fragmentando la respuesta final 
    para la "UI Estúpida" del frontend.
    """
    asistente: AsistenteAnaliticoHibrido = aplicacion_estado.get("asistente")
    if not asistente:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="El motor de IA no está inicializado."
        )

    session_id = peticion.id_sesion.strip() if peticion.id_sesion else str(uuid.uuid4())[:8]
    historial_cargado = await cargar_historial(session_id)
    await guardar_mensaje(session_id, 'user', peticion.mensaje, usuario_id=usuario_id)

    agente = asistente.iniciar_sesion_agente(historial_cargado=historial_cargado)

    async def generador_tokens():
        try:
            # 1. Ejecutamos el flujo con la sintaxis correcta de Workflows v0.14
            resultado_flujo = await agente.run(peticion.mensaje)
            respuesta_texto = str(resultado_flujo)
            
            # 2. Fragmentamos la respuesta (Chunking por palabra)
            palabras = respuesta_texto.split(" ")
            for i, palabra in enumerate(palabras):
                # Reconstruimos el texto manteniendo los espacios
                chunk = palabra if i == 0 else " " + palabra
                
                # Emitimos el chunk hacia el cliente React
                yield chunk
                
                # Pequeño delay de 20ms para crear la animación de tecleo fluido en pantalla
                await asyncio.sleep(0.02) 

            # 3. Guardamos la respuesta final en SQLite
            await guardar_mensaje(session_id, 'assistant', respuesta_texto, usuario_id=usuario_id)

        except Exception as e:
            print(f"[API ERROR EN FLUJO] {e}")
            yield f"\n[Error del Agente: {str(e)}]"

    # Enviamos el ID en los cabezales HTTP
    headers = {"X-Session-ID": session_id}
    
    return StreamingResponse(
        generador_tokens(), 
        media_type="text/plain", 
        headers=headers
    )

