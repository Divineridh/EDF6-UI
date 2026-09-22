# EDF6 UI Mod

Herramientas propias para leer y modificar la UI de Earth Defense Force 6 sin depender de binarios de terceros.

Juego: `C:\Descargas Pesadas\EARTH DEFENSE FORCE 6\EARTH DEFENSE FORCE 6`
Loader ya instalado: EDFModLoader v1.0.10 (`winmm.dll`, `Redirect=True`).

## Cómo se arma la UI

`MAINSCRIPT.AS` (AngelScript) maneja el flujo de pantallas. La rutina `HQMain()` carga la base:

```
g_bg.Play("app:/ui/lyt_bg.sgo");
g_main_frame.Play("app:/ui/lyt_MainFrame.sgo");
CreateUiFile("app:/ui/lyt_HUiHQMain.sgo");
```

Cada pantalla es un `.sgo` dentro de `Root.cpk` (carpeta `UI/`, 467 layouts). El `.sgo` es la
declaración de la pantalla; los `.rab` que lo acompañan son el arte. El último string del layout
(`HUiHQWeaponSelect`) es el nombre de la clase C++ dentro de `EDF.dll` que le da comportamiento.

Pantalla de equipamiento: `UI/LYT_HUIHQWEAPONSELECT.SGO`.

## Formato SGO (reverse engineering propio)

Cabecera de 0x20 bytes:

| offset | contenido |
|--------|-----------|
| 0x00 | `SGO\0` |
| 0x04 | versión (0x102) |
| 0x08 | cantidad de registros raíz |
| 0x0C | offset de la tabla de registros |
| 0x10 / 0x14 | cantidad / offset del índice de nombres |
| 0x1C | base de la tabla de strings (UTF-16LE, terminados en `\0\0`) |

Todo el archivo es un árbol de registros de 12 bytes: `(tipo u32, cantidad u32, valor u32)`.

| tipo | significado | valor |
|------|-------------|-------|
| 0 | array | offset **relativo al propio registro**; `cantidad` = hijos |
| 1 | int | inline |
| 2 | float | inline |
| 3 | string | offset relativo al registro, apunta a UTF-16LE |

Un widget es un array con esta forma:

```
[clase, skin, pos[x,y,z], area[x,y,w,h], flags[], int, int, props[[clave,valor],...]]
```

El espacio de coordenadas es 1920x1080 fijo. Solo existen 4 clases de widget:
`Layout`, `TextField`, `Button`, `TexButtonTextField`.

Propiedades que acepta el layout (vocabulario completo, sacado de los 467 archivos):
`pos`, `area`, `mergin`, `stencil`, `stencil_mergin`, `scroll_bar_info`, `scroll_mergin`,
`font_size`, `font_flag`, `font_border_width`, `font_color`, `font_border_color`, `text`,
`text_dr`, `callback`, `trans_form`, `animation_sec`, `ease_func`, `close_scale`, `hide`,
`transition`, `transition_dir`, `sgo_path`, `init_args`, `hcoord`, `flag_layout`.

No hay ninguna propiedad de cantidad de celdas, filas ni columnas.

## Formato DSGO (el hermano de 64 bits)

Los datos del juego — catálogo de armas, textos, manual — no son SGO sino **DSGO**. Mismo árbol, pero
todo el archivo es una **lista plana de registros de 16 bytes**; el anidamiento se hace por índice, no
por offset.

Cabecera de 0x10 bytes:

| offset | contenido |
|--------|-----------|
| 0x00 | `DSGO` |
| 0x04 | 0x10 (tamaño de registro) |
| 0x08 | cantidad de registros |
| 0x0C | offset del primer registro (0x10) |

Cada registro es `(valor u64, tipo u32, 0 u32)`:

| tipo | significado | dónde está el dato |
|------|-------------|--------------------|
| 0 | **double** | los 8 bytes del `valor` son el IEEE754 |
| 1 | **string** | UTF-16LE en `offset_del_registro + valor` |
| 2 | int | inline en `valor` |
| 3 | **array** | descriptor en `offset_del_registro + valor` |

El descriptor de array son 16 bytes `(u64 0, u32 0x10, u32 cantidad)` seguidos de `cantidad` **índices
u32 a la tabla de registros**. Por eso un mismo registro puede colgar de dos arrays: el formato comparte
nodos.

⚠️ Los offsets de string y de array son **relativos al registro que los declara**, igual que en el SGO
de 32 bits. Tomarlos como absolutos parsea casi todo bien y devuelve strings cortados por la mitad — que
es el síntoma de que la base está mal, no de que el archivo esté raro.

```bash
python tools/dsgo.py <archivo> json    # árbol completo
python tools/dsgo.py <archivo> 1       # sólo el registro 1
```

## Catálogo de armas

`WEAPON/WEAPONTABLE.SGO` y `WEAPON/WEAPONTEXT.<lang>.SGO` son DSGO y **el registro 1 de cada uno es la
lista maestra, con 1564 entradas en el mismo orden**.

Una entrada de la tabla: `[id interno, path del sgo, categoría, 1.0, nivel/100, ?, [ratings], 1.0, ?]`.
La categoría codifica la clase en las centenas — `0xx` Ranger, `1xx` Wing Diver, `2xx` Fencer,
`3xx` Air Raider — y la unidad es el tipo de arma dentro de la clase.

Una entrada del texto: `[nombre, descripción, [stats]]`, y cada stat es
`[etiqueta, plantilla, valores...]` donde la plantilla usa `$0`, `$1`… y cada valor es un array de 7
doubles cuyo **primer elemento es el número** (el resto son parámetros de formato).

```bash
python tools/weapons.py                # -> build/catalog.json y build/catalog.csv
```

⚠️ El nivel sale de multiplicar por 100 el quinto campo. Da valores razonables (0 a 470) pero **no está
verificado contra la pantalla del juego**, y los ítems de colaboración caen en decimales (32.03), así
que puede ser el orden de dropeo y no el "Lv" que se muestra.

## Manual electrónico

> El compendium llegó a inyectarse acá como un capítulo extra (`tools/compendium.py`, borrado en
> sep-2026). Esa vía quedó descartada a favor del overlay del plugin en `EDF6-Compendium`: el
> capítulo era estático, entraba una sola clase por página, pisaba una página real del manual, se
> indexaba por nombre —y hay armas con nombre repetido— y sólo se abría desde el menú de pausa.
> Nunca llegó a instalarse en el juego. Lo que sigue es la documentación del formato, que sigue
> valiendo: la técnica de re-apuntar strings al final del archivo es la que usa `weapon_notes.py`.

`ETC/EMANUAL.EN.DSGO` es el manual, y es un documento rich-text data-driven:

- 5 arrays de **67 páginas** cada uno (registros 1, 986, 1551, 2116 y 2681), que comparten casi todas
  las páginas entre sí.
- Una página es `['', [bloques]]`; un bloque de texto es `[0.0, "markup"]` y uno de imagen es
  `[1.0, "archivo.dds", 1.0]`.
- El markup es real: `<font color=%dq%#c0ffc0%dq%>…</font>`, donde `%dq%` escapa la comilla doble.
  `%LOCALE%` en el nombre de una imagen se resuelve por idioma.
- Lo lee la clase `HUiManual` de `EDF.dll` con el layout `UI/LYT_MANUAL.SGO`.

Es accesible en el juego: el texttable trae `OptionPlayer_CallManual` → "Read Instruction Manual" y
"Instruction Manual Available During Gameplay", o sea que se abre desde el menú de pausa.

## Herramientas

```bash
python tools/cpk.py dirs    "<Root.cpk>"                      # inventario del archivo
python tools/cpk.py list    "<Root.cpk>" ui/                  # listar por patrón
python tools/cpk.py extract "<Root.cpk>" "ui/&.sgo" <destino> # extraer (patrones con &)
python tools/sgo.py <archivo.sgo> json                        # layout completo a JSON
python tools/patch.py <archivo.sgo> slots 36.                 # slots editables de un nodo
python tools/patch.py <origen.sgo> set 36.3.3=401 <destino.sgo>
python tools/dsgo.py <archivo.dsgo> json                      # datos (armas, textos, manual)
python tools/weapons.py                                       # catálogo de armas a JSON/CSV
```

`patch.py` reescribe los valores **en el mismo lugar del binario**: el archivo mantiene tamaño y
estructura idénticos, así que no hace falta reserializar ni hay riesgo de corromper offsets.

## Mapa de LYT_HUIHQWEAPONSELECT.SGO

51 registros raíz. Los relevantes:

| nodo | qué es | pos | area |
|------|--------|-----|------|
| 40 | WindowUpper — marco de la lista | 191, 147 | 1187 x 302 |
| 26 | WeaponIndexArea — fila de categorías | 18, 23 | 1162 x 39 |
| 36 | WeaponSelectArea — viewport de la grilla | 18, 67 | 1162 x 201 |
| 34 | celda de arma (plantilla) | — | 355 x 40 |
| 35 | celda de categoría (plantilla) | — | 355 x 39 |
| 39 | WindowLower — panel de descripción | 256, 468 | 1130 x 498 |
| 23 | área scrolleable de la descripción | 38, 89 | 1050 x 364 |
| 21 | columna de la lista con su scrollbar | — | 355 x 201 |

201 / 40 = 5 filas, 1162 / 355 = 3 columnas → 15 armas visibles.

## Límites

Se puede tocar por layout: geometría, tipografía, márgenes, skins, scroll, animaciones y textos.

No está en el layout: cuántas celdas se instancian, la paginación y el armado de la grilla. Eso vive
en `HUiHQWeaponSelect` dentro de `EDF.dll`. Si la cantidad de filas no se deriva del `area`, ampliar
la grilla exige parche AOB (formato `Mods\Patches\*.txt`) o un plugin C++ con MinHook.

## Reconstruir el mod

```bash
python tools/gen_layout.py    # los tres layouts, desde extract/UI/
python tools/weapons.py       # catalogo de armas
python tools/weapon_notes.py  # notas al principio de la descripcion
python tools/paquete.py       # zip en ../builds/
```

`gen_layout.py` tiene la lista completa de valores editados por nodo, y reproduce los tres archivos
byte por byte. Es la fuente del rediseño: `build/` es salida y no está versionado.

## Instalar un build

```bash
cp -r "C:/ModsCaseros/EDF6-UI/build/UI" "C:/Descargas Pesadas/EARTH DEFENSE FORCE 6/EARTH DEFENSE FORCE 6/Mods/"
```

Para revertir, borrar el archivo de `Mods\UI\`. El `Root.cpk` nunca se toca.
