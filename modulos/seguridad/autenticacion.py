from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

# =====================================================================
# CONFIGURACIÓN DE SEGURIDAD
# =====================================================================
# En un entorno de producción B2B, esta clave debe vivir en un archivo .env
SECRET_KEY = "clave_super_secreta_para_desarrollo_local" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # El token expira en 2 horas

# Configuración del algoritmo de encriptación (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =====================================================================
# FUNCIONES DE HASHEO DE CONTRASEÑAS
# =====================================================================
def obtener_hash_password(password: str) -> str:
    """Toma una contraseña en texto plano y devuelve un hash irreversible."""
    return pwd_context.hash(password)

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    """Compara una contraseña en texto plano con el hash guardado en la BD."""
    return pwd_context.verify(plain_password, hashed_password)

# =====================================================================
# GENERACIÓN DE TOKENS JWT
# =====================================================================
def crear_token_acceso(data: dict) -> str:
    """
    Recibe un diccionario (generalmente con el 'sub': UUID_del_usuario) 
    y devuelve un token JWT firmado y con tiempo de expiración.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt