import sqlite3
import os

# Ruta a tu base de datos
ruta_db = os.path.join("datos", "base_relacional", "historial_sesiones.db")

def revisar_telemetria():
    try:
        conn = sqlite3.connect(ruta_db)
        c = conn.cursor()
        
        # Traemos el último registro guardado
        c.execute('''
            SELECT user_prompt, ttft_ms, total_latency_ms, tokens_per_second 
            FROM auditoria 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        registro = c.fetchone()
        
        if registro:
            print("\n=== 📊 ÚLTIMA MÉTRICA DE RENDIMIENTO LOCAL ===")
            print(f"🗣️ Prompt: '{registro[0]}'")
            print(f"⏱️ Time To First Token (TTFT): {registro[1]} ms")
            print(f"⏳ Latencia Total: {registro[2]} ms")
            print(f"🚀 Velocidad: {registro[3]} Tokens por segundo")
            print("================================================\n")
        else:
            print("Aún no hay registros en la tabla de auditoría.")
            
        conn.close()
    except Exception as e:
        print(f"Error al leer la base de datos: {e}")

if __name__ == "__main__":
    revisar_telemetria()