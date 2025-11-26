# 📦 Chatbot de Productos con Voz — Etapa 2

Este proyecto implementa un **chatbot de productos con entrada por voz**, capaz de escuchar al usuario, transcribir el audio mediante **Whisper (OpenAI Speech-to-Text)** y responder amablemente utilizando **ChatGPT**, con información proveniente exclusivamente de una base de datos SQLite.

El objetivo es cumplir con la **Etapa 2 del Trabajo Práctico** del curso *Principales Tecnologías de la Inteligencia Artificial*.

---

## 🎤 Consulta por voz

El usuario puede hablar directamente al sistema mediante un componente de grabación de audio integrado en Streamlit.  
El audio grabado se envía a la API **Whisper /v1/audio/transcriptions**, que devuelve el texto interpretado.  
A partir de esa transcripción, el chatbot busca productos en la base de datos y responde únicamente sobre ellos.

---

## 📂 Estructura del proyecto

```
Chat_BOT_Productos_voz/
│
├── aplicación.py         # Aplicación Streamlit (voz → texto + chatbot)
├── productos.db          # Base SQLite con la tabla tbl_product
├── requisitos.txt        # Dependencias del proyecto
└── README.md             # Documento descriptivo
```

---

## 🧠 ¿Cómo funciona el chatbot?

1. El usuario **graba un audio** desde la aplicación.
2. Whisper convierte la voz en texto.
3. El sistema **extrae la palabra clave** relevante de la consulta.
4. Se buscan coincidencias en la base **SQLite (`productos.db`)**.
5. Los productos hallados se envían como **contexto** al modelo ChatGPT.
6. El chatbot responde siempre:
   - en español,
   - con tono amable,
   - y *solo* utilizando información de la tabla `tbl_product`.

---

## 🗃️ Base de datos (SQLite)

### **tbl_product**  
Incluye los campos definidos en el enunciado:

| Campo             | Descripción                           |
|------------------|---------------------------------------|
| prod_id          | ID único del producto                 |
| prod_name        | Nombre del producto                   |
| prod_desc        | Descripción detallada                |
| prod_price       | Precio                                |
| prod_currency    | Moneda                                |
| prod_family      | Familia                               |
| prod_subfamily   | Subfamilia                            |
| prod_photo       | URL de la imagen                      |
| status           | Activo / Inactivo                     |

El chatbot solo responde sobre productos con **status = 1**.

---

## 🛠️ Tecnologías utilizadas

| Tecnología           | Uso |
|---------------------|------------------------------------------------|
| **Python**          | Lógica del chatbot |
| **Streamlit**       | Interfaz web (audio + texto) |
| **Whisper (OpenAI)**| Speech-to-Text |
| **ChatGPT (OpenAI)**| Generación de respuesta |
| **SQLite**          | Base de datos |
| **Requests**        | Conexión a las APIs |
| **GitHub**          | Control de versiones |

---

## ▶️ Ejecución local

1. Instalar dependencias:
   ```
   pip install -r requisitos.txt
   ```

2. Configurar tu API Key:
   - Windows:
     ```
     setx OPENAI_API_KEY "sk-..."
     ```
   - Mac / Linux:
     ```bash
     export OPENAI_API_KEY="sk-..."
     ```

3. Ejecutar la aplicación:
   ```
   streamlit run aplicación.py
   ```

4. Abrir en navegador:
   ```
   http://localhost:8501
   ```

---

## ✔️ Estado del proyecto

Proyecto completado:  
- Consulta por voz funcional  
- Transcripción con Whisper  
- Respuesta con ChatGPT  
- Base de datos integrada  
- Interfaz Streamlit lista para evaluación  

