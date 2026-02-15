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

# --- PROMPT ANTI-ALUCINACIONES (V4) ---
SYSTEM_PROMPT = """
ROL: Eres el Gerente de Catálogo de "Kanela by Anier" (Córdoba, Argentina).
IDIOMA ESTRICTO: ESPAÑOL Rioplatense/Neutro. PROHIBIDO INGLÉS (Ej: No usar "Charm", usar "Dije". No usar "Gold", usar "Dorado").

TU MISIÓN: Analizar la imagen, determinar la coherencia visual y generar JSON.

REGLAS DE LÓGICA VISUAL:
1. Dije vs Colgante: Pieza pequeña con argolla simple = "Bijouterie/Dijes". Cadena incluida o grande = "Colgante".
2. Material: 
   - Brillo fantasía -> "aleacion".
   - Gris pulido -> "acero plateado".
   - Dorado intenso -> "acero dorado" (o aleacion si parece fantasía).
   - REGLA: Si es "aleacion", NUNCA pongas "Acero" en el título.

LISTAS CERRADAS (Elige EXACTAMENTE una opción):
A. CATEGORÍA: Bijouterie/Dijes, Bijouterie/Aros/Argollas, Bijouterie/Aros/Colgantes, Bijouterie/Aros/Ear Cuffs, Bijouterie/Pulseras, Bijouterie/Tobilleras, Bijouterie/Cadenas, Bijouterie/Collares Diseño, Bijouterie/Gargantillas, Bijouterie/Conjuntos, Bijouterie/Piercings, Carteras/Totes, Carteras/Bandoleras, Carteras/Sobres, Accesorios/Llaveros
B. ESTILO: Clasico, Punk, Gotico
C. MATERIAL: aleacion, acero dorado, acero plateado, lona, ecocuero
D. COLOR: rosa, rojo, blanco, beige, verde, marron, bordo, negro, azul, amarillo, dorado, plateado, multicolor.
E. GÉNERO: mujer, hombre, unisex.

--- FORMATO JSON ---
{
  "nombre_archivo": "...",
  "titulo": "...", 
  "categoria_producto": "...",
  "estilo_producto": "...",
  "material_producto": "...",
  "color_producto": "...",
  "genero_producto": "...",
  "short_description": "...",
  "long_description": "...",
  "tags": "..."
}
"""

# Configuración Visual para Terminal
custom_theme = Theme({"success": "green", "error": "bold red", "info": "cyan"})
console = Console(theme=custom_theme)
client = Client(host=OLLAMA_HOST)


def limpiar_json(texto):
    texto = re.sub(r"```json\s*", "", texto)
    texto = re.sub(r"```\s*$", "", texto)
    return texto.strip()


def generar_reporte_html(datos):
    """Genera HTML con Modo Oscuro persistente"""

    # CSS con Variables para facilitar el cambio de tema
    css = """
    :root {
        --bg-color: #f4f4f9;
        --card-bg: #ffffff;
        --text-color: #333333;
        --border-color: #eeeeee;
        --badge-bg: #eef;
        --badge-text: #333;
        --accent: #2c3e50;
        --shadow: rgba(0,0,0,0.05);
    }
    
    [data-theme="dark"] {
        --bg-color: #121212;
        --card-bg: #1e1e1e;
        --text-color: #e0e0e0;
        --border-color: #333;
        --badge-bg: #333;
        --badge-text: #ccc;
        --accent: #bb86fc;
        --shadow: rgba(0,0,0,0.5);
    }

    body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg-color); color: var(--text-color); padding: 20px; transition: background 0.3s, color 0.3s; }
    h1 { text-align: center; color: var(--accent); }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
    
    .card { 
        background: var(--card-bg); border-radius: 12px; 
        box-shadow: 0 4px 6px var(--shadow); display: flex; 
        overflow: hidden; border: 1px solid var(--border-color); 
        transition: transform 0.2s;
    }
    .card:hover { transform: translateY(-2px); }
    
    .img-box { 
        width: 150px; padding: 10px; display: flex; flex-direction: column; 
        align-items: center; justify-content: center; 
        border-right: 1px solid var(--border-color);
        background: var(--card-bg);
    }
    
    img { width: 140px; height: 140px; object-fit: contain; }
    /* Baja el brillo de las fotos en modo oscuro para que no encandilen */
    [data-theme="dark"] img { filter: brightness(0.9); }

    .timer { font-size: 0.8rem; margin-top: 5px; opacity: 0.7; }
    
    .info { padding: 15px; flex: 1; }
    h2 { font-size: 1rem; margin: 0 0 10px 0; color: var(--text-color); }
    
    .badges { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }
    .badge { 
        font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; 
        background: var(--badge-bg); color: var(--badge-text); border: 1px solid var(--border-color); 
    }
    
    .desc { font-size: 0.85rem; opacity: 0.9; border-top: 1px solid var(--border-color); padding-top: 10px; }
    details { margin-top: 5px; cursor: pointer; color: var(--accent); }
    
    /* Botón Flotante */
    .theme-toggle {
        position: fixed; top: 20px; right: 20px;
        background: var(--card-bg); border: 1px solid var(--border-color);
        color: var(--text-color); padding: 10px 15px; border-radius: 30px;
        cursor: pointer; box-shadow: 0 4px 10px var(--shadow);
        font-size: 1.2rem; z-index: 1000;
    }
    """

    # Javascript para cambiar y guardar la preferencia
    js = """
    <script>
        const toggleBtn = document.getElementById('theme-toggle');
        const body = document.body;
        
        // Cargar preferencia guardada
        const currentTheme = localStorage.getItem('theme');
        if (currentTheme) {
            body.setAttribute('data-theme', currentTheme);
            updateIcon(currentTheme);
        }

        function toggleTheme() {
            if (body.getAttribute('data-theme') === 'dark') {
                body.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
                updateIcon('light');
            } else {
                body.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                updateIcon('dark');
            }
        }
        
        function updateIcon(theme) {
            const btn = document.getElementById('theme-toggle');
            btn.innerHTML = theme === 'dark' ? '☀️ Modo Luz' : '🌙 Modo Oscuro';
        }
    </script>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kanela AI QA - V6</title>
        <style>{css}</style>
    </head>
    <body>
        <button id="theme-toggle" class="theme-toggle" onclick="toggleTheme()">🌙 Modo Oscuro</button>
        <h1>💎 Catálogo Visual Kanela V6</h1>
        <div class="grid">
    """

    for p in datos:
        ruta = f"./imagenes_a_procesar/{p.get('origen', '')}"
        html += f"""
        <div class="card">
            <div class="img-box">
                <img src="{ruta}" onerror="this.src='https://placehold.co/150?text=Error'">
                <span class="timer">⏱️ {p.get("tiempo_segundos", 0)}s</span>
            </div>
            <div class="info">
                <h2>{p.get("titulo", "Error de Lectura")}</h2>
                <div class="badges">
                    <span class="badge">{p.get("categoria_producto")}</span>
                    <span class="badge">{p.get("estilo_producto")}</span>
                    <span class="badge">{p.get("material_producto")}</span>
                    <span class="badge">{p.get("color_producto")}</span>
                </div>
                <div class="desc">
                    {p.get("short_description", "")[:120]}...
                    <details><summary>Ver Completo</summary><p>{p.get("long_description")}</p></details>
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
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols + [c for c in df.columns if c not in cols]]
    df.to_excel(ARCHIVO_EXCEL, index=False)
    generar_reporte_html(datos)


def analizar_carpeta():
    if not os.path.exists(CARPETA_IMAGENES):
        os.makedirs(CARPETA_IMAGENES)
        return
    archivos = []
    for t in ["*.jpg", "*.png", "*.webp", "*.jpeg"]:
        archivos.extend(glob.glob(os.path.join(CARPETA_IMAGENES, t)))
    if not archivos:
        console.print("[bold red]⚠️ No hay imágenes.[/]")
        return

    console.print(
        f"[bold green]🚀 Iniciando Scanner V6 (Dark Mode Ready) con {MODELO_SEO}...[/]"
    )

    resultados = []
    if os.path.exists(ARCHIVO_JSON):
        try:
            with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
                resultados = json.load(f)
        except Exception:
            pass  # PEP 8 Clean

    # Barra de Progreso Viva
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_total = progress.add_task("[green]Progreso Total", total=len(archivos))

        for imagen_path in archivos:
            nombre = os.path.basename(imagen_path)

            if any(d.get("origen") == nombre for d in resultados):
                progress.advance(task_total)
                continue

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
                data = json.loads(content)
                data["origen"] = nombre
                data["tiempo_segundos"] = duracion

                resultados.append(data)
                guardar_resultados(resultados)

            except Exception as e:
                progress.remove_task(task_img)
                console.print(f"[red]❌ Error con {nombre}: {e}[/]")

            progress.advance(task_total)

    console.print(
        f"\n[bold green]🏁 ¡Listo! Abre {ARCHIVO_HTML} y prueba el botón 'Modo Oscuro'.[/]"
    )


if __name__ == "__main__":
    analizar_carpeta()
