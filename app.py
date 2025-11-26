import os
import json
import sqlite3
from pathlib import Path

import requests
import streamlit as st


# =========================
# 1) CONFIGURACIÓN BÁSICA
# =========================

# Ruta de la base de datos SQLite (mismo repo)
RUTA_DB = Path(__file__).resolve().parent / "productos.db"

# Clave de API de OpenAI
#   - En Streamlit Cloud: Settings -> Secrets -> {"OPENAI_API_KEY": "sk-..."}
#   - En local: export OPENAI_API_KEY=sk-...
OPENAI_API_KEY = (
    st.secrets.get("OPENAI_API_KEY")
    if hasattr(st, "secrets")
    else os.getenv("OPENAI_API_KEY")
)

if not OPENAI_API_KEY:
    st.error(
        "No se encontró la variable de entorno o secret 'OPENAI_API_KEY'. "
        "Configúrala antes de continuar."
    )
    st.stop()


# =========================
# 2) BASE DE DATOS (SQLite)
# =========================

def get_connection():
    """[No verificado] Retorna conexión SQLite a productos.db."""
    conn = sqlite3.connect(RUTA_DB)
    conn.row_factory = sqlite3.Row
    return conn


def buscar_productos_por_texto(texto_busqueda: str, limite: int = 5):
    """
    [No verificado] Busca productos activos cuyo nombre, descripción,
    familia o subfamilia contengan el texto de búsqueda.
    """
    patron = f"%{texto_busqueda.lower()}%"

    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT prod_id, prod_name, prod_desc, prod_currency,
               prod_price, prod_family, prod_subfamily,
               prod_min_stock, status, prod_photo
        FROM tbl_product
        WHERE status = 1
          AND (
                LOWER(prod_name)      LIKE ?
             OR LOWER(prod_desc)      LIKE ?
             OR LOWER(prod_family)    LIKE ?
             OR LOWER(prod_subfamily) LIKE ?
          )
        ORDER BY prod_name
        LIMIT ?;
    """

    cur.execute(query, (patron, patron, patron, patron, limite))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [dict(r) for r in rows]


# =========================
# 3) LIMPIAR TEXTO DE BÚSQUEDA
# =========================

def extraer_texto_busqueda(pregunta: str) -> str:
    """
    [No verificado] Extrae una palabra clave de la pregunta del usuario
    para usarla en la búsqueda SQL.
    """
    pregunta = pregunta.strip().lower()

    # Si habla genéricamente de "productos", no filtramos por nada
    if "producto" in pregunta or "productos" in pregunta:
        return ""

    palabras = [p.strip(".,;:¡!¿?") for p in pregunta.split()]

    stopwords = {
        # verbos y auxiliares
        "tengo", "tienes", "tienen", "tenemos",
        "quiero", "quisiera", "busco", "buscando",
        "estoy", "estamos", "necesito", "necesitamos",
        "compara", "comparar", "comparacion", "comparación",
        "tiene",
        # conectores / artículos / pronombres
        "en", "la", "el", "los", "las",
        "un", "una", "unos", "unas",
        "de", "del", "al", "para", "por", "con", "sobre",
        "que", "su", "sus", "o", "y",
        # palabras muy genéricas en tus preguntas
        "galeria", "galería", "busquedad", "busqueda"
    }

    # filtramos todo lo que sea stopword
    palabras_clave = [p for p in palabras if p and p not in stopwords]

    # si después de filtrar no queda nada, devolvemos la frase completa
    if not palabras_clave:
        return pregunta

    # unir número + unidad (128 gb -> 128gb)
    unidades = {"gb", "tb", "mb", "hz", "mhz", "ghz"}
    if len(palabras_clave) >= 2:
        penultima = palabras_clave[-2]
        ultima = palabras_clave[-1]
        if penultima.isdigit() and ultima in unidades:
            return penultima + ultima

    # nos quedamos con la última palabra clave (ya sin verbos / galería / etc.)
    palabra = palabras_clave[-1]

    # lematización muy simple de plurales
    if len(palabra) > 4 and palabra.endswith("es"):
        palabra = palabra[:-2]
    elif len(palabra) > 3 and palabra.endswith("s"):
        palabra = palabra[:-1]

    return palabra


# =========================
# 4) LLAMADA A CHATGPT
# =========================

def llamar_llm(pregunta_usuario: str, productos_encontrados: list) -> str:
    """
    [No verificado] Llama a /v1/chat/completions usando la lista de productos
    como contexto. Solo debe responder sobre esos productos.
    """
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    if productos_encontrados:
        resumen_productos = []
        for p in productos_encontrados:
            resumen_productos.append(
                f"- ID: {p['prod_id']}, Nombre: {p['prod_name']}, "
                f"Descripción: {p['prod_desc']}, "
                f"Precio: {p['prod_currency']} {p['prod_price']}, "
                f"Familia: {p['prod_family']}, Subfamilia: {p['prod_subfamily']}, "
                f"Foto: {p['prod_photo']}"
            )
        texto_productos = "\n".join(resumen_productos)
    else:
        texto_productos = "No se encontraron productos que coincidan con la búsqueda."

    system_message = (
        "Eres un asistente de una tienda virtual de productos.\n"
        "Respondes SIEMPRE en español, de forma amable, clara y cordial.\n"
        "Solo puedes responder usando la información de la lista de productos "
        "que recibes. Si el usuario pregunta algo que no está relacionado con "
        "los productos o la lista está vacía, debes indicar que solo puedes "
        "responder sobre los productos disponibles en la tabla."
    )

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_message},
            {
                "role": "assistant",
                "content": (
                    "Esta es la lista de productos disponibles en la base de datos:\n"
                    f"{texto_productos}"
                ),
            },
            {"role": "user", "content": pregunta_usuario},
        ],
    }

    resp = requests.post(url, headers=headers, data=json.dumps(data))

    if resp.status_code != 200:
        return (
            f"Hubo un problema al llamar al modelo (código {resp.status_code}). "
            "Revisa la API key, el modelo o la configuración de la cuenta."
        )

    respuesta_json = resp.json()
    return respuesta_json["choices"][0]["message"]["content"]


# =========================
# 5) SPEECH-TO-TEXT (WHISPER)
# =========================

def transcribir_audio(audio_file) -> str:
    """
    [No verificado] Envía el audio a la API de Whisper (OpenAI)
    y devuelve el texto transcrito en español.
    """
    url = "https://api.openai.com/v1/audio/transcriptions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    audio_bytes = audio_file.getvalue()
    filename = audio_file.name or "audio.wav"
    mime_type = audio_file.type or "audio/wav"

    files = {
        "file": (filename, audio_bytes, mime_type),
    }

    data = {
        "model": "whisper-1",
        "language": "es",          # Se espera audio en español
        "response_format": "json",
    }

    resp = requests.post(url, headers=headers, data=data, files=files)

    if resp.status_code != 200:
        st.error(
            f"Error al transcribir el audio (código {resp.status_code}): "
            f"{resp.text}"
        )
        return ""

    result = resp.json()
    return result.get("text", "").strip()


# =========================
# 6) LÓGICA DE CONSULTA
# =========================

def procesar_consulta(pregunta: str):
    """
    [No verificado] Ejecuta todo el flujo:
    1) Extraer texto de búsqueda
    2) Consultar productos
    3) Llamar al LLM
    4) Mostrar respuesta y productos usados
    """
    if not pregunta.strip():
        st.warning("La transcripción resultó vacía. Intenta nuevamente.")
        return

    st.markdown(f"**Texto interpretado:** {pregunta}")

    texto_busqueda = extraer_texto_busqueda(pregunta)
    productos = buscar_productos_por_texto(texto_busqueda)

    if not productos:
        st.warning(
            "No se encontraron productos que coincidan con la búsqueda. "
            "Solo puedo responder sobre los productos registrados en la tabla."
        )
        respuesta = (
            "No encontré productos que coincidan con lo que me comentas. "
            "Prueba preguntando por otra característica o nombre de producto."
        )
    else:
        respuesta = llamar_llm(pregunta, productos)

    st.session_state["ultima_respuesta"] = respuesta

    st.subheader("Respuesta del chatbot")
    st.write(respuesta)

    if productos:
        st.subheader("Productos utilizados como contexto")
        for p in productos:
            with st.container():
                st.markdown(f"**{p['prod_name']}** (ID: `{p['prod_id']}`)")
                st.write(p["prod_desc"])
                st.write(
                    f"Precio: {p['prod_currency']} {p['prod_price']}  |  "
                    f"Familia: {p['prod_family']} / {p['prod_subfamily']}"
                )
                if p["prod_photo"]:
                    # si prod_photo es URL, se intenta mostrar
                    st.image(p["prod_photo"], width=200)


# =========================
# 7) INTERFAZ STREAMLIT
# =========================

st.set_page_config(page_title="Chatbot de Productos con Voz", page_icon="🛍️")

if "ultima_respuesta" not in st.session_state:
    st.session_state["ultima_respuesta"] = ""

st.title("🛍️ Chatbot de Productos con Voz")
st.write(
    "[No verificado] Habla al chatbot sobre los productos y sus características. "
    "La aplicación transcribe tu audio con la API de Speech-to-Text de ChatGPT "
    "y responde usando solo la información de la tabla de productos."
)

st.markdown("---")

# MODO AUDIO (requisito de la Etapa 2)
st.header("🎤 Consulta por voz")

audio_file = st.audio_input(
    "Haz clic en el ícono de micrófono, habla claramente y luego detén la grabación."
)

if audio_file is not None:
    st.audio(audio_file)

    if st.button("Enviar audio al chatbot"):
        texto_transcrito = transcribir_audio(audio_file)
        if texto_transcrito:
            procesar_consulta(texto_transcrito)

st.markdown("---")

# MODO TEXTO (opcional, útil para pruebas)
with st.expander("💬 Consulta opcional por texto (para pruebas)"):
    pregunta_texto = st.text_input(
        "Escribe aquí tu pregunta (opcional):",
        placeholder="Ejemplo: ¿Tienes monitores de 27 pulgadas?",
    )
    if st.button("Consultar por texto"):
        procesar_consulta(pregunta_texto)
