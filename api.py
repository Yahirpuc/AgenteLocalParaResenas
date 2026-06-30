import os
import time
import uuid
import asyncio
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from llama_index.core.agent.workflow import AgentStream

# Importaciones de tu arquitectura modular
from modulos.agente.asistente import AsistenteAnaliticoHibrido
from main import inicializar_db_chat, cargar_historial, guardar_mensaje
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends
from modulos.seguridad.autenticacion import obtener_hash_password, verificar_password, crear_token_acceso, obtener_usuario_actual
from modulos.rutas.herramientas_api import router as herramientas_router
from modulos.rutas.producto_api import router as producto_router

from modulos.infraestructura.clientes_sqlite import (
    crear_usuario,
    eliminar_sesion_db,
    guardar_registro_auditoria,
    crear_tabla_auditoria,
    obtener_usuario_por_correo,
    obtener_sesiones_por_usuario,
    obtener_mensajes_por_sesion   
)

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, HTTPException, status, Depends, Request

# Importamos las variables y funciones de tu módulo de seguridad
from modulos.seguridad.autenticacion import (
    obtener_hash_password, 
    verificar_password, 
    crear_token_acceso,
    SECRET_KEY,      # Importamos la llave para poder desencriptar
    ALGORITHM        # Importamos el algoritmo
)
from modulos.seguridad.guardrails import validar_prompt_seguro




@asynccontextmanager
async def ciclo_vida_api(app: FastAPI):
    print("\n[STARTUP] Inicializando componentes globales del sistema...")
    try:
        await inicializar_db_chat()
        await asyncio.to_thread(crear_tabla_auditoria)
        print("[STARTUP] Tabla de auditoría verificada/creada.")

        ruta_db_local = os.path.join("datos", "base_vectorial")
        coleccion_local = "reviews_analizadas"
        
        asistente = AsistenteAnaliticoHibrido(ruta_db=ruta_db_local, nombre_coleccion=coleccion_local)
        
        # 2. GUARDAMOS EL ASISTENTE EN EL ESTADO NATIVO DE LA APP
        app.state.asistente = asistente
        print("[STARTUP] Componentes listos. Servidor listo para recibir peticiones.\n")
    except Exception as e:
        print(f"[STARTUP ERROR] Falló la inicialización: {e}")
        raise e
        
    yield
    print("\n[SHUTDOWN] Cerrando recursos del sistema.")
    # Limpiamos la memoria al apagar
    app.state.asistente = None

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

class UsuarioRegistro(BaseModel):
    correo: str
    contrasena: str

# DEPENDENCIA DEL ASISTENTE
def obtener_asistente(request: Request) -> AsistenteAnaliticoHibrido:
    """Extrae la instancia del asistente del estado global de forma segura."""
    asistente = getattr(request.app.state, "asistente", None)
    if not asistente:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="El motor de IA no está inicializado."
        )
    return asistente


## =====================================================================
# ENDPOINTS DE AUTENTICACIÓN (CORREGIDOS)
# =====================================================================
@app.post("/registro", status_code=status.HTTP_201_CREATED)
def registrar_usuario(datos: UsuarioRegistro):
    # 1. Encriptar la contraseña (usando tu función de autenticacion.py)
    password_hash = obtener_hash_password(datos.contrasena)
    
    # 2. Guardar en SQLite (usando tu función de clientes_sqlite.py)
    nuevo_id = crear_usuario(datos.correo, password_hash)
    
    if not nuevo_id:
        # Si devuelve None, es porque el UNIQUE del correo falló
        raise HTTPException(
            status_code=400, 
            detail="El correo ya está registrado"
        )
        
    return {"mensaje": "Usuario creado exitosamente", "id": nuevo_id}


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
    """Verifica credenciales y devuelve un JSON Web Token (JWT) enriquecido."""
    
    # Mapeamos las credenciales contra la base de datos local
    usuario_db = await asyncio.to_thread(obtener_usuario_por_correo, credenciales.username)
    
    if not usuario_db or not verificar_password(credenciales.password, usuario_db["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 🚨 CORRECCIÓN AQUÍ: Agregamos el correo al payload sin alterar el sub (UUID)
    token_jwt = crear_token_acceso(
        data={
            "sub": usuario_db["id"],                  # Sigue siendo el UUID para mantener tus relaciones en SQLite
            "username": usuario_db["correo"]          # 📧 ¡Esto es lo que leerá tu EnvolturaAdmin en React!
        }
    )
    
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

@app.delete("/api/sesiones/{sesion_id}")
async def borrar_conversacion(
    sesion_id: str, 
    usuario_id: str = Depends(obtener_usuario_actual)
):
    """
    Endpoint para que el usuario elimine un chat completo desde el frontend.
    """
    exito = await asyncio.to_thread(eliminar_sesion_db, sesion_id, usuario_id)
    
    if not exito:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La sesión no existe o no tienes permisos para eliminarla."
        )
        
    return {"estado": "ok", "mensaje": f"Sesión {sesion_id} y sus mensajes eliminados correctamente."}

# =====================================================================
# INCLUSIÓN DE RUTAS DE HERRAMIENTAS (Protegidas por autenticación)
# =====================================================================
app.include_router(herramientas_router)
app.include_router(producto_router)
# =====================================================================
# ENDPOINTS / RUTAS DE LA API
# =====================================================================

# ENDPOINT CENTRAL DE CHAT: ENRUTADO SEMÁNTICO GENÉRICO MLOPS
# =====================================================================
@app.post("/api/chat")
async def procesar_conversacion(
    peticion: PeticionMensaje,
    usuario_id: str = Depends(obtener_usuario_actual),
    asistente: AsistenteAnaliticoHibrido = Depends(obtener_asistente)
):
    session_id = peticion.id_sesion.strip() if peticion.id_sesion else str(uuid.uuid4())[:8]
    
    # -----------------------------------------------------------------
    # 🛡️ 1. CAPA DE VALIDACIÓN (GUARDRAILS)
    # -----------------------------------------------------------------
    es_seguro, mensaje_bloqueo = validar_prompt_seguro(peticion.mensaje)
    
    if not es_seguro:
        await guardar_mensaje(session_id, 'user', peticion.mensaje, usuario_id=usuario_id)
        await guardar_mensaje(session_id, 'assistant', mensaje_bloqueo, usuario_id=usuario_id)
        
        await asyncio.to_thread(
            guardar_registro_auditoria,
            session_id=session_id,
            user_prompt=peticion.mensaje,
            system_response=mensaje_bloqueo,
            ttft_ms=0.0,
            total_latency_ms=0.0,
            tokens_per_second=0.0,
            was_blocked=True,
            tools_executed=[]
        )
        
        async def generador_bloqueo():
            yield mensaje_bloqueo
            
        return StreamingResponse(generador_bloqueo(), media_type="text/plain", headers={"X-Session-ID": session_id})

    # -----------------------------------------------------------------
    # 🧠 2. FLUJO DIRECTO DEL AGENTE (Consultas RAG e Interacción Casual)
    # -----------------------------------------------------------------
    # Eliminamos el enrutador intermedio. Ahora el modelo de 7B decide de forma
    # nativa y fluida si usa el analizador o responde con memoria, ahorrando un 50% de CPU.
    historial_cargado = await cargar_historial(session_id)
    await guardar_mensaje(session_id, 'user', peticion.mensaje, usuario_id=usuario_id)

    agente = asistente.iniciar_sesion_agente(historial_cargado=historial_cargado)

    async def generador_tokens():
        tiempo_inicio = time.time()
        tiempo_primer_token = None
        conteo_tokens = 0
        is_streaming_answer = False
        buffer_texto = ""
        
        try:
            manejador = agente.run(peticion.mensaje)
            
            async for evento in manejador.stream_events():
                nombre_clase = type(evento).__name__
                
                if nombre_clase == "ToolCall":
                    nombre_herramienta = getattr(evento, "tool_name", "herramienta_local")
                    yield f"[[SYS_TOOL:{nombre_herramienta}]]"
                    
                elif isinstance(evento, AgentStream):
                    if not is_streaming_answer:
                        buffer_texto += evento.delta
                        
                        if "Answer:" in buffer_texto or "Respuesta:" in buffer_texto:
                            is_streaming_answer = True
                            
                            if tiempo_primer_token is None:
                                tiempo_primer_token = time.time()
                                yield "[[SYS_STREAM_START]]"
                            
                            separador = "Answer:" if "Answer:" in buffer_texto else "Respuesta:"
                            texto_limpio = buffer_texto.split(separador)[-1].lstrip()
                            
                            if texto_limpio:
                                conteo_tokens += 1
                                yield texto_limpio
                    else:
                        conteo_tokens += 1
                        yield evento.delta
                        
            resultado_final = await manejador
            texto_completo = str(resultado_final)
            await guardar_mensaje(session_id, 'assistant', texto_completo, usuario_id=usuario_id)

            tiempo_fin = time.time()
            if tiempo_primer_token:
                ttft_ms = (tiempo_primer_token - tiempo_inicio) * 1000
                total_latency_ms = (tiempo_fin - tiempo_inicio) * 1000
                tiempo_generacion_activa = tiempo_fin - tiempo_primer_token
                tps = conteo_tokens / tiempo_generacion_activa if tiempo_generacion_activa > 0 else 0
                
                await asyncio.to_thread(
                    guardar_registro_auditoria,
                    session_id=session_id,
                    user_prompt=peticion.mensaje,
                    system_response=texto_completo,
                    ttft_ms=round(ttft_ms, 2),
                    total_latency_ms=round(total_latency_ms, 2),
                    tokens_per_second=round(tps, 2),
                    was_blocked=False, 
                    tools_executed=[] 
                )

        except Exception as e:
            print(f"[API ERROR EN FLUJO] {e}")
            yield f"\n[Error del Agente: {str(e)}]"

    headers = {"X-Session-ID": session_id}
    return StreamingResponse(generador_tokens(), media_type="text/plain", headers=headers)

# =====================================================================
# ENDPOINT DE PURGA DE HISTORIAL
# =====================================================================
@app.delete("/api/usuarios/{usuario_id}/historial/purgar")
async def purgar_historial_por_perfil(usuario_id: str, token_uid: str = Depends(obtener_usuario_actual)):
    """
    Elimina físicamente todas las sesiones y mensajes del perfil de usuario especificado
    conectándose directamente a la base de datos de SQLite.
    """
    import sqlite3
    import os
    from fastapi import HTTPException
    
    # Declaramos la ruta exacta localmente dentro de la función
    ruta_db_relacional = os.path.join("datos", "base_relacional", "historial_sesiones.db")
    
    try:
        conn = sqlite3.connect(ruta_db_relacional)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        
        # 1. Consultamos si existen registros vinculados
        cursor.execute("SELECT COUNT(*) FROM sesiones WHERE usuario_id = ?;", (usuario_id,))
        total_sesiones = cursor.fetchone()[0]
        
        if total_sesiones == 0:
            conn.close()
            return {
                "status": "success", 
                "message": "El historial de conversaciones de este perfil ya se encuentra limpio."
            }
        
        # 2. Eliminamos las sesiones (El CASCADE configurado limpia la tabla 'mensajes' automáticamente)
        cursor.execute("DELETE FROM sesiones WHERE usuario_id = ?;", (usuario_id,))
        conn.commit()
        conn.close()
        
        return {
            "status": "success", 
            "message": f"Mantenimiento exitoso. Se eliminaron todas las conversaciones del perfil ({total_sesiones} chats purgados)."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error crítico en el motor relacional al purgar el historial: {str(e)}"
        )