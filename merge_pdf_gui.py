#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MERGE PDF GUI
Herramienta con interfaz gráfica para unir varios PDF en uno solo, en el
orden que elijas (puedes subir, bajar y quitar archivos de la lista).

Lee:     los PDF que agregues (uno a uno o una carpeta completa).
Genera:  un PDF unido en la carpeta del primer archivo de la lista,
         con nombre PDFs_unidos_AAAAMMDD_HHMMSS.pdf (editable).
         Si ocurre un error, el detalle técnico queda en merge_pdf_gui.log.

Requiere: py -m pip install -r requirements.txt   (pypdf)

Uso:
  py merge_pdf_gui.py
  py merge_pdf_gui.py "C:\\Docs\\parte1.pdf" "C:\\Docs\\parte2.pdf"
  py merge_pdf_gui.py --help
"""

import argparse
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("Falta la librería pypdf. Instálala con:\n  py -m pip install pypdf")
    sys.exit(1)

VERSION = "1.0.0"
NOMBRE_APP = "Merge PDF"

if getattr(sys, "frozen", False):  # empaquetado como .exe con PyInstaller
    CARPETA_APP = Path(sys.executable).parent
else:
    CARPETA_APP = Path(__file__).parent
RUTA_LOG = CARPETA_APP / "merge_pdf_gui.log"

# delay=True: el .log solo se crea si de verdad ocurre un error.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(RUTA_LOG, encoding="utf-8", delay=True)],
)
log = logging.getLogger("merge_pdf")

# ─── Paleta de colores ───
COLOR_AZUL = "#033E84"
COLOR_ROJO = "#D84141"
COLOR_GRIS = "#666666"
COLOR_FONDO_AZUL = "#E9F5FF"
COLOR_FONDO_BLANCO = "#FFFFFF"
COLOR_AZUL_OSCURO = "#022B5C"

FUENTES_PREFERIDAS = ("Source Sans 3", "Segoe UI")
FONT_PRIMARY = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SMALL = ("Segoe UI", 9)

TEXTO_AYUDA = """\
Cómo usar Merge PDF

1. Agrega los PDF con "+ Agregar PDFs" o "+ Agregar carpeta".
2. Ordénalos con "Subir" y "Bajar". El PDF final respeta ese orden.
3. Revisa el nombre del archivo de salida (se puede editar).
4. Presiona "Unir PDFs".

El resultado se guarda en la carpeta del primer PDF de la lista.
Los PDF protegidos con contraseña se saltan y se informan en el registro.
"""


# ─── Línea de comandos ───
class FormateadorAyuda(argparse.RawDescriptionHelpFormatter):
    """Formateador de argparse con el encabezado 'uso:' en español."""

    def add_usage(self, usage, actions, groups, prefix=None):
        return super().add_usage(usage, actions, groups, prefix if prefix is not None else "uso: ")


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="merge_pdf_gui.py",
        description="Une varios PDF en uno solo mediante una ventana gráfica.",
        epilog=(
            "Ejemplos:\n"
            "  py merge_pdf_gui.py\n"
            "      abre la ventana vacía\n"
            '  py merge_pdf_gui.py "C:\\Docs\\parte1.pdf" "C:\\Docs\\parte2.pdf"\n'
            "      abre la ventana con esos PDF ya cargados, en ese orden\n"
            "  py merge_pdf_gui.py --version\n"
            "      muestra la versión instalada"
        ),
        formatter_class=FormateadorAyuda,
        add_help=False,
    )
    parser._positionals.title = "argumentos posicionales"
    parser._optionals.title = "opciones"
    parser.add_argument("pdfs", nargs="*", type=Path,
                        help="PDF a cargar en la lista al abrir (opcional, por defecto ninguno)")
    parser.add_argument("-h", "--help", action="help", help="muestra esta ayuda y termina")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}",
                        help="muestra la versión y termina")
    return parser


def configurar_fuentes(raiz: tk.Tk) -> None:
    """Usa la primera fuente preferida instalada en el equipo."""
    global FONT_PRIMARY, FONT_BOLD, FONT_TITLE, FONT_SMALL
    instaladas = set(tkfont.families(raiz))
    familia = next((f for f in FUENTES_PREFERIDAS if f in instaladas), "Segoe UI")
    FONT_PRIMARY = (familia, 11)
    FONT_BOLD = (familia, 11, "bold")
    FONT_TITLE = (familia, 16, "bold")
    FONT_SMALL = (familia, 9)


# ─── Motor Merge PDF ───
class PDFMerger:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def merge_pdfs(self, pdf_files: List[str], output_path: str,
                   skip_encrypted: bool = True,
                   progress_cb=None) -> Tuple[str, int, List[Tuple[str, str]]]:
        """
        Une los PDFs en el orden dado.

        Returns:
            (output_path, archivos_unidos, [(nombre, razon_skip), ...])
        """
        writer = PdfWriter()
        added = 0
        skipped: List[Tuple[str, str]] = []

        for idx, pdf_path in enumerate(pdf_files):
            if self.cancelled:
                break

            name = os.path.basename(pdf_path)
            if progress_cb:
                progress_cb(idx, len(pdf_files), f"Procesando: {name}")

            try:
                reader = PdfReader(pdf_path)
                if reader.is_encrypted:
                    if skip_encrypted:
                        skipped.append((name, "protegido con contraseña"))
                        continue
                    reader.decrypt("")

                for page in reader.pages:
                    writer.add_page(page)
                added += 1

            except Exception as e:
                # Un PDF dañado no debe detener la unión del resto: se informa y se sigue.
                log.exception("No se pudo leer %s", pdf_path)
                skipped.append((name, str(e)))

        if self.cancelled:
            return output_path, added, skipped

        if added == 0:
            raise RuntimeError("No se pudo añadir ningún PDF.")

        writer.add_metadata({
            "/Title": "PDFs unidos",
            "/Producer": f"{NOMBRE_APP} {VERSION}"
        })

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)

        if progress_cb:
            progress_cb(len(pdf_files), len(pdf_files), "¡Listo!")

        return output_path, added, skipped


# ─── GUI ───
class MergePDFApp(tk.Tk):
    def __init__(self, pdfs_iniciales: List[Path] | None = None):
        super().__init__()
        configurar_fuentes(self)
        self.title(f"{NOMBRE_APP} {VERSION}")
        self.geometry("660x700")
        self.configure(bg=COLOR_FONDO_BLANCO)
        self.resizable(False, False)

        self.merger = PDFMerger()
        self.pdf_list: List[str] = []
        self.output_path = None
        self.running = False

        self._build_menu()
        self._build_ui()

        for pdf in pdfs_iniciales or []:
            if pdf.is_file() and pdf.suffix.lower() == ".pdf":
                self.pdf_list.append(str(pdf.resolve()))
        if self.pdf_list:
            self._refresh_listbox()

    # ── Menú ──
    def _build_menu(self):
        menubar = tk.Menu(self)
        menu_ayuda = tk.Menu(menubar, tearoff=0)
        menu_ayuda.add_command(label="Cómo usar", command=self._mostrar_ayuda)
        menu_ayuda.add_command(label="Acerca de", command=self._mostrar_acerca_de)
        menubar.add_cascade(label="Ayuda", menu=menu_ayuda)
        self.config(menu=menubar)

    def _mostrar_ayuda(self):
        messagebox.showinfo("Ayuda", TEXTO_AYUDA)

    def _mostrar_acerca_de(self):
        messagebox.showinfo("Acerca de",
                            f"{NOMBRE_APP} {VERSION}\n\nUne varios PDF en uno solo.\n"
                            "Licencia MIT.")

    # ── Franja degradada ──
    def _draw_gradient_bar(self, parent):
        canvas = tk.Canvas(parent, height=4, bg=COLOR_FONDO_BLANCO, highlightthickness=0)
        canvas.pack(fill="x", padx=30, pady=(18, 8))
        canvas.update_idletasks()
        w = canvas.winfo_width() or 600
        for i in range(w):
            r_ratio = i / w
            r = int(3 + (216 - 3) * r_ratio)
            g = int(62 + (65 - 62) * r_ratio)
            b = int(132 + (65 - 132) * r_ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            canvas.create_line(i, 0, i, 4, fill=color)

    # ── Build UI ──
    def _build_ui(self):
        self._draw_gradient_bar(self)

        title = tk.Label(self, text="Unir PDFs", font=FONT_TITLE, fg=COLOR_AZUL, bg=COLOR_FONDO_BLANCO)
        title.pack(pady=(0, 10))

        main = tk.Frame(self, bg=COLOR_FONDO_BLANCO, padx=30)
        main.pack(fill="both", expand=True)

        # ── Botones agregar / quitar ──
        self._section(main, "Archivos PDF a unir")

        btn_row = tk.Frame(main, bg=COLOR_FONDO_BLANCO)
        btn_row.pack(fill="x", pady=(0, 6))

        btn_add = tk.Button(btn_row, text="+ Agregar PDFs", font=FONT_BOLD,
                            bg=COLOR_AZUL, fg="white", activebackground=COLOR_AZUL_OSCURO,
                            activeforeground="white", bd=0, padx=14, pady=4,
                            cursor="hand2", command=self._add_files)
        btn_add.pack(side="left")

        btn_add_folder = tk.Button(btn_row, text="+ Agregar carpeta", font=FONT_PRIMARY,
                                   bg=COLOR_AZUL, fg="white", activebackground=COLOR_AZUL_OSCURO,
                                   activeforeground="white", bd=0, padx=14, pady=4,
                                   cursor="hand2", command=self._add_folder)
        btn_add_folder.pack(side="left", padx=(8, 0))

        btn_clear = tk.Button(btn_row, text="Limpiar lista", font=FONT_PRIMARY,
                              bg=COLOR_GRIS, fg="white", activebackground="#555555",
                              activeforeground="white", bd=0, padx=14, pady=4,
                              cursor="hand2", command=self._clear_list)
        btn_clear.pack(side="right")

        # ── Listbox con scrollbar ──
        list_frame = tk.Frame(main, bg=COLOR_FONDO_BLANCO)
        list_frame.pack(fill="both", expand=True, pady=(0, 6))

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(list_frame, font=FONT_SMALL, bg=COLOR_FONDO_AZUL,
                                  fg=COLOR_GRIS, selectbackground=COLOR_AZUL,
                                  selectforeground="white", bd=1, relief="solid",
                                  height=10, yscrollcommand=scrollbar.set,
                                  selectmode="extended")
        self.listbox.pack(fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        # ── Botones ordenar / quitar selección ──
        order_row = tk.Frame(main, bg=COLOR_FONDO_BLANCO)
        order_row.pack(fill="x", pady=(0, 8))

        btn_up = tk.Button(order_row, text="▲ Subir", font=FONT_SMALL,
                           bg=COLOR_FONDO_AZUL, fg=COLOR_AZUL, bd=1, padx=8, pady=2,
                           cursor="hand2", command=self._move_up)
        btn_up.pack(side="left")

        btn_down = tk.Button(order_row, text="▼ Bajar", font=FONT_SMALL,
                             bg=COLOR_FONDO_AZUL, fg=COLOR_AZUL, bd=1, padx=8, pady=2,
                             cursor="hand2", command=self._move_down)
        btn_down.pack(side="left", padx=(4, 0))

        btn_remove = tk.Button(order_row, text="✕ Quitar selección", font=FONT_SMALL,
                               bg=COLOR_FONDO_AZUL, fg=COLOR_ROJO, bd=1, padx=8, pady=2,
                               cursor="hand2", command=self._remove_selected)
        btn_remove.pack(side="left", padx=(4, 0))

        self.count_label = tk.Label(order_row, text="0 archivos", font=FONT_SMALL,
                                    fg=COLOR_GRIS, bg=COLOR_FONDO_BLANCO)
        self.count_label.pack(side="right")

        # ── Nombre de salida ──
        self._section(main, "Archivo de salida")

        out_frame = tk.Frame(main, bg=COLOR_FONDO_BLANCO)
        out_frame.pack(fill="x", pady=(0, 8))

        tk.Label(out_frame, text="Se guarda en la carpeta del primer PDF. Nombre:",
                 font=FONT_SMALL, fg=COLOR_GRIS, bg=COLOR_FONDO_BLANCO).pack(anchor="w")

        self.output_name_var = tk.StringVar(value="")
        self.entry_output = tk.Entry(out_frame, textvariable=self.output_name_var,
                                     font=FONT_PRIMARY, bg=COLOR_FONDO_AZUL, width=40)
        self.entry_output.pack(fill="x", pady=(2, 0), ipady=3)

        # ── Barra progreso ──
        self.progress_label = tk.Label(main, text="", font=FONT_SMALL,
                                       fg=COLOR_GRIS, bg=COLOR_FONDO_BLANCO)
        self.progress_label.pack(fill="x", pady=(6, 2))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("App.Horizontal.TProgressbar",
                        troughcolor=COLOR_FONDO_AZUL, background=COLOR_AZUL, thickness=18)
        self.progress = ttk.Progressbar(main, style="App.Horizontal.TProgressbar",
                                        mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 8))

        # ── Botones acción ──
        action_row = tk.Frame(main, bg=COLOR_FONDO_BLANCO)
        action_row.pack(fill="x", pady=(2, 6))

        self.btn_merge = tk.Button(action_row, text="  Unir PDFs  ", font=FONT_BOLD,
                                   bg=COLOR_ROJO, fg="white", activebackground="#b83030",
                                   activeforeground="white", bd=0, padx=24, pady=8,
                                   cursor="hand2", command=self._run_merge)
        self.btn_merge.pack(side="left")

        self.btn_open_folder = tk.Button(action_row, text="Abrir carpeta", font=FONT_PRIMARY,
                                         bg=COLOR_AZUL, fg="white",
                                         activebackground=COLOR_AZUL_OSCURO,
                                         activeforeground="white", bd=0, padx=16, pady=8,
                                         cursor="hand2", state="disabled",
                                         command=self._open_output_folder)
        self.btn_open_folder.pack(side="right")

        # ── Log ──
        self.log_text = tk.Text(main, height=4, font=FONT_SMALL, bg=COLOR_FONDO_AZUL,
                                fg=COLOR_GRIS, bd=1, relief="solid", state="disabled",
                                wrap="word")
        self.log_text.pack(fill="x", pady=(4, 12))

        self._update_default_output_name()

    # ── Helpers ──
    def _section(self, parent, text):
        lbl = tk.Label(parent, text=text, font=FONT_BOLD, fg=COLOR_AZUL,
                       bg=COLOR_FONDO_BLANCO, anchor="w")
        lbl.pack(fill="x", pady=(6, 2))

    def _refresh_listbox(self):
        self.listbox.delete(0, "end")
        for idx, path in enumerate(self.pdf_list, 1):
            name = os.path.basename(path)
            size = os.path.getsize(path) / (1024 * 1024)
            self.listbox.insert("end", f" {idx}. {name}  ({size:.1f} MB)")
        self.count_label.config(text=f"{len(self.pdf_list)} archivo{'s' if len(self.pdf_list) != 1 else ''}")
        self._update_default_output_name()

    def _update_default_output_name(self):
        if not self.output_name_var.get().strip() or self.output_name_var.get().startswith("PDFs_unidos_"):
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_name_var.set(f"PDFs_unidos_{stamp}.pdf")

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Seleccionar PDFs",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")]
        )
        if paths:
            for p in paths:
                if p not in self.pdf_list:
                    self.pdf_list.append(p)
            self._refresh_listbox()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta con PDFs")
        if folder:
            pdfs = sorted(
                [str(p) for p in Path(folder).iterdir() if p.suffix.lower() == ".pdf"],
                key=lambda x: os.path.basename(x).lower()
            )
            for p in pdfs:
                if p not in self.pdf_list:
                    self.pdf_list.append(p)
            self._refresh_listbox()

    def _clear_list(self):
        self.pdf_list.clear()
        self._refresh_listbox()

    def _remove_selected(self):
        selected = list(self.listbox.curselection())
        for idx in reversed(selected):
            self.pdf_list.pop(idx)
        self._refresh_listbox()

    def _move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.pdf_list[i - 1], self.pdf_list[i] = self.pdf_list[i], self.pdf_list[i - 1]
        self._refresh_listbox()
        self.listbox.selection_set(i - 1)

    def _move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.pdf_list) - 1:
            return
        i = sel[0]
        self.pdf_list[i + 1], self.pdf_list[i] = self.pdf_list[i], self.pdf_list[i + 1]
        self._refresh_listbox()
        self.listbox.selection_set(i + 1)

    def _log(self, msg: str):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _update_progress(self, current, total, msg=""):
        if total > 0:
            pct = int(current / total * 100)
            self.progress["value"] = pct
        self.progress_label.config(text=msg)
        self.update_idletasks()

    def _open_output_folder(self):
        if self.output_path:
            folder = os.path.dirname(self.output_path)
            if os.path.isdir(folder):
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    os.system(f'open "{folder}"')
                else:
                    os.system(f'xdg-open "{folder}"')

    # ── Ejecutar merge ──
    def _run_merge(self):
        if self.running:
            return

        if len(self.pdf_list) < 2:
            messagebox.showwarning("Pocos archivos", "Agrega al menos 2 PDFs para unir.")
            return

        out_name = self.output_name_var.get().strip()
        if not out_name:
            out_name = f"PDFs_unidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        if not out_name.lower().endswith(".pdf"):
            out_name += ".pdf"

        # Guardar en la carpeta del primer PDF
        out_dir = os.path.dirname(self.pdf_list[0])
        out_full = os.path.join(out_dir, out_name)

        if os.path.isfile(out_full):
            if not messagebox.askyesno("Archivo existe",
                                       f"{out_name} ya existe.\n¿Sobrescribir?"):
                return

        self.running = True
        self.btn_merge.config(state="disabled", text="  Procesando...  ")
        self.btn_open_folder.config(state="disabled")
        self._clear_log()
        self.progress["value"] = 0

        self.merger = PDFMerger()

        def worker():
            try:
                def progress_cb(cur, tot, msg):
                    self.after(0, self._update_progress, cur, tot, msg)

                result_path, added, skipped = self.merger.merge_pdfs(
                    pdf_files=self.pdf_list,
                    output_path=out_full,
                    skip_encrypted=True,
                    progress_cb=progress_cb
                )

                self.output_path = result_path

                def on_done():
                    self.progress["value"] = 100
                    self.progress_label.config(text="¡Listo!")
                    sz = os.path.getsize(result_path) / (1024 * 1024)
                    self._log(f"✅ {added} PDFs unidos exitosamente")
                    self._log(f"📄 {os.path.basename(result_path)}  ({sz:.2f} MB)")
                    self._log(f"📁 {os.path.dirname(result_path)}")
                    if skipped:
                        for name, reason in skipped:
                            self._log(f"⚠️ Saltado: {name} ({reason})")
                    self.btn_merge.config(state="normal", text="  Unir PDFs  ")
                    self.btn_open_folder.config(state="normal")
                    self.running = False

                self.after(0, on_done)

            except Exception as e:
                log.exception("Error al unir los PDF")

                def on_error():
                    self._log(f"❌ Error: {e}")
                    self._log(f"Detalle técnico en: {RUTA_LOG}")
                    self.progress_label.config(text="Error")
                    self.btn_merge.config(state="normal", text="  Unir PDFs  ")
                    self.running = False
                self.after(0, on_error)

        threading.Thread(target=worker, daemon=True).start()


def main() -> int:
    args = crear_parser().parse_args()
    app = MergePDFApp(args.pdfs)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
