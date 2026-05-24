import json
import os
import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import Document
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding

class IndexadorRAG:
    def __init__(self, ruta_db="chroma_db", nombre_coleccion="reviews_analizadas"):
        self.ruta_db = ruta_db
        self.nombre_coleccion = nombre_coleccion
        
        # Configuramos el modelo de embeddings local de Ollama
        self.embed_model = OllamaEmbedding(model_name="nomic-embed-text")

    def construir_indice(self, archivo_enriquecido="reseñas_enriquecidas.json"):
        """Lee el JSON enriquecido por la IA y lo monta en ChromaDB limpiando registros viejos."""
        if not os.path.exists(archivo_enriquecido):
            print(f"[ERROR] No se encuentra el archivo '{archivo_enriquecido}'.")
            return

        with open(archivo_enriquecido, "r", encoding="utf-8") as f:
            datos = json.load(f)

        print(f"[INFO] Convirtiendo {len(datos)} opiniones enriquecidas a nodos de LlamaIndex...")
        documentos_llamaindex = []

        for item in datos:
            estrellas_valor = item["estrellas"] if item["estrellas"] else 0
            
            # FORMATO BLINDADO: Delimitadores claros para que el LLM local no cruce datos
            texto_estructurado = f"""
            === RESEÑA DE CLIENTE ===
            AUTOR: {item['autor']}
            TITULO: {item['titulo_comentario']}
            TEXTO DE LA OPINIÓN: {item['texto']}
            =========================
            """.strip()

            doc = Document(
                text=texto_estructurado, # <-- Pasamos el texto formateado de forma estricta
                id_=item["id"],
                metadata={
                    "autor": item["autor"],
                    "estrellas": str(estrellas_valor),
                    "fuente": item["fuente"],
                    "sentimiento": item["metadatos"]["sentimiento"],
                    "categoria": item["metadatos"]["categoria"],
                    "fecha": item["metadatos"]["fecha_publicacion"]
                }
            )
            documentos_llamaindex.append(doc)

        print("[INFO] Inicializando ChromaDB localmente...")
        db_cliente = chromadb.PersistentClient(path=self.ruta_db)
        
        # Eliminación preventiva de la colección anterior para evitar duplicados u opiniones desactualizadas
        try:
            db_cliente.delete_collection(name=self.nombre_coleccion)
            print("[INFO] Colección persistente anterior eliminada para una actualización limpia de metadatos.")
        except Exception:
            # Si la colección no existía previamente, continúa el flujo sin interrumpir
            pass
        
        chroma_collection = db_cliente.get_or_create_collection(name=self.nombre_coleccion)
        
        # Acoplamos ChromaDB como el almacén de vectores oficial de LlamaIndex
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        print("[INFO] Generando embeddings e indexando en la Base de Datos Vectorial...")
        # Construimos el índice pasando nuestros documentos, embeddings y el contexto de almacenamiento
        index = VectorStoreIndex.from_documents(
            documentos_llamaindex,
            storage_context=storage_context,
            embed_model=self.embed_model
        )
        
        print(f"[OK] Base de datos vectorial creada con éxito en la carpeta '{self.ruta_db}'.")
        return index

if __name__ == "__main__":
    indexador = IndexadorRAG()
    indexador.construir_indice()