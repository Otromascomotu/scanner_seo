import os
import glob
import json
import pandas as pd
import time
from ollama import Client
import re
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.console import Console
from rich.theme import Theme

# --- CONFIGURACIÓN ---
OLLAMA_HOST = "http://172.27.16.1:11434"
MODELO_SEO = "qwen2.5vl:3b"
CARPETA_IMAGENES = "./imagenes_a_procesar"
ARCHIVO_JSON = "productos_kanela.json"
ARCHIVO_EXCEL = "catalogo_kanela.xlsx"
ARCHIVO_HTML = "ver_productos.html"

# --- PROMPT V5 (GOLD FILLED UPDATE) ---
SYSTEM_PROMPT = """
ROL: Gerente de Catálogo de "Kanela by Anier" (Córdoba, Argentina).
IDIOMA: ESPAÑOL NEUTRO. PROHIBIDO "CHARM". USAR "DIJE".

REGLAS VISUALES:
1. Dije vs Colgante: Pequeño c/argolla = "Bijouterie/Dijes". Grande/cadena = "Colgante".
2. Material: 
   - Brillo fantasía = "aleacion". 
   - Gris = "acero plateado". 
   - Dorado = "acero dorado (Gold Filled)" (o aleacion si se ve de baja calidad).
3. Si es "aleacion", NO usar "Acero" en título.

LISTAS CERRADAS:
A. CATEGORÍA: Bijouterie/Dijes, Bijouterie/Aros/Argollas, Bijouterie/Aros/Colgantes, Bijouterie/Aros/Ear Cuffs, Bijouterie/Pulseras, Bijouterie/Tobilleras, Bijouterie/Cadenas, Bijouterie/Collares Diseño, Bijouterie/Gargantillas, Bijouterie/Conjuntos, Bijouterie/Piercings, Carteras/Totes, Carteras/Bandoleras, Carteras/Sobres, Accesorios/Llaveros
B. ESTILO: Clasico, Punk, Gotico
C. MATERIAL: aleacion, acero dorado (Gold Filled), acero plateado, lona, ecocuero
D. COLOR: rosa, rojo, blanco, beige, verde, marron, bordo, negro, azul, amarillo, dorado, plateado, multicolor
E. GÉNERO: mujer, hombre, unisex

--- JSON ---
{
  "nombre_archivo": "...", "titulo": "...", 
  "categoria_producto": "...", "estilo_producto": "...", "material_producto": "...", 
  "color_producto": "...", "genero_producto": "...", 
  "short_description": "...", "long_description": "...", "tags": "..."
}
"""

custom_theme = Theme({"success": "green", "error": "bold red", "info": "cyan"})
console = Console(theme=custom_theme)
client = Client(host=OLLAMA_HOST)


def limpiar_json(texto):
    """Limpia bloques markdown del JSON"""
    texto = re.sub(r"```json\s*", "", texto)
    texto = re.sub(r"```\s*$", "", texto)
    return texto.strip()


def sanitarizar_texto(texto):
    """Fuerza bruta para eliminar palabras prohibidas y corregir formatos"""
    reemplazos = {
        "Charm": "Dije",
        "charm": "dije",
        "Charms": "Dijes",
        "charms": "dijes",
        "Gold": "Dorado",
        "gold": "dorado",
        "Goldfilled": "Gold Filled",  # Corregir si la IA lo escribe junto
        "Gold-filled": "Gold Filled",
    }
    for old, new in reemplazos.items():
        texto = texto.replace(old, new)
    return texto


def generar_reporte_html(datos):
    css = """
    :root {
        --bg: #f4f6f8; --card-bg: #fff; --text: #2d3748; --text-light: #718096;
        --border: #e2e8f0; --accent: #3182ce; --badge-bg: #edf2f7;
        --shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    [data-theme="dark"] {
        --bg: #1a202c; --card-bg: #2d3748; --text: #f7fafc; --text-light: #a0aec0;
        --border: #4a5568; --accent: #63b3ed; --badge-bg: #4a5568;
        --shadow: 0 4px 6px -1px rgba(0,0,0,0.5);
    }
    
    body { font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text); padding: 0; margin: 0; transition: 0.3s; }
    
    header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 20px 40px; background: var(--card-bg); border-bottom: 1px solid var(--border);
        box-shadow: var(--shadow); position: sticky; top: 0; z-index: 100;
    }
    h1 { margin: 0; font-size: 1.5rem; color: var(--accent); }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(500px, 1fr)); gap: 30px; padding: 30px; max-width: 1600px; margin: 0 auto; }
    
    .card { 
        background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border);
        box-shadow: var(--shadow); display: grid; grid-template-columns: 180px 1fr; overflow: hidden;
    }
    
    .img-col { 
        padding: 20px; background: var(--badge-bg); display: flex; flex-direction: column; 
        align-items: center; justify-content: center; border-right: 1px solid var(--border);
    }
    img { width: 140px; height: 140px; object-fit: contain; }
    
    .info-col { padding: 25px; display: flex; flex-direction: column; }
    h2 { margin: 0 0 15px; font-size: 1.2rem; line-height: 1.3; }
    
    .specs { 
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; 
    }
    .badge {
        font-size: 0.8rem; padding: 6px 10px; background: var(--bg); 
        border: 1px solid var(--border); border-radius: 6px; 
        display: flex; flex-direction: column;
    }
    .b-label { font-size: 0.7rem; color: var(--text-light); font-weight: 700; text-transform: uppercase; margin-bottom: 2px; }
    .b-val { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .desc { font-size: 0.9rem; color: var(--text-light); line-height: 1.5; }
    
    button.toggle {
        background: var(--bg); border: 1px solid var(--border); padding: 8px 16px; 
        border-radius: 20px; cursor: pointer; color: var(--text); font-weight: 600;
    }
    button.copy-btn {
        background: var(--accent); color: white; border: none; padding: 5px 10px; 
        border-radius: 4px; cursor: pointer; font-size: 0.8rem; margin-top: 5px;
    }
    button.copy-btn:active { transform: scale(0.95); }

    @media (max-width: 768px) {
        .grid { grid-template-columns: 1fr; padding: 15px; }
        .card { grid-template-columns: 1fr; }
        .img-col { border-right: none; border-bottom: 1px solid var(--border); flex-direction: row; justify-content: space-between; }
        .specs { grid-template-columns: repeat(2, 1fr); }
    }
    """

    js = """
    <script>
        const body = document.body;
        const currentTheme = localStorage.getItem('theme');
        if (currentTheme) body.setAttribute('data-theme', currentTheme);
        updateText(currentTheme || 'light');

        function toggleTheme() {
            const newTheme = body.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateText(newTheme);
        }
        function updateText(theme) {
            document.getElementById('toggle-btn').innerText = theme === 'dark' ? '☀️ Modo Luz' : '🌙 Modo Oscuro';
        }
        function copyToClipboard(textId) {
            const text = document.getElementById(textId).innerText;
            navigator.clipboard.writeText(text).then(() => {
                alert('¡HTML copiado al portapapeles!');
            });
        }
    </script>
    """

    html = f"""
    <!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Kanela V11</title><style>{css}</style></head>
    <body>
        <header>
            <h1>💎 Kanela AI V11</h1>
            <button id="toggle-btn" class="toggle" onclick="toggleTheme()">🌙 Modo Oscuro</button>
        </header>
        <div class="grid">
    """

    for i, p in enumerate(datos):
        ruta = f"./imagenes_a_procesar/{p.get('origen', '')}"
        desc_id = f"desc-{i}"

        html += f"""
        <div class="card">
            <div class="img-col">
                <img src="{ruta}" onerror="this.src='https://placehold.co/150'">
                <div style="margin-top:10px; font-size:0.8rem; font-weight:bold;">⏱️ {p.get("tiempo_segundos", 0)}s</div>
            </div>
            <div class="info-col">
                <h2>{p.get("titulo", "Error")}</h2>
                
                <div class="specs">
                    <div class="badge"><span class="b-label">Categoría</span><span class="b-val" title="{p.get("categoria_producto")}">{p.get("categoria_producto")}</span></div>
                    <div class="badge"><span class="b-label">Estilo</span><span class="b-val">{p.get("estilo_producto")}</span></div>
                    <div class="badge"><span class="b-label">Material</span><span class="b-val" title="{p.get("material_producto")}">{p.get("material_producto")}</span></div>
                    <div class="badge"><span class="b-label">Color</span><span class="b-val">{p.get("color_producto")}</span></div>
                    <div class="badge"><span class="b-label">Género</span><span class="b-val">{p.get("genero_producto")}</span></div>
                </div>

                <div class="desc">
                    {p.get("short_description", "")[:100]}...
                    <details>
                        <summary>Ver y Copiar HTML</summary>
                        <div style="background:var(--bg); padding:10px; border-radius:6px; margin-top:10px; border:1px solid var(--border);">
                            <strong style="font-size:0.8rem;">Descripción Larga (HTML):</strong>
                            <div id="{desc_id}" style="font-family:monospace; font-size:0.75rem; white-space:pre-wrap; margin:5px 0;">{p.get("long_description")}</div>
                            <button class="copy-btn" onclick="copyToClipboard('{desc_id}')">📋 Copiar HTML</button>
                        </div>
                    </details>
                </div>
            </div>
        </div>"""

    html += f"</div>{js}</body></html>"
    with open(ARCHIVO_HTML, "w", encoding="utf-8") as f:
        f.write(html)


def guardar_resultados(datos):
    with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

    df = pd.DataFrame(datos)
    cols = [
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

    # --- CORRECCIÓN 1: Bucle for expandido ---
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    # -----------------------------------------

    df = df[cols + [c for c in df.columns if c not in cols]]
    df.to_excel(ARCHIVO_EXCEL, index=False)
    generar_reporte_html(datos)


def analizar_carpeta():
    if not os.path.exists(CARPETA_IMAGENES):
        os.makedirs(CARPETA_IMAGENES)
        return

    archivos = []
    exts = ["*.jpg", "*.png", "*.webp", "*.jpeg"]
    for t in exts:
        archivos.extend(
            glob.glob(os.path.join(CARPETA_IMAGENES, "**", t), recursive=True)
        )

    if not archivos:
        console.print("[bold red]⚠️ No hay imágenes.[/]")
        return

    console.print(
        f"[bold green]🚀 Scanner V12 (Recursive + Batch Optimized) con {MODELO_SEO}...[/]"
    )

    resultados = []
    if os.path.exists(ARCHIVO_JSON):
        try:
            with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
                resultados = json.load(f)
        except Exception:
            pass

    # Crear conjunto de imágenes ya procesadas para búsqueda rápida
    procesados = {d.get("origen") for d in resultados}

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_total = progress.add_task("[green]Total", total=len(archivos))

        for imagen_path in archivos:
            # Usar path relativo como identificador (ej: "dijes/foto1.jpg")
            nombre = os.path.relpath(imagen_path, CARPETA_IMAGENES).replace("\\", "/")

            # Skip logic: Si ya existe, saltar
            if nombre in procesados:
                # console.print(f"[dim]Salteando {nombre}...[/]") # Opcional: reducir ruido
                progress.advance(task_total)
                continue

            # Si no existe, lo procesamos (Upsert ya no es necesario si saltamos,
            # pero mantenemos la lógica de append)

            task_img = progress.add_task(f"Analizando {nombre}...", total=None)
            inicio = time.time()
            try:
                response = client.chat(
                    model=MODELO_SEO,
                    messages=[
                        {
                            "role": "user",
                            "content": SYSTEM_PROMPT,
                            "images": [imagen_path],
                        }
                    ],
                    options={"temperature": 0.1, "num_ctx": 4096},
                )

                duracion = round(time.time() - inicio, 2)
                progress.remove_task(task_img)

                content = limpiar_json(response["message"]["content"])
                content_sanitizado = sanitarizar_texto(content)

                data = json.loads(content_sanitizado)
                data["origen"] = nombre
                data["tiempo_segundos"] = duracion

                resultados.append(data)
                guardar_resultados(resultados)

            except Exception as e:
                progress.remove_task(task_img)
                console.print(f"[red]Error: {e}[/]")

            progress.advance(task_total)

    console.print(f"\n[bold green]🏁 Listo: {ARCHIVO_HTML}[/]")


if __name__ == "__main__":
    analizar_carpeta()
