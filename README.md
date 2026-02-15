# 💎 Kanela AI Catalog Scanner

Herramienta de automatización para e-commerce que utiliza Inteligencia Artificial Local (Ollama) para analizar imágenes de joyería y generar catálogos SEO optimizados para WooCommerce.

Diseñado específicamente para la marca **Kanela by Anier** (Córdoba, Arg), respetando su identidad de marca (Estilos: Gótico, Punk, Clásico).

## 🚀 Características

- **Análisis Visual Local:** Usa el modelo `qwen2.5vl:3b` corriendo en local (Cero costo de API, privacidad total).
- **SEO & Copywriting:** Genera títulos, descripciones cortas/largas en HTML y Tags optimizados para búsquedas locales (Córdoba Capital).
- **Validación Estricta:** Clasifica productos usando listas cerradas (Enums) para Categorías, Materiales y Colores, evitando alucinaciones de la IA.
- **Reporte Visual (QA):** Genera un archivo `ver_productos.html` para comparar lado a lado la imagen con los datos generados.
- **Multi-Formato:** Exporta simultáneamente a Excel (`.xlsx`) listo para importar y JSON (`.json`) de respaldo.
- **Eficiencia:** Incluye barra de progreso, reanudación automática (no repite fotos ya procesadas) y métricas de tiempo.

## 🛠️ Requisitos Previos

- **Python 3.10+**
- **Ollama** corriendo en segundo plano (Windows/Linux/Mac).
- **Gestor de paquetes `uv`** (Recomendado) o `pip`.
- **Hardware:** Probado en NVIDIA RTX 2060 (6GB VRAM).

## 📦 Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <tu-repo-url>
   cd scanner_seo
   ```

2. **Instalar dependencias:**
   ```bash
   uv venv
   source .venv/bin/activate
   uv sync
   ```
## ⚙️ Configuración

3. **Configurar variables:**
   ```bash
   cp .env.example .env
   # Edita .env con tus datos
   OLLAMA_HOST = "http://172.27.16.1:11434" # IP de tu host Ollama (Si usas WSL -> Windows)
   MODELO_SEO = "qwen2.5vl:3b" # Modelo liviano para GPUs de 6GB
   ```
4. **Configurar el modelo LLM:**
   ```bash
   # ollama pull qwen2.5vl:3b
   ```
## ▶️ Uso

5. **Coloca las imágenes de tus productos (.jpg, .png, .webp) en la carpeta: ./imagenes_a_procesar:**

## ▶📊 Procesamiento

4. **Procesar imágenes:**
   ```bash
   uv run scanner.py
   ```

5. **Ver resultados:**
   ```bash
   # Ver resultados en ver_productos.html
   # Importar Excel en WooCommerce
   # Importar JSON en WooCommerce
   ```

6. **🤖 Estructura del prompt:**

El sistema actúa como un "Gerente de E-commerce" con reglas estrictas:

Estilos: Detecta Gótico, Punk o Clásico.

Prohibiciones: No usa palabras genéricas como "lindo" o "barato".

Formato: Salida estricta en JSON para evitar errores de parseo.


## 📂 Procesamiento Masivo (Lotes)

El sistema ahora soporta subcarpetas y optimización de lotes:

1.  **Carpetas Recursivas:** Puedes organizar tus imágenes en subdirectorios dentro de `imagenes_a_procesar`.
    *   Ejemplo:
        ```text
        imagenes_a_procesar/
        ├── anillos/
        │   └── anillo-calavera.jpg
        ├── dijes/
        │   └── dije-corazon.jpg
        └── lote_2024/
            └── foto1.jpg
        ```
    *   El reporte mostrará la ruta relativa (ej: `dijes/dije-corazon.jpg`).

2.  **Optimización (Skip Logic):**
    *   Si el script se interrumpe, **no te preocupes**.
    *   Al reiniciarlo, detectará qué imágenes ya están procesadas (en `productos_kanela.json`) y las saltará instantáneamente.
    *   Puedes agregar carpetas nuevas progresivamente.

### 💡 Recomendación de Hardware (RTX 2060 6GB)
*   **Tamaño de Lote Ideal:** 50 a 100 imágenes por ejecución.
*   **Tiempo Estimado:** ~15 minutos por lote.
*   **Recomendación:** Procesa un lote, revisa el HTML brevemente, y carga el siguiente.
