# Merge PDF

Herramienta de escritorio para **unir varios PDF en uno solo**, en el orden que elijas. Tiene ventana gráfica: agregas archivos (o una carpeta completa), los ordenas con Subir/Bajar y presionas *Unir PDFs*.

## Instalación (Windows, cmd)

```bat
git clone https://github.com/laguileg/merge_pdf.git
cd merge_pdf
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```

## Uso

```bat
py merge_pdf_gui.py
py merge_pdf_gui.py "C:\Docs\parte1.pdf" "C:\Docs\parte2.pdf"
py merge_pdf_gui.py --help
```

Sin argumentos abre la ventana vacía; con rutas de PDF, los deja cargados en la lista en ese orden. Dentro de la ventana, el menú **Ayuda → Cómo usar** explica los pasos.

| Opción | Qué hace |
|---|---|
| `pdfs` | PDF a cargar al abrir (opcional) |
| `-h`, `--help` | Muestra la ayuda |
| `--version` | Muestra la versión |

## Diseño

La ventana usa el sistema de marca **Luciano Aguilera · Prisma Sol**: encabezado violeta con el logo, línea de acento sol, títulos en **Urbanist** y texto en **Inter**.

- Las fuentes son gratuitas en [Google Fonts](https://fonts.google.com/): instala [Urbanist](https://fonts.google.com/specimen/Urbanist) e [Inter](https://fonts.google.com/specimen/Inter) en Windows para verla tal cual. Si no están, usa Century Gothic y Segoe UI.
- El logo y el ícono están en la carpeta `assets/`. Si falta, la herramienta funciona igual, sin logo.

## Archivos que genera

- `PDFs_unidos_AAAAMMDD_HHMMSS.pdf` (nombre editable) en la carpeta del **primer** PDF de la lista.
- `merge_pdf_gui.log` junto al script, **solo si ocurre un error**, con el detalle técnico.

## Problemas conocidos

- **Los PDF con contraseña se saltan**: aparecen como "Saltado" en el registro de la ventana. Quítales la contraseña primero.
- **Un PDF dañado no detiene el proceso**: se salta, se informa y se unen los demás.

## Crear un .exe (opcional)

```bat
py -m pip install pyinstaller
pyinstaller --onefile --windowed --name merge_pdf --icon assets\isotipo-app.ico --add-data "assets;assets" merge_pdf_gui.py
```

El ejecutable queda en `dist\merge_pdf.exe`.

## Licencia

[MIT](LICENSE): puedes usar, modificar y compartir este código libremente, manteniendo el aviso de autoría.

La licencia cubre el código. El logo y los elementos de la marca Prisma Sol (`assets/`) son de Luciano Aguilera y no están incluidos: ver [assets/MARCA.md](assets/MARCA.md).

## Historial

| Fecha | Versión | Cambios |
|---|---|---|
| 2026-11-19 | 1.1.0 | Nuevo diseño con el sistema de marca Prisma Sol: encabezado violeta con logo, línea sol, Urbanist + Inter, botones y campos con la nueva paleta, ícono de ventana. Sin cambios de funcionamiento. |
| 2026-11-11 | 1.0.0 | Primera versión pública: ayuda en español (`--help`, menú Ayuda), `--version`, PDF iniciales por línea de comandos y registro de errores en `.log`. |
