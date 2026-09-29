# Análisis de la propuesta y plan de implementación — the-doc-project

> Fecha: 2026-09-29 · Estado del repo analizado: rama `main`, commit `4a88acc`

Este documento revisa el planteamiento inicial (plantillas → motor → renderizado → generador de plantillas) y el contenido actual del repositorio. Para cada parte indica **qué es correcto**, **qué es mejorable** y **qué se puede descartar o rediseñar**, y propone un plan por fases.

**Objetivo del proyecto:** un software **determinista** (repetible; los documentos los genera código, no un LLM), **genérico** (sirve para distintos tipos de informe) y **simple** (pocas dependencias y pocas piezas).

---

## 0. Requisitos confirmados

| Tema | Decisión |
|---|---|
| Determinismo | Mismas plantillas + mismos datos + misma versión del motor → **mismo informe en contenido y aspecto**. En tiempo de ejecución no interviene ningún LLM. No se exige igualdad byte a byte ni comparación por hash (Word tampoco lo hace) |
| PDF | Imprimible y **PDF/A** |
| Integración | Uso manual y dentro de un workflow automatizado. Ambos casos se cubren con **la misma CLI dentro de Docker** (§6.1). **API aplazada**: primero el motor y las plantillas |
| Temas | **Uno por departamento**: `elausa_lab` (laboratorio, amarillo/azul) y `elausa_cyber` (cyber, gris/naranja). Unificarlos es trabajo futuro de la empresa |
| Informes piloto | **Ambos**: el de ensayos (plantillas JSON) y el Vulnerability Intake (`generar_informe.py`) |
| Contenido | Tablas, imágenes, **gráficas generadas a partir de los datos** y **textos libres** redactados por el usuario |
| Origen de datos | **CSV / Excel**, con un formato que se define en este proyecto |
| Datos faltantes | El campo se deja **vacío** y el software **avisa** de qué falta |
| Quién edita plantillas | Primero desarrolladores y después personal no técnico |
| Trazabilidad | Deseable: basta con que quede registrada en los logs |
| Idiomas | Solo uno |
| Infraestructura | Docker y logs de uso y de error. Sin base de datos |

### Dependencias

**Criterio:** una dependencia entra si **ahorra código propio que tendría que mantenerse y que es propenso a bugs**. Queda fuera si solo añade piezas, configuración o superficie que se puede romper. Para todo lo demás se usa la biblioteca estándar de Python (`json`, `csv`, `html`, `argparse`, `logging`, `hashlib`, `base64`).

| Dependencia | Por qué entra | Qué evita |
|---|---|---|
| **WeasyPrint** | Es la única forma razonable de sacar **PDF/A** desde HTML. Repite cabecera y pie en cada página, numera "página X de N" y hace saltos de página automáticos | Chrome/Edge headless (el del script actual), que no genera PDF/A |
| **Pydantic v2** | Valida las plantillas de forma declarativa: rechaza erratas (`extra="forbid"`), distingue el tipo de componente por el campo `type`, da errores con la ruta exacta (`sections[1].blocks[0].width_ratio`) y exporta **JSON Schema** (autocompletado en el editor y base del futuro generador) | Cientos de líneas de validación escritas a mano, que es donde más bugs aparecerían |
| **Jinja2** | El HTML de cada tema vive en ficheros `.html.j2`, con **escape automático** de todos los datos. `StrictUndefined` hace que una variable mal escrita dé error en lugar de salir vacía | Construir HTML con f-strings en Python, donde un solo `html.escape` olvidado es un bug. `string.Template` no basta: las cabeceras de los dos temas necesitan bucles y condicionales |
| **openpyxl** | Leer y escribir `.xlsx`. La stdlib no lo hace | pandas: mucho más pesado para solo leer celdas |
| **matplotlib** | Gráficas → SVG | Dibujar ejes, escalas y leyendas a mano |
| pytest (solo desarrollo) | Ya se usa en el repo | — |

Las versiones se **fijan** (Pydantic, por ejemplo, rompió compatibilidad al pasar de v1 a v2), de modo que una actualización es siempre una decisión explícita.

**Evaluados y fuera:**

| Dependencia | Motivo |
|---|---|
| FastAPI | La API está aplazada |
| markdown-it-py | El formato `text` (párrafos y listas) basta por ahora. Si hacen falta negritas o tablas dentro del texto, se **añade esta librería** en vez de ampliar un parser propio |
| docker compose | Sin API no hay servicio que levantar: basta `docker run` |
| Formato de logs JSON | `logging` en texto plano cubre el requisito |

**veraPDF** no es una dependencia del software: es una herramienta externa para comprobar a mano, en la fase 0, que el PDF/A es válido.

---

## 1. ¿Motor genérico con plantillas JSON, o un monolito por informe?

### Qué es un monolito como `generar_informe.py`

El script tiene ~300 líneas y hace **todo** para un único informe: valores por defecto, CSS, HTML de cabecera y pie, las tablas de las tres páginas, la carga y validación de datos y la impresión a PDF. Lo generó un LLM y funciona.

Mirándolo por dentro, sus ~300 líneas se reparten así:

| Parte del script | ¿Específica de ELA-VH-001? |
|---|---|
| Textos fijos (`INTRO`, títulos de tabla, etiquetas, `DECISIONS`) | **Sí**, pero es contenido, no lógica |
| Distribución (qué tablas, en qué orden, anchos de columna, filas con 1 o 2 pares etiqueta/valor) | **Sí**, pero se puede describir como datos |
| Lista de campos y valores por defecto (`DEFAULTS`) | **Sí**, es el contrato de datos |
| CSS, cabecera, pie, escape de HTML, `td()`, `grid_table()` | **No**: genérico |
| Carga y validación del JSON de datos, CLI, PDF por navegador | **No**: genérico |

Es decir, **lo que es propio del informe es contenido y distribución, no código**. Eso es lo que se puede escribir en JSON.

### Comparación

| Criterio | Un monolito por informe | Motor + plantillas JSON |
|---|---|---|
| Coste del primer informe | ✅ Bajo | ❌ Alto: hay que hacer el motor |
| Coste del informe N | ❌ Otro script de ~300 líneas que revisar y testear | ✅ Solo JSON |
| Cambio de marca, logo o pie | ❌ Hay que tocar N scripts | ✅ Un tema |
| Corregir un bug (p. ej. el texto que se recorta) | ❌ En N sitios, y cada script generado por LLM tiene una estructura distinta | ✅ Una vez |
| Edición por personal no técnico | ❌ Imposible: es código | ✅ Posible, y más fácil con el generador |
| Contrato de datos, Excel vacío, avisos de faltantes | ❌ Hay que repetirlo en cada script | ✅ Se deriva automáticamente de la plantilla |
| Libertad de diseño | ✅ Total | ⚠️ Limitada a lo que permitan los tipos de componente |
| Determinismo | ✅ Igual en los dos | ✅ Igual en los dos |

Hay una opción intermedia: una **librería Python compartida más un script corto por informe**. Evita repetir código, pero cada informe nuevo sigue siendo código. No sirve si el objetivo es que personal no técnico cree informes.

### Veredicto

**Sí tiene utilidad.** Con dos informes ya y la previsión de más, y con personal no técnico editando plantillas, el motor genérico sale a cuenta a partir del segundo o tercer informe. Los monolitos solo compensan si fueran pocos informes, muy distintos entre sí y mantenidos siempre por desarrolladores. No es el caso.

**La condición para que salga a cuenta** es mantener un **conjunto pequeño de tipos de componente genéricos** (§2) y aplicar esta regla:

> Un informe nuevo es **solo JSON**. Si necesita algo que el motor no hace, se añade una **opción genérica** a un tipo existente, nunca código `if informe == ...`.

Si cada informe acabara pidiendo su propio tipo de componente, se estarían escribiendo monolitos dentro del motor, que es peor que tenerlos fuera.

### Prueba: `generar_informe.py` expresado con los tipos genéricos

Todo el Vulnerability Intake cabe en los tipos de §2, con dos opciones genéricas nuevas: **filas con dos pares etiqueta/valor** y **columna de casillas**.

| Elemento del script | Cómo se expresa |
|---|---|
| Cabecera (logo, título, Code/Rev/Date) | `header` con su HTML de tema y ranuras |
| Pie (confidencialidad, barra, "n / N") | `footer`. La barra de progreso que cambia en cada página es lo único que no sale directamente en CSS: se deja como **barra fija**, o se hace un segundo render (~10 líneas) si se quiere mantener |
| Título h1 + párrafo de introducción | `text` (el título viene de un dato; la intro es un texto fijo en la plantilla) |
| REPORT SUMMARY, VULNERABILITY INTAKE, INITIAL INFORMATION REVIEW, TRIAGE ASSESSMENT | `key_value` con filas de 1 o 2 pares y `min_height` por fila |
| TRIAGE RESULT (caja naranja) | `key_value` con `"variant": "highlight"`: una clase CSS del tema |
| RELEASED BY, DOCUMENT HISTORY | `table` con `min_rows: 2` |
| TRIAGE DECISION | `table` con **filas fijas** definidas en la plantilla y una **columna de casillas** ligada a `triage_decision`, seguida de un `key_value` |
| Páginas 1 / 2 / 3 | Secciones con `page_break_before` |
| `DEFAULTS` con placeholders "[...]" | Contrato de datos + Excel vacío con notas de guía (§3.3) |

Ejemplo ilustrativo del bloque REPORT SUMMARY:

```json
{
  "component_id": "vh_report_summary",
  "type": "key_value",
  "source": "summary",
  "title": "REPORT SUMMARY",
  "column_widths": [0.23, 0.30, 0.13, 0.34],
  "rows": [
    { "cells": [ { "label": "Vulnerability ID", "value_key": "vulnerability_id" } ] },
    { "cells": [ { "label": "Detection / reception date", "value_key": "detection_date" } ] },
    { "cells": [
        { "label": "Affected product / family", "value_key": "product" },
        { "label": "Affected version(s)", "value_key": "versions" } ] },
    { "cells": [ { "label": "Vulnerability summary", "value_key": "summary", "format": "text" } ] }
  ]
}
```

Una fila con un solo par ocupa el ancho completo. El mismo tipo `key_value` sirve para `sample_info_table` del informe de ensayos, con `"column_widths": [0.3, 0.7]`.

**Temas:** cada departamento conserva el suyo. El informe de ensayos usa `elausa_lab` (amarillo/azul) y el Vulnerability Intake usa `elausa_cyber` (gris/naranja, sacado del CSS del script). Como la base de cada informe indica su tema, ninguno de los dos necesita código propio. Si la empresa unifica la imagen en el futuro, basta con cambiar `theme` en las bases.

---

## 2. Parte 1 — Plantillas

### ✅ Correcto

- **Separar estructura, componentes, layout y tema.** Es la decisión más importante y está bien tomada: permite cambiar el estilo sin tocar la estructura y reutilizar componentes entre informes.
- **Tokens visuales separados de los estilos de componente.**
- **JSON como formato**: fácil de generar por programa (para el futuro generador) y se diffea bien en Git.
- **Anchos por ratio** (`column_widths`, `width_ratio`).
- **La lógica que depende de los datos va en Python**, no en la plantilla (PASS/FAIL, por ejemplo).
- **`repeatable`** en `test_block`: una plantilla genérica tiene que poder repetir bloques según los datos.

### 🔧 Mejorable, con errores concretos que hay que corregir

**a) Los IDs no cuadran entre la base y los componentes.** Solo 4 de los 11 referenciados existen:

| En `base/elausa_report.json` | `component_id` real |
|---|---|
| `report_header` | `header` |
| `document_history_table` | `document_history` |
| `tests_summary_table` | `performed_tests` |
| `equipment_list_table` | `equipment_list` |
| `setup_description_table` | `setup_table` |
| `appendix_table` | `appendix` |
| `footer_table` | `footer` |

→ Regla: **`component_id` == nombre del fichero**, y el loader comprueba que toda referencia existe.

**b) Esquemas inconsistentes entre componentes.**
- `rows` va dentro de `props` en unos y fuera en `test_block`; `alignment_defaults` está fuera de `props` en `footer_block`.
- `alignment_defaults` es plano en unos y por parte en `sample_info_table`.
- Las claves de `alignment_overrides` cambian (`value_key`, `value`, `title`, `left_value`).
- `rows` es un objeto en `evaluation_table` y una lista en los demás.
- En tipografías aparecen tanto `italic` como `italics`.
- Erratas: `"enaled"`, `mesurement_units`, `"results title"` (con espacio) como clave, `"title": "report_sample"`.

→ Una sola forma por tipo de componente, fijada en **modelos Pydantic** (§3.1). Las claves desconocidas se rechazan, así que estas erratas saltan al cargar la plantilla y no al ver el PDF.

**c) `order` es redundante y ya está duplicado** (dos `order: 3` en `portada`). → Se elimina y cuenta el orden de la lista.

**d) La base no referencia un layout.** → Añadir `"layout": "a4_standard"`.

**e) Cabecera y pie modelados como "secciones".** Son elementos de **página**, no contenido que fluye. → Se referencian desde un bloque `page` de la base:

```json
{
  "template_id": "elausa_test_report",
  "version": "1.0.0",
  "theme": "elausa_lab",
  "layout": "a4_standard",
  "page": { "header": "header_block", "footer": "footer_block" },
  "sections": [
    { "id": "portada", "blocks": [ { "component": "sample_info_table", "width_ratio": 0.66, "align": "center" } ] },
    { "id": "info_pruebas", "page_break_before": true, "blocks": [ ... ] }
  ]
}
```

Sobre tu duda de **darles carpeta propia a cabecera y pie: no hace falta.** Siguen siendo componentes; solo cambia desde dónde se referencian.

**f) Páginas frente a secciones.** **Lo correcto es el flujo**: las secciones fluyen, `page_break_before` fuerza un salto y WeasyPrint pagina. Las páginas de alto fijo de `generar_informe.py` recortan el texto que no cabe (`overflow:hidden`), y en un informe de calidad eso es **perder datos en silencio**.

**g) Estilo dinámico con token inexistente** (`evaluation_status`). → En el componente se declara `"status_classes": {"PASS": "pass", "FAIL": "fail"}` y el tema define `.pass` y `.fail`.

**h) Sin versión de plantilla.** → Campo `version` en la base, que se registra en los logs.

**i) Sin contrato de datos explícito.** → El motor lo **deriva** de los componentes (`source` + `value_key` + `columns`). De ahí salen los avisos de datos faltantes y el Excel vacío.

### ♻️ Descartable o rediseñable

- **El modelo recursivo de `header_block`** (contenedores anidados) reinventa CSS Grid dentro de JSON. → La cabecera se define con una **plantilla HTML del tema** (`header.html.j2`) que recibe los datos (`title`, `code`, `revision`...). Cada departamento tiene la suya, con su propia estructura. Las dimensiones van en CSS. Igual para el pie.
- **`component_styles.json`** → se sustituye por **`theme.css`**, con clases por tipo de componente (`.c-table`, `.c-key-value`...) y variantes (`.v-highlight`). `visual_tokens.json` **se mantiene** y se convierte en variables CSS (`--color-bg-primary`) con unas pocas líneas de Python. `case` pasa a `text-transform`.
- **`templates/variants/`**: no crearlo hasta que exista una segunda variante real.
- **Dos layouts casi iguales**: se mantienen; no merece la pena crear herencia.

### Tipos de componente (conjunto mínimo)

| Tipo | Uso | Opciones genéricas |
|---|---|---|
| `table` | Título + cabeceras + filas de datos | `min_rows`, `fixed_rows`, columna de casillas |
| `key_value` | Filas etiqueta/valor | 1 o 2 pares por fila, `min_height`, `section_title`, `variant` |
| `text` | Título o párrafo, fijo o de un dato | `format: text` |
| `image` | Imagen desde un fichero de entrada | ancho |
| `chart` | Gráfica desde una tabla de datos | `kind` (`line`/`bar`), `x`, `y` |
| `group` | Lista de componentes | `repeat_over: "<source>"` (test_block, anexos) |
| `header` / `footer` | HTML del tema con ranuras | — |

`test_block` deja de ser un tipo y pasa a ser un `group` con `repeat_over: "tests"` que contiene `key_value`, `table` y `chart`.

---

## 3. Parte 2 — Motor de construcción

### ✅ Correcto

- **Pipeline por etapas** (cargar → validar → resolver → renderizar).
- **Documento resuelto intermedio (la "receta")**: desacopla el motor del renderizado y se puede volcar para depurar (`docgen recipe`).
- **Modelos que se autovalidan** (`resolved_content.py`) y **tests desde el principio**. La idea se mantiene; en §3.1 se hace con Pydantic.

### 🔧 Mejorable

**3.1 Carga y validación con Pydantic.** Un modelo por tipo de componente, unidos en una unión discriminada por `type`, y todos con `extra="forbid"`. Pydantic cubre la forma de los datos: tipos, campos obligatorios, claves desconocidas y la ruta del error. El loader añade las comprobaciones que dependen de otros ficheros:
- las referencias: componente, tema y layout existen; los tokens existen; `len(column_widths)` coincide con el número de columnas y los anchos suman 1; no hay IDs duplicados.

`schema_validator.py` desaparece (lo hace Pydantic) y `semantic_validator.py` queda como unas pocas funciones dentro de `loader.py`. Los modelos resueltos de `resolved_content.py` pueden pasar a Pydantic para que todo sea igual; su comportamiento no cambia y sus tests siguen valiendo.

**3.2 Flujo de datos.**

```
Excel/CSV + textos .txt + imágenes ──(data_input)──► datos (dict) ──┐
                                                                     ├─► RESOLVER ──► receta ──(render_html)──► HTML ──(WeasyPrint)──► PDF/A
plantillas JSON ──(loader)──────────────────────────────────────────┘
```

- **data_input**: Excel (`openpyxl`) o CSV (`csv`) → diccionario. También se acepta un JSON de datos directamente.
- **resolver** (Python puro): une plantilla y datos por `source` / `value_key`; aplica `min_rows`, `repeat_over` y las clases de estado; y **recoge los avisos**.
- **render_html** (Jinja2, con `autoescape` y `StrictUndefined`): una plantilla por tipo de componente (`components/table.html.j2`...), elegida por el nombre del tipo, más la cabecera y el pie de cada tema. Las plantillas **solo pintan**: la lógica (binding, estados, avisos) se queda en el resolver.
- Nada de sintaxis Jinja dentro de los JSON de plantilla. Si hace falta interpolar una etiqueta ("Report {code}"), se usa `str.format_map`.

**3.3 Formato de Excel.**
- **Una hoja por `source`.**
- Hoja clave-valor: 2 columnas `campo | valor`.
- Hoja tabular: la primera fila son las cabeceras y cada fila siguiente es un registro.
- Repetibles: hoja `tests` con una fila por test; hoja `results` con una columna `test_number` que enlaza cada resultado con su test (de ahí salen tablas y gráficas).
- Imágenes: se indica el nombre de fichero, que se busca en la carpeta de entrada.
- `docgen data-template <plantilla>` **genera el Excel vacío** desde el contrato de datos, con una nota de guía en cada campo. Sustituye a los placeholders `[...]` y al comando `datos` del script actual.

**3.4 Textos libres** (evaluaciones, justificaciones, descripciones):
- Formato `text`: texto plano. Una línea en blanco separa párrafos y las líneas que empiezan por `- ` se muestran como lista. Son ~15 líneas de código propio, sin librería.
- Se escriben **en la celda de Excel** (Alt+Enter para saltos de línea) o, si son largos, **en un fichero `.txt` aparte**, indicado en la celda como `@evaluacion_test1.txt`.
- Si más adelante hacen falta negritas o tablas dentro del texto, se valora añadir Markdown. Hoy no.

**3.5 Datos faltantes.** La celda queda **vacía** y se genera un aviso (`sample_info.part_number falta (sample_info_table)`) que va al log como `WARNING` y se imprime al final de la ejecución de la CLI. Los campos u hojas **desconocidos** también avisan, porque suelen ser erratas.

### ♻️ Descartable

- `content_resolvers/` (registro + clase base + un fichero por tipo) → basta **un `dict` en `resolver.py`**.
- `binding_resolver.py`, `document_resolver.py` y `style_resolver.py` → un solo `resolver.py`. El estilo va en CSS.
- `resolved_document.py` y `styles.py` (vacíos) → los modelos resueltos se quedan juntos en `models.py`.

---

## 4. Parte 3 — Renderizado

### ✅ Correcto

- **HTML como paso intermedio y PDF a partir del HTML**: HTML para previsualizar y PDF para archivar, desde una sola fuente.
- Del script actual se conservan: el **escape de todos los datos**, el **logo incrustado en base64** y el **test de humo** que cuenta páginas.

### 🔁 Rediseñar

**4.1 WeasyPrint en lugar de Chrome/Edge headless.**

| Criterio | Chrome/Edge (actual) | **WeasyPrint** |
|---|---|---|
| PDF/A | ❌ No | ✅ `pdf_variant="pdf/a-3b"` |
| Cabecera/pie repetidos y "página X de N" | ❌ A mano, con páginas de alto fijo que recortan | ✅ CSS nativo (`@page`, `counter(page)` / `counter(pages)`) |
| Saltos de página | Limitados | ✅ `break-before`, `break-inside: avoid`, cabecera de tabla repetida |
| Requiere navegador instalado | ❌ Sí | ✅ No |
| CSS moderno | ✅ Completo | ⚠️ Flex/Grid parcial. Para tablas y bloques, perfecto |

`render_pdf.py` son unas 20 líneas. `regisrty.py` sobra: la plantilla Jinja se elige por el nombre del tipo.

**4.2 Entorno controlado** (para que el aspecto sea el mismo en todas partes):
- **Fuentes dentro de la imagen Docker**. **Nunca Google Fonts** por red, que es lo que hace ahora el script. PDF/A además exige incrustar las fuentes.
- WeasyPrint **sin acceso a red**, solo a ficheros locales, por seguridad: los datos vienen de Excel.
- Versiones fijadas de la imagen base y de las dependencias.

**4.3 Gráficas**: matplotlib → SVG incrustado en el HTML. El componente `chart` declara `kind`, `x`, `y`, `source` y títulos de ejes; los colores salen de los tokens del tema.

### ♻️ Descartable

- **`generar_informe.py` y su test**, una vez portado a plantillas JSON (fase 5). Hasta entonces sirve de **referencia visual**.

---

## 5. Parte 4 — Generador de plantillas

- ✅ **Dejarlo en segundo plano es correcto**: necesita un formato de plantilla estable, y hoy no lo es.
- Mientras tanto, estas piezas del plan ya lo facilitan:
  - **JSON Schema exportado desde Pydantic**: autocompletado y validación en el editor desde ya, y la base sobre la que se construirá el generador;
  - **`docgen validate`**, con errores legibles;
  - **`docgen render --html`** como vista previa rápida;
  - **`docgen data-template`**, que da el Excel de datos vacío.
- Más adelante: un formulario, para crear plantillas y para rellenar datos, incluidos los textos libres. La tecnología se decide entonces.

---

## 6. Requisitos transversales

### 6.1 Una sola CLI (`argparse`)

- `docgen render --template elausa_test_report --data datos.xlsx -o informe.pdf [--html]`
- `docgen validate <plantilla>` · `docgen data-template <plantilla>` · `docgen recipe` (depuración)

Tanto el **uso manual** como el **workflow automatizado** usan esta CLI: el workflow ejecuta `docker run --rm -v ... docgen render ...` y lee el código de salida y el log.

**API HTTP: aplazada (decisión confirmada).** Solo hará falta si el workflow no puede lanzar un contenedor (por ejemplo, si tiene que ser un servicio remoto siempre levantado). En ese caso, será una capa fina sobre la misma función `render()`, y el framework se elegirá entonces.

### 6.2 Docker

- **Una imagen**: `python:3.12-slim` con la versión fijada, las dependencias de sistema de WeasyPrint (Pango), las fuentes y el usuario no root.
- Volúmenes: `templates/`, `input/`, `output/` y `logs/`. Así se editan plantillas sin reconstruir la imagen.

### 6.3 Logs (`logging` de la stdlib)

- Salida a stdout (Docker la recoge) y a `logs/docgen.log` con `RotatingFileHandler`.
- **Uso** (`INFO`), una línea por generación: `run_id`, plantilla + `version`, SHA-256 de datos y PDF (`hashlib`, para saber qué ficheros produjeron cada informe), duración y número de avisos.
- **Avisos** (`WARNING`): datos faltantes o desconocidos.
- **Errores** (`ERROR`, con traceback).

---

## 7. Estructura de repositorio propuesta

Se aprovecha la carpeta `core/` que ya existe, aplanada:

```
the-doc-project/
├── pyproject.toml            # weasyprint, pydantic, jinja2, openpyxl, matplotlib (+ pytest), versiones fijadas; entrypoint "docgen"
├── Dockerfile
├── conventions.md            # actualizado a este diseño
├── core/
│   ├── models.py             # Pydantic: definiciones de plantilla + receta (incluye resolved_content.py actual)
│   ├── loader.py             # carga (Pydantic) + comprobación de referencias + export de JSON Schema
│   ├── data_input.py         # Excel/CSV/JSON/.txt → datos; contrato de datos; Excel vacío
│   ├── resolver.py           # plantilla + datos → receta + avisos
│   ├── render_html.py        # Jinja2 (autoescape + StrictUndefined)
│   ├── render_pdf.py         # WeasyPrint, PDF/A
│   ├── charts.py             # matplotlib → SVG
│   └── cli.py                # argparse + configuración de logging
├── templates/
│   ├── base/ · components/ · layouts/
│   ├── html/components/*.html.j2                                                             # una plantilla por tipo, común a todos los temas
│   └── themes/
│       ├── elausa_lab/{visual_tokens.json, theme.css, header.html.j2, footer.html.j2, logo.png}    # laboratorio (actual themes/elausa)
│       ├── elausa_cyber/{visual_tokens.json, theme.css, header.html.j2, footer.html.j2, logo.png}  # cyber (sacado de generar_informe.py)
│       └── fonts/                                                                            # compartidas
└── tests/
```

Se pasa de ~20 ficheros vacíos a 8 módulos. Un módulo se divide cuando crezca, no antes.

---

## 8. Plan de implementación por fases

Cada fase termina con algo que se puede ejecutar y comprobar.

### Fase 0 — Limpieza y prueba de riesgo
- [ ] Commitear `.gitignore` (`__pycache__/`, `*.pyc`, `output/`, `logs/`) y sacar los `.pyc` del repo.
- [ ] `pyproject.toml` con las dependencias de §0 y sus versiones fijadas; quitar los `sys.path.append` de los tests.
- [ ] Añadir `logo.png` al repo, que falta.
- [ ] **POC en Docker**: un HTML con cabecera/pie repetidos, "página X de N", una tabla de 3 páginas y un SVG de matplotlib → WeasyPrint PDF/A-3b. Comprobar que valida en veraPDF y que el texto largo pasa de página sin recortarse.

### Fase 1 — Formato de plantilla estable
- [ ] Corregir los JSON según §2 y definir los tipos de §2 como modelos Pydantic.
- [ ] Exportar el JSON Schema y referenciarlo con `$schema` en cada JSON, para tener validación en el editor.
- [ ] Renombrar `themes/elausa` a `themes/elausa_lab`.
- [ ] `loader.py` + `docgen validate`.
- [ ] Actualizar `conventions.md`.
- **Salida:** `docgen validate elausa_test_report` pasa, y si se rompe un ID a propósito, falla con un mensaje claro.

### Fase 2 — Entrada de datos
- [ ] Contrato de datos derivado de la plantilla.
- [ ] `data_input.py`: Excel/CSV/JSON, textos `@*.txt` y avisos.
- [ ] `docgen data-template` → Excel vacío con notas.
- **Salida:** Excel generado → rellenado → datos, con test.

### Fase 3 — Resolver
- [ ] `resolver.py`: binding, `min_rows`, `repeat_over`, filas fijas, casillas, clases de estado y avisos.
- [ ] `docgen recipe` + tests unitarios.

### Fase 4 — Render del piloto 1 (informe de ensayos)
- [ ] `theme.css` + tokens → variables CSS; `header.html.j2` / `footer.html.j2`; una plantilla Jinja por tipo.
- [ ] `charts.py`; `render_pdf.py` con PDF/A; test de humo del PDF.
- **Salida:** informe de ensayos completo, con tests repetidos y una gráfica, que valida en veraPDF.

### Fase 5 — Piloto 2: `generar_informe.py` → plantillas JSON
- [ ] Crear el tema `elausa_cyber` (tokens y CSS a partir del CSS del script, más su cabecera y su pie).
- [ ] Expresar ELA-VH-001 **solo con JSON** (§1), añadiendo como opciones genéricas las filas de 2 pares, las filas fijas y las casillas.
- [ ] Comparar visualmente con la salida del script y, cuando sea equivalente, **eliminar el script**.
- **Salida:** dos informes distintos, con dos temas distintos, salen del mismo motor sin código específico de ninguno.

### Fase 6 — CLI final, Docker y logs
- [ ] `cli.py` con logs de uso, avisos y errores.
- [ ] `Dockerfile` final; los tests se ejecutan dentro de la imagen.
- **Salida:** `docker run ... docgen render ...` genera los dos informes y deja constancia en `logs/`.

### Fase 7 — Generador de plantillas (cuando lo anterior esté estable)
- [ ] Decidir cómo será, a partir de lo aprendido con los dos pilotos.

---

## 9. Resumen

| Parte | Veredicto | Acción principal |
|---|---|---|
| Motor genérico frente a monolitos | ✅ Útil a partir del 2.º–3.er informe | Informe nuevo = solo JSON; lo que falte se añade como opción genérica |
| 1. Plantillas | ✅ La separación es correcta · 🔧 los JSON son incoherentes | IDs = fichero, una forma por tipo, cabecera/pie en `page`, estilos en CSS |
| ↳ ¿Carpeta propia para cabecera/pie? | ♻️ No hace falta | Componentes referenciados desde `page` |
| 2. Motor | ✅ Pipeline y receta correctos | Pydantic para validar plantillas; Excel/CSV + textos libres; avisos de faltantes |
| 3. Renderizado | 🔁 Cambiar de motor | WeasyPrint (PDF/A, paginación real); HTML con Jinja2 (escape automático) |
| 4. Generador | ✅ Posponerlo es correcto | Apoyarse en JSON Schema / validate / data-template / preview |
| Integración | Simplificada | Una CLI en Docker para todo; la API queda aplazada |
| Temas | Uno por departamento | `elausa_lab` y `elausa_cyber`; cada base indica el suyo |
| Dependencias | Solo las que reducen código propio y bugs | WeasyPrint, Pydantic, Jinja2, openpyxl, matplotlib |
| `generar_informe.py` | Referencia temporal | Portarlo a JSON en la fase 5 y eliminarlo |

**Mayor riesgo:** que el PDF/A de WeasyPrint no valide en veraPDF con las fuentes y las imágenes reales. Por eso se comprueba primero (fase 0).
