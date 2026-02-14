import os
import glob
import json
import pandas as pd
from ollama import Client
import re

# --- CONFIGURACIÓN ---
# Apuntamos a tu Windows (ajusta la IP si cambió, pero la 172... suele ser esa)
OLLAMA_HOST = "http://172.27.16.1:11434"
MODELO_SEO = "qwen2.5vl:3b"
CARPETA_IMAGENES = "./imagenes_a_procesar"
ARCHIVO_JSON = "productos_kanela.json"
ARCHIVO_EXCEL = "catalogo_kanela.xlsx"

# --- TU SÚPER PROMPT (INTEGRADO) ---
SYSTEM_PROMPT = """
ACTÚA COMO: Experto en SEO, GEO y AIEO para el e-commerce "Kanela by Anier", una tienda de joyería y accesorios ubicada en el Centro de Córdoba, Argentina. Tu tono debe adaptarse al estilo del producto (Gótico/Dark, Punk/Rebel o Clásico/Timeless) según el "Diccionario de Estilo de Kanela", el cual es el siguiente:

1. Estilo Gótico (Dark & Aesthetic)
Enfocado en el misterio y el detalle ornamental.

Palabras Recomendadas: Labrado, relieve, envejecido, oscuro, ornamental, victoriano, simbólico, dramático.

Elementos: Calaveras, rosas, dagas, murciélagos, cruces, pentagramas, piedras facetadas.

Sentido AIEO: "Look gótico", "estética oscura", "misticismo", "accesorio gótico de autor".

Palabras Prohibidas: Lindo, tierno, común, barato, negrito.

2. Estilo Punk (Rebel & Raw)
Enfocado en la fuerza de los materiales y la actitud urbana.

Palabras Recomendadas: Industrial, robusto, afilado, remaches, tachas, cadena gruesa, pulido espejo, agresivo.

Elementos: Spikes (púas), imperdibles, cierres, argollas grandes, cuero, acero macizo.

Sentido AIEO: "Estilo punk rock", "accesorio rebelde", "punk-chic", "urbano alternativo".

Palabras Prohibidas: Delicado, fino, sutil, discreto.

3. Estilo Clásico (Timeless & Elegante)
Para la línea de joyería tradicional y versátil.

Palabras Recomendadas: Atemporal, minimalista, sobrio, sofisticado, versátil, acabado premium, elegante.

Elementos: Perlas, formas geométricas, líneas puras, brillos sutiles, dijes básicos.

Sentido AIEO: "Accesorio de uso diario", "joyería clásica", "regalo elegante", "minimalismo".

Palabras Prohibidas: Simple (usar "minimalista"), básico (usar "atemporal"), cualquiera.

Recordatorio para tus "Tags" (GEO/AIEO)
No olvides rotar estas etiquetas para posicionarte en las zonas clave de Córdoba Capital:

Zonas: centro-cordoba, nueva-cordoba, guemes-cordoba.

Intención: regalo-mujer, moda-alternativa, san-valentin, aesthetic.


Debes realizar una tarea la cual es la siguiente:

TAREA: Analiza la imagen del producto proporcionada y genera los metadatos para WooCommerce siguiendo ESTRICTAMENTE estas reglas:

1. NOMBRE DEL ARCHIVO DE IMAGEN:

- Formato: kebab-case (todo-minuscula-separado-por-guiones).

- Estructura: [tipo-producto]-[material/color]-[estilo]-[característica-clave].jpg

- Regla: Prioriza español, pero incluye anglicismos de nicho si aplica (ej: "wings", "choker", "tote"). NUNCA uses tildes ni ñ.


2. TÍTULO DEL PRODUCTO:

- Estructura: [Nombre del Producto] + [Atributo Clave] + [Estilo/Uso].

- Regla: NO incluyas "| Kanela by Anier" al final. Debe ser limpio y descriptivo. Si es un set, inicia con "Set 2 en 1".


3. DESCRIPCIÓN CORTA (SHORT DESCRIPTION):

- Formato: HTML. Usa una lista <ul> con 3-4 puntos clave (<li>) persuasivos.

- Contenido: Destaca diseño, material y estilo.

- CIERRE OBLIGATORIO: Agrega este bloque HTML exacto al final:

  <p>

  📍 <strong>Retiro inmediato:</strong> Zona Plaza San Martín, Córdoba.<br>

  🚚 <strong>Envíos a todo el país:</strong> Despachamos tu pedido en 24hs.

  </p>


4. DESCRIPCIÓN LARGA (LONG DESCRIPTION):

- Párrafo 1 (Narrativa): Texto emocional de 2-3 líneas vendiendo el estilo (usa palabras como "místico", "atemporal", "robusto" según corresponda).

- Párrafo 2 (Técnico): Bloque HTML con título <h3>Especificaciones Técnicas</h3> y una lista <ul> con: Tipo, Diseño, Material, Color, Medidas (estimadas si no las tienes), Estilo.

- CIERRE OBLIGATORIO: Agrega este bloque de confianza al final:

  ---

  💎 <strong>Somos Kanela by Anier:</strong> Tu tienda de accesorios de confianza en el centro de Córdoba Capital.

  ✅ Atención personalizada.

  ✅ Envíos a todo el país y retiro en local.


5. TAGS (ETIQUETAS):

- Genera 10-12 etiquetas separadas por comas.

- Mezcla: Tipo de producto, Estilo (ej: Dark Aesthetic, Coquette), Material, Uso (ej: Regalo, Insumos) y GEO (ej: Joyería Córdoba).


SALIDA: Devuelve SOLO un objeto JSON con las claves: "nombre_archivo_img", "titulo_producto", "descripcion_corta", "descripcion_larga", "tags".
y también debes devolver una tabla en formato Excel .xlsx con las mismas claves.
"""

# Inicializamos cliente
client = Client(host=OLLAMA_HOST)


def limpiar_json(texto):
    """Limpia los bloques de código ```json que a veces pone la IA"""
    texto = re.sub(r"```json\s*", "", texto)
    texto = re.sub(r"```\s*$", "", texto)
    return texto.strip()


def guardar_resultados(datos):
    """Guarda en JSON y Excel en cada paso por seguridad"""
    # 1. Guardar JSON
    with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

    # 2. Guardar Excel
    df = pd.DataFrame(datos)
    df.to_excel(ARCHIVO_EXCEL, index=False)
    print(f"💾 Guardado: {len(datos)} productos en JSON y Excel.")


def analizar_carpeta():
    if not os.path.exists(CARPETA_IMAGENES):
        os.makedirs(CARPETA_IMAGENES)
        print(f"📂 Carpeta creada: '{CARPETA_IMAGENES}'. Pon tus fotos ahí.")
        return

    # Buscar imágenes
    tipos = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
    archivos = []
    for tipo in tipos:
        archivos.extend(glob.glob(os.path.join(CARPETA_IMAGENES, tipo)))

    if not archivos:
        print("⚠️ No hay imágenes para procesar.")
        return

    print(f"🚀 Iniciando Scanner Kanela con {MODELO_SEO}...")

    # Cargar datos previos si existen (para no perder trabajo)
    resultados = []
    if os.path.exists(ARCHIVO_JSON):
        try:
            with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
                resultados = json.load(f)
        except Exception:
            resultados = []

    # --- BUCLE DE PROCESAMIENTO ---
    for imagen_path in archivos:
        nombre_original = os.path.basename(imagen_path)

        # Evitar procesar si ya existe en la lista
        if any(d.get("origen") == nombre_original for d in resultados):
            print(f"⏩ Saltando {nombre_original} (ya procesado).")
            continue

        print(f"🔍 Analizando: {nombre_original}...")

        try:
            response = client.chat(
                model=MODELO_SEO,
                messages=[
                    {"role": "user", "content": SYSTEM_PROMPT, "images": [imagen_path]}
                ],
            )

            # Procesar respuesta
            contenido = response["message"]["content"]
            contenido_limpio = limpiar_json(contenido)

            try:
                # Intentamos convertir el texto a objeto JSON real
                datos_producto = json.loads(contenido_limpio)

                # Agregamos el nombre original para referencia
                datos_producto["origen"] = nombre_original

                # Agregamos a la lista maestra
                resultados.append(datos_producto)

                print(
                    f"✅ Éxito: {datos_producto.get('titulo', 'Producto sin título')}"
                )

                # Guardamos INMEDIATAMENTE (por si crashea después)
                guardar_resultados(resultados)

            except json.JSONDecodeError:
                print(
                    f"⚠️ Error: La IA no devolvió un JSON válido para {nombre_original}."
                )
                print("Respuesta cruda:", contenido)

        except Exception as e:
            print(f"❌ Error crítico con {nombre_original}: {e}")

    print("\n🎉 ¡Proceso terminado! Revisa 'catalogo_kanela.xlsx'.")


if __name__ == "__main__":
    analizar_carpeta()
