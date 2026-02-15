import os
import glob
import json
import pandas as pd
import time
from ollama import Client
import re
from tqdm import tqdm  # Barra de progreso

# --- CONFIGURACIÓN ---
OLLAMA_HOST = "http://172.27.16.1:11434"
MODELO_SEO = "qwen2.5vl:3b"
CARPETA_IMAGENES = "./imagenes_a_procesar"
ARCHIVO_JSON = "productos_kanela.json"
ARCHIVO_EXCEL = "catalogo_kanela.xlsx"
ARCHIVO_HTML = "ver_productos.html"

# --- EL SÚPER PROMPT REFINADO (V4 - ANTI-ALUCINACIONES) ---
SYSTEM_PROMPT = """
ROL: Eres el Gerente de Catálogo de "Kanela by Anier" (Córdoba, Argentina).
IDIOMA ESTRICTO: ESPAÑOL Rioplatense/Neutro. PROHIBIDO INGLÉS (Ej: No usar "Charm", usar "Dije". No usar "Gold", usar "Dorado").

TU MISIÓN: Analizar la imagen, determinar la coherencia visual y generar JSON.

REGLAS DE LÓGICA VISUAL (LEER ANTES DE RESPONDER):
1. **Dije vs Colgante:** Si es una pieza pequeña con una argollita simple o mosquetón para colgar en pulsera, es "Bijouterie/Dijes". Si tiene cadena incluida o es grande para el cuello, es "Colgante".
2. **Material:** - Si brilla mucho pero parece fantasía/costume jewelry -> "aleacion".
   - Si se ve robusto, pulido espejo y grisáceo -> "acero plateado".
   - Si se ve dorado intenso -> "acero dorado" (solo si parece alta calidad) o "aleacion" (si es fantasía).
   - REGLA DE ORO: Si clasificas como "aleacion", NUNCA pongas "Acero" en el título.
3. **Colores:** Sé simple. "Rosa", "Dorado", "Plateado". No inventes colores raros.

LISTAS CERRADAS (Elige EXACTAMENTE una opción):

A. CATEGORÍA:
   - Bijouterie/Dijes
   - Bijouterie/Aros/Argollas
   - Bijouterie/Aros/Colgantes
   - Bijouterie/Aros/Ear Cuffs
   - Bijouterie/Pulseras
   - Bijouterie/Tobilleras
   - Bijouterie/Cadenas
   - Bijouterie/Collares Diseño
   - Bijouterie/Gargantillas
   - Bijouterie/Conjuntos
   - Bijouterie/Piercings
   - Carteras/Totes
   - Carteras/Bandoleras
   - Carteras/Sobres
   - Accesorios/Llaveros

B. ESTILO:
   - Clasico (Atemporal, perlas, brillo sutil)
   - Punk (Cadenas gruesas, tachas, seguridad)
   - Gotico (Oscuro, cruces, calaveras, rosas, antiguo)

C. MATERIAL:
   - aleacion
   - acero dorado
   - acero plateado
   - lona
   - ecocuero

D. COLOR:
   - rosa, rojo, blanco, beige, verde, marron, bordo, negro, azul, amarillo, dorado, plateado, multicolor.

E. GÉNERO:
   - mujer, hombre, unisex.

--- FORMATO DE SALIDA (JSON) ---
{
  "nombre_archivo": "nombre-kebab-case.jpg",
  "titulo": "[Producto] [Diseño/Figura] de [Material] [Color] [Estilo]", 
  "categoria_producto": "(Copiar exacto de lista A)",
  "estilo_producto": "(Copiar exacto de lista B)",
  "material_producto": "(Copiar exacto de lista C)",
  "color_producto": "(Copiar exacto de lista D)",
  "genero_producto": "(Copiar exacto de lista E)",
  "short_description": "<ul><li>Ítem venta 1</li><li>Ítem venta 2</li><li>Ítem venta 3</li></ul>",
  "long_description": "<p>Párrafo emotivo describiendo uso y sensación.</p><h3>Especificaciones</h3><ul><li>Medida aprox: ...</li><li>Terminación: ...</li></ul>",
  "tags": "lista, de, 10, tags, seo, incluyendo, cordoba"
}
"""

client = Client(host=OLLAMA_HOST)


def limpiar_json(texto):
    """Limpia bloques de código markdown"""
    texto = re.sub(r"```json\s*", "", texto)
    texto = re.sub(r"```\s*$", "", texto)
    return texto.strip()


def generar_reporte_html(datos):
    """Genera reporte HTML Responsive y detallado"""
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Catálogo Kanela AI</title>
        <style>
            :root { --primary: #2c3e50; --accent: #e74c3c; --bg: #f8f9fa; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); margin: 0; padding: 20px; }
            h1 { color: var(--primary); text-align: center; margin-bottom: 30px; }
            
            .grid-container {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 20px;
            }
            
            .card {
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                overflow: hidden;
                display: flex;
                flex-direction: row;
                border: 1px solid #eee;
                transition: transform 0.2s;
            }
            .card:hover { transform: translateY(-2px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }
            
            .img-container {
                width: 160px;
                background: #fff;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                border-right: 1px solid #eee;
                padding: 10px;
            }
            
            .img-container img {
                width: 150px;
                height: 150px;
                object-fit: contain; /* Mantiene proporción sin estirar */
                border-radius: 8px;
            }
            
            .timer { font-size: 0.8rem; color: #666; margin-top: 10px; background: #eee; padding: 2px 8px; border-radius: 10px; }
            
            .info { padding: 15px; flex: 1; min-width: 0; }
            
            h2 { font-size: 1.1rem; margin: 0 0 10px 0; color: var(--primary); line-height: 1.3; }
            
            .specs { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }
            .badge { 
                font-size: 0.75rem; padding: 3px 8px; border-radius: 4px; font-weight: 600; 
                border: 1px solid #eee; white-space: nowrap;
            }
            .badge-cat { background: #e8f4fd; color: #0d47a1; }
            .badge-style { background: #fce4ec; color: #880e4f; }
            .badge-mat { background: #e0f2f1; color: #004d40; }
            
            .desc-box { font-size: 0.85rem; color: #444; margin-top: 10px; border-top: 1px solid #eee; padding-top: 10px; }
            .desc-box ul { padding-left: 20px; margin: 5px 0; }
            .desc-box h3 { font-size: 0.9rem; margin: 10px 0 5px; color: #555; }
            
            .tags { font-size: 0.75rem; color: #888; font-style: italic; margin-top: 10px; display: block; }
            
            /* Responsive Móvil */
            @media (max-width: 600px) {
                .card { flex-direction: column; }
                .img-container { width: 100%; border-right: none; border-bottom: 1px solid #eee; flex-direction: row; justify-content: space-between; }
                .img-container img { width: 100px; height: 100px; }
            }
        </style>
    </head>
    <body>
        <h1>💎 Catálogo Visual Kanela (QA V4.0)</h1>
        <div class="grid-container">
    """

    for p in datos:
        ruta_img = f"./imagenes_a_procesar/{p.get('origen', '')}"

        html += f"""
        <div class="card">
            <div class="img-container">
                <img src="{ruta_img}" alt="Producto" onerror="this.src='https://placehold.co/150x150?text=No+Image'">
                <span class="timer">⏱️ {p.get("tiempo_segundos", 0)}s</span>
            </div>
            <div class="info">
                <h2>{p.get("titulo", "Sin Título")}</h2>
                
                <div class="specs">
                    <span class="badge badge-cat">📂 {p.get("categoria_producto")}</span>
                    <span class="badge badge-style">✨ {p.get("estilo_producto")}</span>
                    <span class="badge badge-mat">🛠️ {p.get("material_producto")}</span>
                    <span class="badge">🎨 {p.get("color_producto")}</span>
                    <span class="badge">👤 {p.get("genero_producto")}</span>
                </div>

                <div class="desc-box">
                    <strong>Descripción Corta:</strong>
                    {p.get("short_description", "")}
                    
                    <details>
                        <summary style="cursor:pointer; color:blue; font-size:0.8rem; margin-top:5px;">Ver Descripción Larga</summary>
                        <div style="margin-top:5px; padding:5px; background:#f9f9f9; border-radius:4px;">
                            {p.get("long_description", "")}
                        </div>
                    </details>
                </div>
                
                <span class="tags">🏷️ {p.get("tags")}</span>
            </div>
        </div>
        """

    html += "</div></body></html>"
    with open(ARCHIVO_HTML, "w", encoding="utf-8") as f:
        f.write(html)


def guardar_resultados(datos):
    """Guarda en todos los formatos"""
    # JSON
    with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

    # Excel
    df = pd.DataFrame(datos)

    # Orden de columnas solicitado
    cols_orden = [
        "origen",
        "titulo",
        "categoria_producto",
        "estilo_producto",
        "material_producto",
        "color_producto",
        "genero_producto",
        "tiempo_segundos",
        "tags",
        "short_description",
        "long_description",
    ]

    # Asegurar columnas
    for c in cols_orden:
        if c not in df.columns:
            df[c] = ""

    cols_final = cols_orden + [c for c in df.columns if c not in cols_orden]
    df = df[cols_final]

    df.to_excel(ARCHIVO_EXCEL, index=False)

    # HTML
    generar_reporte_html(datos)


def analizar_carpeta():
    if not os.path.exists(CARPETA_IMAGENES):
        os.makedirs(CARPETA_IMAGENES)
        print(f"📂 Carpeta creada: '{CARPETA_IMAGENES}'.")
        return

    tipos = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
    archivos = []
    for tipo in tipos:
        archivos.extend(glob.glob(os.path.join(CARPETA_IMAGENES, tipo)))

    if not archivos:
        print(f"⚠️ No hay imágenes en '{CARPETA_IMAGENES}'.")
        return

    print(f"🚀 Scanner Kanela V4.0 (Modo Estricto) con {MODELO_SEO}...")

    resultados = []
    # Cargar previos si existen
    if os.path.exists(ARCHIVO_JSON):
        try:
            with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
                resultados = json.load(f)
        except Exception:
            resultados = []

    start_time = time.time()

    # Barra de progreso
    pbar = tqdm(archivos, unit="img")

    for imagen_path in pbar:
        nombre_file = os.path.basename(imagen_path)
        pbar.set_description(f"Analizando: {nombre_file[:15]}...")

        # Saltar si ya existe
        if any(d.get("origen") == nombre_file for d in resultados):
            continue

        img_start = time.time()

        try:
            response = client.chat(
                model=MODELO_SEO,
                messages=[
                    {"role": "user", "content": SYSTEM_PROMPT, "images": [imagen_path]}
                ],
                options={
                    "temperature": 0.1,  # Súper estricto para que respete Español y Listas
                    "num_ctx": 4096,  # Memoria visual amplia (importante para fotos HD)
                    "top_p": 0.9,  # Ayuda a mantener coherencia
                },
                # ------------------------
            )

            duracion = round(time.time() - img_start, 2)
            content = limpiar_json(response["message"]["content"])

            try:
                data = json.loads(content)
                data["origen"] = nombre_file
                data["tiempo_segundos"] = duracion

                resultados.append(data)
                guardar_resultados(resultados)  # Guardado incremental

            except json.JSONDecodeError:
                # Log de error pero no crash
                resultados.append(
                    {
                        "origen": nombre_file,
                        "titulo": "ERROR FORMATO JSON",
                        "short_description": f"Raw output: {content}",
                        "tiempo_segundos": duracion,
                    }
                )
                guardar_resultados(resultados)

        except Exception as e:
            pbar.write(f"❌ Error crítico con {nombre_file}: {e}")

    total_time = round(time.time() - start_time, 2)
    print(f"\n🏁 Finalizado: {len(resultados)} productos en {total_time}s.")
    print(f"📄 Excel: {ARCHIVO_EXCEL}")
    print(f"🎨 Visual: {ARCHIVO_HTML}")


if __name__ == "__main__":
    analizar_carpeta()
