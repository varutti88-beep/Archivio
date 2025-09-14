import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageTk
import shutil
import tempfile
import zipfile
import sqlite3
import subprocess
import sys
import platform
from pathlib import Path
import webbrowser
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import ttk


# ============================================================
# Costanti per colori e font
# ============================================================
BG_COLOR = "white"
MENU_BG = "#002fff"
MENU_BTN_BG = "#03cbea"
MENU_BTN_ACTIVE = "#0a84d5"
FG_COLOR = "white"
FONT_NORMAL = ("Segoe UI", 12)
FONT_BOLD = ("Segoe UI", 15, "bold")

# File JSON per salvataggio dati
FILE_CLIENTI = "clienti.json"
FILE_CONSEGNE = "consegne.json"
FILE_PRODOTTI = "prodotti.json"
FILE_NOTE = "note.json"
FILE_STOCCAGGIO = "stoccaggio.json"
FILE_BACKUP = "backup.zip"
FILE_FATTURE = "fatture.json"
FILE_PRODUZIONE = "produzione.json"

def set_style(root):
    style = ttk.Style(root)

    # Usa un tema di base
    style.theme_use("clam")

    # Stile generico per i frame
    style.configure("TFrame", background=BG_COLOR)

    # Stile generico per le label
    style.configure("TLabel", background=BG_COLOR, foreground="black", font=FONT_NORMAL)

    # Stile per i bottoni
    style.configure("TButton",
                    background=MENU_BTN_BG,
                    foreground="black",
                    font=FONT_NORMAL,
                    padding=6)
    style.map("TButton",
              background=[("active", MENU_BTN_ACTIVE)],
              foreground=[("active", "white")])

    # 🔹 Stile per le entry (qui eliminiamo lo sfondo bianco!)
    style.configure("TEntry",
                    fieldbackground=BG_COLOR,   # sfondo dentro la casella
                    background=BG_COLOR,        # bordo
                    foreground="black",         # colore testo
                    insertcolor="black")        # colore cursore

def bind_mousewheel(widget, target):
    """
    Permette di scorrere con la rotellina del mouse.
    widget = quello che riceve l'evento (es. frame o tree)
    target = la scrollbar o il widget scrollabile
    """
    def _on_mousewheel(event):
        if event.delta:  # Windows e Mac
            target.yview_scroll(int(-1*(event.delta/120)), "units")
        else:  # Linux (usa Button-4 e Button-5)
            if event.num == 4:
                target.yview_scroll(-1, "units")
            elif event.num == 5:
                target.yview_scroll(1, "units")

    # Associa eventi
    widget.bind_all("<MouseWheel>", _on_mousewheel)
    widget.bind_all("<Button-4>", _on_mousewheel)
    widget.bind_all("<Button-5>", _on_mousewheel)


class ArchivioFatture:
    def __init__(self, db_path="archivio_fatture.db", folder="documenti_fatture"):
        self.db_path = db_path
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self._crea_db()

    def _crea_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fatture (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_file TEXT NOT NULL,
                path TEXT NOT NULL,
                tipo TEXT,
                data_importazione TEXT
            )
        """)
        conn.commit()
        conn.close()

    def importa_documento(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError("File non trovato!")

        nome_file = os.path.basename(file_path)
        tipo = os.path.splitext(file_path)[1].lower()
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        destinazione = os.path.join(self.folder, nome_file)
        base, ext = os.path.splitext(destinazione)
        counter = 1
        while os.path.exists(destinazione):
            destinazione = f"{base}_{counter}{ext}"
            counter += 1

        shutil.copy2(file_path, destinazione)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO fatture (nome_file, path, tipo, data_importazione) VALUES (?, ?, ?, ?)",
                    (nome_file, destinazione, tipo, data))
        conn.commit()
        conn.close()

    def lista_documenti(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, nome_file, tipo, data_importazione FROM fatture")
        rows = cur.fetchall()
        conn.close()
        return rows

    def apri_documento(self, doc_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT path FROM fatture WHERE id=?", (doc_id,))
        row = cur.fetchone()
        conn.close()
        if row and os.path.exists(row[0]):
            if os.name == "nt":  # Windows
                os.startfile(row[0])
            elif sys.platform == "darwin":  # macOS
                subprocess.call(("open", row[0]))
            else:  # Linux
                subprocess.call(("xdg-open", row[0]))
        else:
            raise FileNotFoundError("Documento non trovato!")

    def elimina_documento(self, doc_id):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT path FROM fatture WHERE id=?", (doc_id,))
        row = cur.fetchone()
        if row and os.path.exists(row[0]):
            os.remove(row[0])  # elimina il file
        cur.execute("DELETE FROM fatture WHERE id=?", (doc_id,))
        conn.commit()
        conn.close()

class FattureFrame(ttk.Frame):
    def __init__(self, parent, archivio: ArchivioFatture, logger=None):
        super().__init__(parent)
        self.archivio = archivio
        self.logger = logger

        # Bottoni (importa / apri / elimina)
        frm_buttons = ttk.Frame(self)
        frm_buttons.pack(fill="x", pady=5)

        btn_importa = ttk.Button(frm_buttons, text="📂 Importa documento", command=self.importa_documento)
        btn_importa.pack(side="left", padx=5)

        btn_apri = ttk.Button(frm_buttons, text="🔍 Apri documento", command=self.apri_documento)
        btn_apri.pack(side="left", padx=5)

        btn_elimina = ttk.Button(frm_buttons, text="🗑️ Elimina documento", command=self.elimina_documento)
        btn_elimina.pack(side="left", padx=5)

        # Barra ricerca
        frm_search = ttk.Frame(self)
        frm_search.pack(fill="x", pady=5)
        ttk.Label(frm_search, text="🔎 Cerca:").pack(side="left", padx=5)
        self.var_search = tk.StringVar()
        ent_search = ttk.Entry(frm_search, textvariable=self.var_search)
        ent_search.pack(side="left", padx=5, fill="x", expand=True)
        ent_search.bind("<KeyRelease>", lambda e: self.refresh_tree())  # ricerca live

        # Tabella
        self.tree = ttk.Treeview(self, columns=("ID", "Nome File", "Tipo", "Data"), show="headings")
        for col in ("ID", "Nome File", "Tipo", "Data"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        self.tree.pack(expand=True, fill="both", padx=10, pady=10)

        self.refresh_tree()

    def refresh_tree(self):
        filtro = self.var_search.get().strip().lower() if hasattr(self, "var_search") else ""
        self.tree.delete(*self.tree.get_children())
        for row in self.archivio.lista_documenti():
            if not filtro or filtro in str(row[1]).lower() or filtro in str(row[2]).lower() or filtro in str(row[3]).lower():
                self.tree.insert("", "end", values=row)

    def importa_documento(self):
        path = filedialog.askopenfilename(title="Seleziona documento", filetypes=[("Tutti i file", "*.*")])
        if not path:
            return
        try:
            self.archivio.importa_documento(path)
            self.refresh_tree()
            if self.logger:
                self.logger.log(f"Documento importato: {path}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            if self.logger:
                self.logger.log(f"Errore importazione documento: {e}")

    def apri_documento(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona un documento prima di aprirlo.")
            return
        values = self.tree.item(selected[0])["values"]
        doc_id = values[0]
        try:
            self.archivio.apri_documento(doc_id)
            if self.logger:
                self.logger.log(f"Aperto documento ID {doc_id}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            if self.logger:
                self.logger.log(f"Errore apertura documento: {e}")

    def elimina_documento(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona un documento da eliminare.")
            return
        values = self.tree.item(selected[0])["values"]
        doc_id = values[0]
        nome_file = values[1]
        confirm = messagebox.askyesno("Conferma eliminazione", f"Vuoi eliminare '{nome_file}'?")
        if not confirm:
            return
        try:
            self.archivio.elimina_documento(doc_id)
            self.refresh_tree()
            if self.logger:
                self.logger.log(f"Eliminato documento ID {doc_id} ({nome_file})")
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            if self.logger:
                self.logger.log(f"Errore eliminazione documento: {e}")

class LoggerFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.text = tk.Text(self, height=8, state='disabled', bg="#f0f0f0", font=("Segoe UI", 10))
        self.text.pack(expand=True, fill="both")

    def log(self, msg):
        self.text.configure(state='normal')
        now = datetime.now().strftime("%H:%M:%S")
        self.text.insert(tk.END, f"[{now}] {msg}\n")
        self.text.see(tk.END)
        self.text.configure(state='disabled')


class BaseDataFrame(ttk.Frame):
    def __init__(self, parent, file_path, columns, logger=None):
        super().__init__(parent)
        self.file_path = file_path
        self.columns = columns
        self.logger = logger
        self.data = []
        self.filtered_data = []
        self.current_selection_index = None
        self._create_widgets()
        self.load_data()
        self.refresh_tree()

        # Bind doppio click -> apre Google Maps
        self.tree.bind("<Double-1>", self.on_double_click)

    # ==============================
    # Abilita scroll con la rotellina
    # ==============================
    def bind_mousewheel(self, widget, target):
        def _on_mousewheel(event):
            if event.delta:  # Windows/Mac
                target.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:  # Linux (Button-4 e Button-5)
                if event.num == 4:
                    target.yview_scroll(-1, "units")
                elif event.num == 5:
                    target.yview_scroll(1, "units")

        widget.bind_all("<MouseWheel>", _on_mousewheel)
        widget.bind_all("<Button-4>", _on_mousewheel)
        widget.bind_all("<Button-5>", _on_mousewheel)

    def on_double_click(self, event):
        item_id = self.tree.selection()
        if not item_id:
            return
        values = self.tree.item(item_id[0])["values"]

        # Trova la colonna "Comune e indirizzo"
        try:
            col_index = self.columns.index("Comune e indirizzo")
        except ValueError:
            return

        indirizzo = values[col_index]
        if indirizzo:
            url = f"https://www.google.com/maps/search/{indirizzo.replace(' ', '+')}"
            webbrowser.open(url)

    def _create_widgets(self):
        frm_form = ttk.Frame(self)
        frm_form.pack(fill="x", padx=10, pady=10)

        self.entries = {}
        for i, col in enumerate(self.columns):
            lbl = ttk.Label(frm_form, text=col + ":", font=FONT_NORMAL)
            lbl.grid(row=i, column=0, sticky="w", pady=4)
            ent = ttk.Entry(frm_form, font=FONT_NORMAL)
            ent.grid(row=i, column=1, sticky="ew", pady=4)
            if "descrizione" in col.lower():
                ent.config(font=("Segoe UI", 14))
            self.entries[col] = ent
        frm_form.columnconfigure(1, weight=1)

        frm_buttons = ttk.Frame(self)
        frm_buttons.pack(fill="x", padx=10, pady=5)

        self.btn_add = ttk.Button(frm_buttons, text="Aggiungi", command=self.add_record)
        self.btn_add.pack(side="left", padx=5)
        self.btn_edit = ttk.Button(frm_buttons, text="Modifica", command=self.edit_record)
        self.btn_edit.pack(side="left", padx=5)
        self.btn_delete = ttk.Button(frm_buttons, text="Elimina", command=self.delete_record)
        self.btn_delete.pack(side="left", padx=5)
        self.btn_clear = ttk.Button(frm_buttons, text="🧹 Pulisci campi", command=self.clear_entries)
        self.btn_clear.pack(side="left", padx=5)

        frm_import_export = ttk.Frame(self)
        frm_import_export.pack(fill="x", padx=10, pady=5)
        self.btn_import = ttk.Button(frm_import_export, text="Importa Excel", command=self.import_excel)
        self.btn_import.pack(side="right", padx=5)
        self.btn_export = ttk.Button(frm_import_export, text="Esporta Excel", command=self.export_excel)
        self.btn_export.pack(side="right", padx=5)

        frm_search = ttk.Frame(self)
        frm_search.pack(fill="x", padx=10, pady=5)

        lbl_search = ttk.Label(frm_search, text="Cerca:", font=FONT_NORMAL)
        lbl_search.pack(side="left")
        self.var_search = tk.StringVar()
        ent_search = ttk.Entry(frm_search, textvariable=self.var_search, font=FONT_NORMAL)
        ent_search.pack(side="left", fill="x", expand=True, padx=5)
        ent_search.bind("<KeyRelease>", lambda e: self.apply_filter())

        # ============================
        # Treeview + Scrollbar verticale
        # ============================
        tree_frame = ttk.Frame(self)
        tree_frame.pack(expand=True, fill="both", padx=10, pady=10)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.tree = ttk.Treeview(
            tree_frame, columns=self.columns, show="headings",
            selectmode="browse", yscrollcommand=scrollbar.set
        )
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w")

        self.tree.pack(side="left", expand=True, fill="both")
        scrollbar.config(command=self.tree.yview)

        # 🔹 Rotellina abilitata
        self.bind_mousewheel(self.tree, self.tree)

        # Label per Totale
        if self.file_path == FILE_PRODOTTI:
            self.lbl_totale_pagato = ttk.Label(self, text="Totale pagato: 0.00", font=FONT_BOLD)
            self.lbl_totale_pagato.pack(padx=10, pady=2, anchor="e")
        elif self.file_path == FILE_CONSEGNE:
            self.lbl_totale_riscosso = ttk.Label(self, text="Totale riscosso: 0.00", font=FONT_BOLD)
            self.lbl_totale_riscosso.pack(padx=10, pady=2, anchor="e")

    def load_data(self):
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            else:
                self.data = []
            if self.logger:
                self.logger.log(f"Dati caricati da {self.file_path} 📂")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare dati da {self.file_path}.\n{e}")
            self.data = []

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.apply_filter()

        # Aggiorna totale pagato per Prodotti
        if self.file_path == FILE_PRODOTTI and hasattr(self, "lbl_totale_pagato"):
            totale = 0.0
            for row in self.filtered_data:
                try:
                    totale += float(row.get("Prezzo", 0))
                except ValueError:
                    pass
            self.lbl_totale_pagato.config(text=f"Totale pagato: {totale:.2f}")

        # Aggiorna totale riscosso per Consegne
        if self.file_path == FILE_CONSEGNE and hasattr(self, "lbl_totale_riscosso"):
            totale = 0.0
            for row in self.filtered_data:
                try:
                    totale += float(row.get("Prezzo", 0))
                except ValueError:
                    pass
            self.lbl_totale_riscosso.config(text=f"Totale riscosso: {totale:.2f}")

    def apply_filter(self):
        search_term = self.var_search.get().lower()
        self.filtered_data = [r for r in self.data if search_term in json.dumps(r).lower()]
        self.tree.delete(*self.tree.get_children())
        for item in self.filtered_data:
            vals = [item.get(col, "") for col in self.columns]
            self.tree.insert("", "end", values=vals)

    def on_tree_select(self, _event):
        selected = self.tree.selection()
        if not selected:
            self.current_selection_index = None
            self.clear_entries()
            return
        item = self.tree.item(selected[0])
        values = item["values"]
        try:
            self.current_selection_index = self.data.index(self.filtered_data[self.tree.index(selected[0])])
        except Exception:
            self.current_selection_index = None
        for col, val in zip(self.columns, values):
            self.entries[col].delete(0, tk.END)
            self.entries[col].insert(0, val)

    def clear_entries(self):
        for ent in self.entries.values():
            ent.delete(0, tk.END)

    def get_entries_data(self):
        return {col: self.entries[col].get().strip() for col in self.columns}

    def add_record(self):
        new_record = self.get_entries_data()
        self.data.append(new_record)
        self.save_data()
        self.refresh_tree()
        self.clear_entries()
        if self.logger:
            self.logger.log("Record aggiunto. ➕")

    def edit_record(self):
        if self.current_selection_index is None:
            messagebox.showwarning("Attenzione", "Seleziona un record da modificare.")
            return
        new_data = self.get_entries_data()
        self.data[self.current_selection_index] = new_data
        self.save_data()
        self.refresh_tree()
        self.clear_entries()
        if self.logger:
            self.logger.log("Record modificato. ✏️")

    def delete_record(self):
        if self.current_selection_index is None:
            messagebox.showwarning("Attenzione", "Seleziona un record da eliminare.")
            return
        answer = messagebox.askyesno("Conferma", "Sei sicuro di voler eliminare il record selezionato?")
        if answer:
            del self.data[self.current_selection_index]
            self.save_data()
            self.refresh_tree()
            self.clear_entries()
            self.current_selection_index = None
            if self.logger:
                self.logger.log("Record eliminato. 🗑️")

    def save_data(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            if self.logger:
                self.logger.log(f"Dati salvati in {self.file_path} 💾")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare dati in {self.file_path}.\n{e}")

    def import_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if not path:
            return
        try:
            df = pd.read_excel(path)

            missing_cols = [col for col in self.columns if col not in df.columns]
            if missing_cols:
                messagebox.showwarning("Attenzione", f"Queste colonne mancano nel file Excel e saranno lasciate vuote: {', '.join(missing_cols)}")

            records = []
            for _, row in df.iterrows():
                record = {}
                for col in self.columns:
                    record[col] = str(row[col]) if col in df.columns else ""
                records.append(record)

            self.data = records
            self.save_data()
            self.refresh_tree()
            messagebox.showinfo("Importazione", "Dati importati correttamente.")
            if self.logger:
                self.logger.log(f"Dati importati da Excel: {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante importazione:\n{e}")

    def export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.DataFrame(self.data)
            for col in self.columns:
                if col not in df.columns:
                    df[col] = ""
            df = df[self.columns]
            df.to_excel(path, index=False)
            messagebox.showinfo("Esportazione", f"Dati esportati con successo in:\n{path}")
            if self.logger:
                self.logger.log(f"Dati esportati in Excel: {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante esportazione:\n{e}")


    def export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.DataFrame(self.data)
            for col in self.columns:
                if col not in df.columns:
                    df[col] = ""
            df = df[self.columns]
            df.to_excel(path, index=False)
            messagebox.showinfo("Esportazione", f"Dati esportati con successo in:\n{path}")
            if self.logger:
                self.logger.log(f"Dati esportati in Excel: {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante esportazione:\n{e}")


class NoteFrame(ttk.Frame):
    def __init__(self, parent, logger=None):
        super().__init__(parent)
        self.logger = logger
        self.file_path = FILE_NOTE
        self.text = tk.Text(self, font=FONT_NORMAL)
        self.text.pack(expand=True, fill="both", padx=10, pady=10)
        self.load_notes()
        btn_save = ttk.Button(self, text="Salva Note", command=self.save_notes)
        btn_save.pack(pady=5)

    def load_notes(self):
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.text.delete(1.0, tk.END)
                    self.text.insert(tk.END, content)
            if self.logger:
                self.logger.log("Note caricate. 🗒️")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare note.\n{e}")

    def save_notes(self):
        try:
            content = self.text.get(1.0, tk.END)
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(content)
            if self.logger:
                self.logger.log("Note salvate. 💾")
            messagebox.showinfo("Salvataggio", "Note salvate correttamente.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare note.\n{e}")

class StoccaggioFrame(BaseDataFrame):
    def __init__(self, parent, logger=None):
        columns = ["Descrizione", "Data Produzione", "Data Scadenza", "Lotto"]
        super().__init__(parent, FILE_STOCCAGGIO, columns, logger)

class BackupFrame(ttk.Frame):
    def __init__(self, parent, logger=None):
        super().__init__(parent)
        self.logger = logger

        lbl_info = ttk.Label(self, text="Backup dati archivio", font=FONT_BOLD)
        lbl_info.pack(pady=10)

        frm_buttons = ttk.Frame(self)
        frm_buttons.pack(pady=10)

        btn_backup = ttk.Button(frm_buttons, text="Crea Backup ZIP", command=self.create_backup)
        btn_backup.pack(side="left", padx=5)

        btn_import = ttk.Button(frm_buttons, text="Importa Backup ZIP", command=self.import_backup)
        btn_import.pack(side="left", padx=5)

        self.lbl_status = ttk.Label(self, text="", font=FONT_NORMAL)
        self.lbl_status.pack(pady=10)

    def create_backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP files", "*.zip")])
        if not path:
            return
        try:
            with zipfile.ZipFile(path, 'w') as backup_zip:
                for file in [FILE_CLIENTI, FILE_CONSEGNE, FILE_PRODOTTI, FILE_NOTE, FILE_STOCCAGGIO]:
                    if os.path.exists(file):
                        backup_zip.write(file)
            self.lbl_status.config(text=f"Backup creato: {path}")
            if self.logger:
                self.logger.log("Backup creato con successo. 🗃️")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile creare backup.\n{e}")

    def import_backup(self):
        path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not path:
            return
        try:
            with zipfile.ZipFile(path, 'r') as backup_zip:
                backup_zip.extractall()
            self.lbl_status.config(text=f"Backup importato da {path}")
            if self.logger:
                self.logger.log("Backup importato con successo. 📥")
            messagebox.showinfo("Importazione", "Backup importato correttamente.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile importare backup.\n{e}")
            

class EtichetteFrame(ttk.Frame):
    def __init__(self, parent, logger=None):
        super().__init__(parent)
        self.logger = logger

        self.fields = [
            "Descrizione Prodotto",
            "Data Produzione",
            "Data Scadenza",
            "Lotto",
            "Cliente"
        ]

        # Form con entry
        frm_form = ttk.Frame(self)
        frm_form.pack(padx=10, pady=10, fill="x")

        self.entries = {}
        for i, field in enumerate(self.fields):
            lbl = ttk.Label(frm_form, text=field + ":", font=FONT_NORMAL)
            lbl.grid(row=i, column=0, sticky="w", pady=3)
            ent = ttk.Entry(frm_form, font=FONT_NORMAL)
            ent.grid(row=i, column=1, sticky="ew", pady=3)
            self.entries[field] = ent
        frm_form.columnconfigure(1, weight=1)

        # Bottoni
        frm_buttons = ttk.Frame(self)
        frm_buttons.pack(pady=10)

        self.btn_pulisci = ttk.Button(frm_buttons, text="Pulisci", command=self.clear_entries)
        self.btn_pulisci.pack(side="left", padx=5)

        self.btn_anteprima = ttk.Button(frm_buttons, text="Anteprima", command=self.show_preview)
        self.btn_anteprima.pack(side="left", padx=5)

        self.btn_stampa = ttk.Button(frm_buttons, text="Stampa", command=self.print_label)
        self.btn_stampa.pack(side="left", padx=5)

        # Variabili per anteprima
        self.preview_window = None
        self.canvas = None
        self.img_tk = None  # Mantiene riferimento immagine Tkinter

    def clear_entries(self):
        for ent in self.entries.values():
            ent.delete(0, tk.END)
        if self.logger:
            self.logger.log("Campi etichetta puliti. 🧹")

    def crea_immagine(self):
        larghezza, altezza = 400, 250
        img = Image.new("RGB", (larghezza, altezza), "white")
        draw = ImageDraw.Draw(img)

        try:
            font_title = ImageFont.truetype("arial.ttf", 22)
            font_text = ImageFont.truetype("arial.ttf", 16)
        except:
            font_title = ImageFont.load_default()
            font_text = ImageFont.load_default()

        title = "ETICHETTA"
        w, h = draw.textbbox((0, 0), title, font=font_title)[2:]
        draw.text(((larghezza - w) / 2, 10), title, fill="black", font=font_title)

        draw.line([(20, 45), (larghezza - 20, 45)], fill="black", width=2)

        y = 60
        for field in self.fields:
            val = self.entries[field].get()
            text = f"{field}: {val}"
            w, h = draw.textbbox((0, 0), text, font=font_text)[2:]
            draw.text(((larghezza - w) / 2, y), text, fill="black", font=font_text)
            y += h + 10

        draw.rectangle([5, 5, larghezza - 5, altezza - 5], outline="black", width=2)

        return img

    def show_preview(self):
        img = self.crea_immagine()
        if self.preview_window is None or not self.preview_window.winfo_exists():
            self.preview_window = tk.Toplevel(self)
            self.preview_window.title("Anteprima Etichetta")
            self.preview_window.geometry("420x280")
            self.preview_window.resizable(False, False)
            self.canvas = tk.Canvas(self.preview_window, width=img.width, height=img.height)
            self.canvas.pack()
            self.preview_window.protocol("WM_DELETE_WINDOW", self._on_preview_close)

        self.canvas.delete("all")
        self.img_tk = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.img_tk)
        if self.logger:
            self.logger.log("Anteprima etichetta visualizzata. 👀")

    def _on_preview_close(self):
        if self.preview_window:
            self.preview_window.destroy()
        self.preview_window = None
        self.canvas = None
        self.img_tk = None

    def print_label(self):
        img = self.crea_immagine()
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        img.save(tmp_file.name)
        tmp_file.close()
        try:
            if os.name == 'nt':
                os.startfile(tmp_file.name, "print")
            else:
                messagebox.showinfo("Stampa", "La stampa è supportata solo su Windows.")
            if self.logger:
                self.logger.log("Etichetta inviata alla stampante. 🖨️")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la stampa:\n{e}")

class ProduzioneFrame(ttk.Frame):
    def __init__(self, parent, file_path, logger=None):
        super().__init__(parent)
        self.file_path = file_path
        self.logger = logger
        self.data = []
        self.filtered_data = []
        self.current_selection_index = None

        self._create_widgets()
        self.load_data()
        self.refresh_tree()

    def _create_widgets(self):
        # Form inserimento
        frm_form = ttk.Frame(self)
        frm_form.pack(fill="x", padx=10, pady=10)

        self.entries = {}
        fields = ["Cliente", "Lavoro", "Data Inizio", "Data Fine Prevista", "Quantità Totale", "Quantità Completata"]
        for i, col in enumerate(fields):
            ttk.Label(frm_form, text=col + ":", font=FONT_NORMAL).grid(row=i, column=0, sticky="w", pady=4)
            ent = ttk.Entry(frm_form, font=FONT_NORMAL)
            ent.grid(row=i, column=1, sticky="ew", pady=4)
            self.entries[col] = ent
        frm_form.columnconfigure(1, weight=1)

        # Pulsanti
        frm_buttons = ttk.Frame(self)
        frm_buttons.pack(fill="x", padx=10, pady=5)
        ttk.Button(frm_buttons, text="Aggiungi", command=self.add_record).pack(side="left", padx=5)
        ttk.Button(frm_buttons, text="Modifica", command=self.edit_record).pack(side="left", padx=5)
        ttk.Button(frm_buttons, text="Elimina", command=self.delete_record).pack(side="left", padx=5)

        # Tabella
        self.tree = ttk.Treeview(
            self,
            columns=["Cliente", "Lavoro", "Data Inizio", "Data Fine Prevista", "Quantità Totale", "Quantità Completata", "Avanzamento"],
            show="headings",
            selectmode="browse",
            height=12
        )
        for col in ["Cliente", "Lavoro", "Data Inizio", "Data Fine Prevista", "Quantità Totale", "Quantità Completata", "Avanzamento"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)
        self.tree.pack(expand=True, fill="both", padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Stile Progressbar moderna
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("green.Horizontal.TProgressbar", troughcolor="#E0E0E0", bordercolor="#E0E0E0",
                        background="#4CAF50", lightcolor="#4CAF50", darkcolor="#388E3C")

    def get_entries_data(self):
        return {col: self.entries[col].get().strip() for col in self.entries}

    def clear_entries(self):
        for ent in self.entries.values():
            ent.delete(0, tk.END)

    def add_record(self):
        self.data.append(self.get_entries_data())
        self.save_data()
        self.refresh_tree()
        self.clear_entries()

    def edit_record(self):
        if self.current_selection_index is None:
            return
        self.data[self.current_selection_index] = self.get_entries_data()
        self.save_data()
        self.refresh_tree()
        self.clear_entries()

    def delete_record(self):
        if self.current_selection_index is None:
            return
        del self.data[self.current_selection_index]
        self.save_data()
        self.refresh_tree()
        self.clear_entries()

    def load_data(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = []

    def save_data(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.filtered_data = self.data
        for item in self.filtered_data:
            totale = int(item.get("Quantità Totale", 0) or 0)
            completata = int(item.get("Quantità Completata", 0) or 0)
            perc = int((completata / totale) * 100) if totale > 0 else 0

            vals = [
                item.get("Cliente", ""),
                item.get("Lavoro", ""),
                item.get("Data Inizio", ""),
                item.get("Data Fine Prevista", ""),
                totale,
                completata,
                f"{perc}%"
            ]
            self.tree.insert("", "end", values=vals)

    def on_tree_select(self, _event):
        selected = self.tree.selection()
        if not selected:
            self.current_selection_index = None
            return
        item = self.tree.item(selected[0])
        values = item["values"]
        self.current_selection_index = self.tree.index(selected[0])
        for col, val in zip(self.entries.keys(), values):
            self.entries[col].delete(0, tk.END)
            self.entries[col].insert(0, val)

    # -------------------------
    # gl iimport li tengo qui perchè sto lavorando sul modulo clienti e mi va più comodo 
    # -------------------------        
import os
import json
import shutil
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import pandas as pd
import subprocess
import sys
import win32api
import win32print


class ClientiFrame(tb.Frame):
    """
    ClientiFrame completo:
    - salva/carica clienti in JSON (default 'clienti.json')
    - Import/Export Excel (schermata principale)
    - popup dettagli cliente (header azzurro, documenti, note editabili, extra)
    - documenti vengono copiati in una cartella locale per sicurezza
    """

    def __init__(self, parent, logger=None, file_path="clienti.json", docs_folder="clienti_documenti"):
        super().__init__(parent)
        self.logger = logger
        self.file_path = file_path
        self.docs_folder = docs_folder
        os.makedirs(self.docs_folder, exist_ok=True)

        # colonne principali
        self.fields = ["Nome", "Cognome", "Telefono", "Email", "P.IVA", "Indirizzo", "Comune"]

        # dati
        self.clients = []
        self.next_id = 1
        self.sort_state = {}

        # UI
        title = tb.Label(self, text="👥 Gestione Clienti", font=("Segoe UI", 20, "bold"))
        title.pack(fill="x", pady=(8, 6))

        info_lbl = tb.Label(
            self,
            text="ℹ️ Doppio clic su Nome Cliente → apre dettagli | Doppio clic su Indirizzo/Comune → apre Google Maps",
            font=("Segoe UI", 10, "italic"),
            foreground="gray"
        )
        info_lbl.pack(fill="x", pady=(0, 8), padx=8)

        main = tb.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=6)

        # form a sinistra
        frm_left = tb.Labelframe(main, text="Dati Cliente", padding=8, bootstyle=SECONDARY)
        frm_left.pack(side="left", fill="y", padx=(0, 12))

        self.entries = {}
        for f in self.fields:
            r = tb.Frame(frm_left)
            r.pack(fill="x", pady=4)
            tb.Label(r, text=f + ":", width=12, anchor="w").pack(side="left")
            e = tb.Entry(r)
            e.pack(side="left", fill="x", expand=True)
            self.entries[f] = e

        # azioni CRUD
        btns = tb.Frame(frm_left)
        btns.pack(fill="x", pady=(8, 0))
        tb.Button(btns, text="➕ Aggiungi", bootstyle=SUCCESS, command=self.add_cliente).pack(fill="x", pady=3)
        tb.Button(btns, text="✏️ Modifica", bootstyle=INFO, command=self.edit_cliente).pack(fill="x", pady=3)
        tb.Button(btns, text="🗑️ Elimina", bootstyle=DANGER, command=self.del_cliente).pack(fill="x", pady=3)
        tb.Button(btns, text="🧹 Pulisci campi", bootstyle=SECONDARY, command=self.clear_fields).pack(fill="x", pady=3)

        tb.Separator(frm_left).pack(fill="x", pady=6)

        tb.Button(btns, text="📥 Importa Excel", bootstyle=PRIMARY, command=self.import_excel).pack(fill="x", pady=3)
        tb.Button(btns, text="📤 Esporta Excel", bootstyle=PRIMARY, command=self.export_excel).pack(fill="x", pady=3)

        # area tabella principale
        right = tb.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        # ricerca
        search = tb.Frame(right)
        search.pack(fill="x", pady=(0, 6))
        tb.Label(search, text="🔍 Cerca:").pack(side="left", padx=(0,6))
        self.search_var = tb.StringVar()
        ent_search = tb.Entry(search, textvariable=self.search_var, width=40)
        ent_search.pack(side="left", padx=(6,0))
        ent_search.bind("<KeyRelease>", self.filtra_clienti)

        # treeview
        self.tree = ttk.Treeview(right, columns=self.fields, show="headings", selectmode="browse")
        for col in self.fields:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_col(c))
            self.tree.column(col, width=130, anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")

        vsb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")

        self.tree.tag_configure('odd', background='#ffffff')
        self.tree.tag_configure('even', background='#f7f9fb')

        # bind eventi
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)  # gestisce maps vs popup

        # carica dati da file (se esistono)
        self.load_clients()
        self.populate_tree()

    # ----------------------------
    # file I/O
    # ----------------------------
    def load_clients(self):
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.clients = json.load(f)
                # normalize missing fields
                for c in self.clients:
                    for key in ("documenti", "note", "extra"):
                        if key not in c:
                            c[key] = []
                # next_id
                ids = [c.get("id", 0) for c in self.clients]
                self.next_id = max(ids) + 1 if ids else 1
            else:
                self.clients = []
                self.next_id = 1
        except Exception as e:
            messagebox.showerror("Errore", f"Errore caricamento clienti:\n{e}")
            self.clients = []
            self.next_id = 1

    def save_clients(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.clients, f, ensure_ascii=False, indent=2)
            if self.logger:
                self.logger.log(f"💾 Clienti salvati in {self.file_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare i clienti:\n{e}")

    # ----------------------------
    # popolamento UI
    # ----------------------------
    def populate_tree(self, filter_text=""):
        self.tree.delete(*self.tree.get_children())
        ft = (filter_text or "").lower().strip()
        idx = 0
        for c in self.clients:
            combined = " ".join(str(c.get(col,"")) for col in self.fields).lower()
            if ft and ft not in combined:
                continue
            tag = 'even' if idx % 2 == 0 else 'odd'
            values = [c.get(col,"") for col in self.fields]
            self.tree.insert("", "end", iid=str(c["id"]), values=values, tags=(tag,))
            idx += 1

    # ----------------------------
    # selezione / CRUD
    # ----------------------------
    def on_tree_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        try:
            cid = int(iid)
        except:
            return
        client = next((x for x in self.clients if x.get("id")==cid), None)
        if not client:
            return
        for col in self.fields:
            self.entries[col].delete(0, "end")
            self.entries[col].insert(0, client.get(col, ""))

    def add_cliente(self):
        vals = [self.entries[c].get().strip() for c in self.fields]
        if not any(vals):
            messagebox.showwarning("Attenzione", "Compila almeno un campo prima di aggiungere.")
            return
        client = {"id": self.next_id}
        for i, col in enumerate(self.fields):
            client[col] = vals[i] if i < len(vals) else ""
        client.setdefault("documenti", [])
        client.setdefault("note", [])
        client.setdefault("extra", [])
        self.clients.append(client)
        self.next_id += 1
        self.save_clients()
        self.populate_tree(self.search_var.get())
        self.clear_fields()
        if self.logger: self.logger.log("➕ Cliente aggiunto")

    def edit_cliente(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un cliente da modificare.")
            return
        cid = int(sel[0])
        client = next((x for x in self.clients if x["id"]==cid), None)
        if not client:
            return
        for col in self.fields:
            client[col] = self.entries[col].get().strip()
        self.save_clients()
        self.populate_tree(self.search_var.get())
        self.clear_fields()
        if self.logger: self.logger.log("✏️ Cliente modificato")

    def del_cliente(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un cliente da eliminare.")
            return
        if not messagebox.askyesno("Conferma", "Eliminare il cliente selezionato?"):
            return
        cid = int(sel[0])
        # rimuove metadati (non eliminiamo per sicurezza i file fisici automaticamente)
        self.clients = [c for c in self.clients if c["id"] != cid]
        self.save_clients()
        self.populate_tree(self.search_var.get())
        self.clear_fields()
        if self.logger: self.logger.log("🗑️ Cliente eliminato")

    def clear_fields(self):
        for e in self.entries.values():
            e.delete(0, "end")
        try:
            self.tree.selection_remove(self.tree.selection())
        except:
            pass
        if self.logger: self.logger.log("🧹 Campi puliti")

    # ----------------------------
    # ricerca / ordine
    # ----------------------------
    def filtra_clienti(self, event=None):
        self.populate_tree(self.search_var.get())

    def sort_col(self, col):
        rev = self.sort_state.get(col, False)
        self.clients.sort(key=lambda x: str(x.get(col,"")).lower(), reverse=rev)
        self.sort_state[col] = not rev
        self.populate_tree(self.search_var.get())

    # ----------------------------
    # doppio clic: maps vs popup
    # ----------------------------
    def on_tree_double_click(self, event):
        # identifichiamo riga + colonna
        rowid = self.tree.identify_row(event.y)
        colid = self.tree.identify_column(event.x)
        if not rowid:
            return
        cid = int(rowid)
        client = next((x for x in self.clients if x["id"]==cid), None)
        if not client:
            return
        # se ha cliccato sulla colonna Indirizzo o Comune -> apri maps
        try:
            col_index = int(colid.replace("#","")) - 1
        except:
            col_index = None
        if col_index is not None and 0 <= col_index < len(self.fields):
            cname = self.fields[col_index]
            if cname in ("Indirizzo", "Comune"):
                addr = f"{client.get('Indirizzo','')} {client.get('Comune','')}".strip()
                if addr:
                    url = "https://www.google.com/maps/search/" + addr.replace(" ", "+")
                    webbrowser.open(url)
                    if self.logger: self.logger.log(f"🌍 Aperto Maps per: {addr}")
                    return
        # altrimenti apri popup dettagliato
        self.open_client_popup(client)

    # ----------------------------
    # excel import/export (principale)
    # ----------------------------
    def import_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if not path:
            return
        try:
            df = pd.read_excel(path)
            # proviamo a mappare colonne, se esistono nomi identici li usiamo, altrimenti usiamo ordine
            for _, row in df.iterrows():
                vals = []
                for col in self.fields:
                    if col in df.columns:
                        vals.append(str(row.get(col, "")))
                    else:
                        # fallback: if DataFrame has positional columns, use by position
                        vals.append("")
                # aggiunge cliente
                client = {"id": self.next_id}
                for i, col in enumerate(self.fields):
                    client[col] = vals[i] if i < len(vals) else ""
                client.setdefault("documenti", [])
                client.setdefault("note", [])
                client.setdefault("extra", [])
                self.clients.append(client)
                self.next_id += 1
            self.save_clients()
            self.populate_tree()
            if self.logger: self.logger.log(f"⬆️ Importati clienti da {os.path.basename(path)}")
            messagebox.showinfo("Import", "Import completato.")
        except Exception as e:
            messagebox.showerror("Errore import", str(e))

    def export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.DataFrame([{col: c.get(col,"") for col in self.fields} for c in self.clients])
            df.to_excel(path, index=False)
            if self.logger: self.logger.log(f"⬇️ Esportati clienti su {os.path.basename(path)}")
            messagebox.showinfo("Export", "Esportazione completata.")
        except Exception as e:
            messagebox.showerror("Errore export", str(e))

    # ----------------------------
    # popup dettagli cliente (documenti / note / extra)
    # ----------------------------
    def open_client_popup(self, client):
        popup = tb.Toplevel(self)
        popup.title(f"Scheda Cliente - {client.get('Nome','')} {client.get('Cognome','')}")
        
        # dimensioni più grandi e minime
        popup.geometry("1200x800")
        popup.minsize(1100, 500)
        popup.transient(self)
        popup.grab_set()

        # centra la finestra
        popup.update_idletasks()
        w = popup.winfo_width()
        h = popup.winfo_height()
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        popup.geometry(f"{w}x{h}+{x}+{y}")

        # header azzurro
        header = tk.Frame(popup, bg="#0d6efd")
        header.pack(fill="x")
        tk.Label(header, text=f"👤 {client.get('Nome','')} {client.get('Cognome','')}",
                 font=("Segoe UI", 16, "bold"), fg="white", bg="#0d6efd").pack(side="left", padx=12, pady=12)
        tk.Label(header, text=f"P.IVA: {client.get('P.IVA','')}", font=("Segoe UI", 10), fg="white", bg="#0d6efd")\
            .pack(side="left", padx=8)

        # pulsanti rapidi
        quick = tb.Frame(popup)
        quick.pack(fill="x", padx=10, pady=6)
        tb.Button(quick, text="🌍 Maps", bootstyle=INFO,
                  command=lambda: webbrowser.open("https://www.google.com/maps/search/" + f"{client.get('Indirizzo','')} {client.get('Comune','')}".replace(" ", "+"))
                  ).pack(side="left", padx=6)
        tb.Button(quick, text="✉️ Email", bootstyle=SUCCESS,
                  command=lambda: webbrowser.open(f"mailto:{client.get('Email','')}")).pack(side="left", padx=6)
        tb.Button(quick, text="📞 Telefono", bootstyle=WARNING,
                  command=lambda: messagebox.showinfo("Telefono", f"Chiama: {client.get('Telefono','')}")).pack(side="left", padx=6)

        # notebook
        nb = tb.Notebook(popup)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Info tab (dati statici) ---
        tab_info = tb.Frame(nb)
        nb.add(tab_info, text="📋 Info")
        for r, col in enumerate(self.fields):
            tb.Label(tab_info, text=f"{col}:", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", padx=12, pady=6)
            tb.Label(tab_info, text=client.get(col, ""), font=("Segoe UI", 10)).grid(row=r, column=1, sticky="w", padx=12, pady=6)

                        # --- Documenti tab ---
                # --- Documenti tab ---
        tab_docs = tb.Frame(nb)
        nb.add(tab_docs, text="📂 Documenti")

        docs_cols = ("Data", "Nome", "Formato", "Percorso")
        docs_tree = ttk.Treeview(tab_docs, columns=docs_cols, show="headings", height=10)
        for c in docs_cols:
            docs_tree.heading(c, text=c)
            docs_tree.column(c, width=200)
        docs_tree.pack(fill="both", expand=True, side="left", padx=(10, 0), pady=8)

        docs_sb = ttk.Scrollbar(tab_docs, orient="vertical", command=docs_tree.yview)
        docs_tree.configure(yscroll=docs_sb.set)
        docs_sb.pack(side="right", fill="y")

        # popola documenti
        for d in client.get("documenti", []):
            docs_tree.insert("", "end", values=(d.get("data", ""), d.get("nome", ""), d.get("formato", ""), d.get("path", "")))

        # funzioni documenti
        def import_doc_local():
            path = filedialog.askopenfilename()
            if not path:
                return
            try:
                nome = os.path.basename(path)
                fmt = os.path.splitext(nome)[1].lstrip(".").lower()
                data_s = datetime.now().strftime("%Y-%m-%d %H:%M")
                dest_name = f"{client['id']}_{int(datetime.now().timestamp())}_{nome}"
                dest_path = os.path.join(self.docs_folder, dest_name)
                shutil.copy2(path, dest_path)
                doc = {"data": data_s, "nome": nome, "formato": fmt, "path": dest_path}
                client.setdefault("documenti", []).append(doc)
                docs_tree.insert("", "end", values=(doc["data"], doc["nome"], doc["formato"], doc["path"]))
                self.save_clients()
                if self.logger: 
                    self.logger.log(f"📥 Documento importato per {client.get('Nome','')}: {nome}")
            except Exception as e:
                messagebox.showerror("Errore import", str(e))

        def open_doc_local():
            sel = docs_tree.selection()
            if not sel:
                messagebox.showwarning("Attenzione", "Seleziona un documento.")
                return
            path = docs_tree.item(sel[0])["values"][3]
            if not path or not os.path.exists(path):
                messagebox.showerror("Errore", "File non trovato.")
                return
            try:
                if os.name == "nt":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    os.system(f"open \"{path}\"")
                else:
                    os.system(f'xdg-open "{path}"')
            except Exception as e:
                messagebox.showerror("Errore apertura", str(e))

        def export_doc_local():
            sel = docs_tree.selection()
            if not sel:
                messagebox.showwarning("Attenzione", "Seleziona un documento da esportare.")
                return
            src = docs_tree.item(sel[0])["values"][3]
            if not src or not os.path.exists(src):
                messagebox.showerror("Errore", "File sorgente non trovato.")
                return
            target = filedialog.asksaveasfilename(initialfile=docs_tree.item(sel[0])["values"][1])
            if not target:
                return
            try:
                shutil.copy2(src, target)
                messagebox.showinfo("Esporta", f"Documento salvato in: {target}")
            except Exception as e:
                messagebox.showerror("Errore export", str(e))

        def del_doc_local():
            sel = docs_tree.selection()
            if not sel:
                messagebox.showwarning("Attenzione", "Seleziona un documento da eliminare.")
                return
            if not messagebox.askyesno("Conferma", "Eliminare il documento selezionato?"):
                return
            vals = docs_tree.item(sel[0])["values"]
            client["documenti"] = [d for d in client.get("documenti", []) 
                                   if not (d.get("data") == vals[0] and d.get("nome") == vals[1])]
            try:
                if os.path.exists(vals[3]) and os.path.commonpath(
                    [os.path.abspath(vals[3]), os.path.abspath(self.docs_folder)]
                ) == os.path.abspath(self.docs_folder):
                    os.remove(vals[3])
            except Exception:
                pass
            docs_tree.delete(sel[0])
            self.save_clients()
            if self.logger: 
                self.logger.log("🗑️ Documento eliminato")

        # bottoni documenti
        docs_btns = tb.Frame(tab_docs)
        docs_btns.pack(fill="y", padx=10, pady=(0, 8), side="right")

        tb.Button(docs_btns, text="📥 Importa documento", bootstyle=INFO, command=import_doc_local).pack(fill="x", pady=4)
        tb.Button(docs_btns, text="📤 Esporta documento", bootstyle=PRIMARY, command=export_doc_local).pack(fill="x", pady=4)
        tb.Button(docs_btns, text="📂 Apri documento", bootstyle=SECONDARY, command=open_doc_local).pack(fill="x", pady=4)
        tb.Button(docs_btns, text="🗑️ Elimina documento", bootstyle=DANGER, command=del_doc_local).pack(fill="x", pady=4)



class MainApp(tb.Window):
    def __init__(self):
        super().__init__(themename="darkly")  # altri temi: "cosmo", "solar", "flatly", "cyborg"...
        self.title("Archivio aziendale – Produzione Varutti Gabriele – Vietata la copia")
        self.geometry("1100x750")
        self.resizable(True, True)

        # Logger in basso (senza bootstyle, perché LoggerFrame non lo supporta)
        self.logger = LoggerFrame(self)
        self.logger.pack(side="bottom", fill="x")

        # Frame laterale menu
        self.menu_frame = ttk.Frame(self, padding=10)
        self.menu_frame.pack(side="left", fill="y")

        # Container centrale
        container = ttk.Frame(self)
        container.pack(side="right", expand=True, fill="both")
        self.container = container

        # Archivio fatture
        self.archivio_fatture = ArchivioFatture()

        # Dizionario con tutti i frame
        self.frames = {}
        self.init_frames(container)

        # Bottoni menu
        self.create_menu_buttons()

        # Mostra primo frame
        self.show_frame("Clienti")

    def init_frames(self, container):
        """Inizializza tutti i frame"""
        self.frames["Clienti"] = BaseDataFrame(container, FILE_CLIENTI,
            ["Nome", "Cognome", "Telefono", "Email", "P.IVA", "Indirizzo", "Comune"], self.logger)

        self.frames["Prodotti"] = BaseDataFrame(container, FILE_PRODOTTI,
            ["Codice", "Descrizione", "Prezzo", "Quantità", "Data di Scadenza", "Fornitore"], self.logger)

        self.frames["Consegne"] = BaseDataFrame(container, FILE_CONSEGNE,
            ["Cliente", "Prodotto", "Data Consegna", "Quantità", "Comune e indirizzo",
             "Pagato si o no?", "Prezzo"], self.logger)

        self.frames["Produzione"] = ProduzioneFrame(container, FILE_PRODUZIONE, self.logger)
        self.frames["Note"] = NoteFrame(container, self.logger)
        self.frames["Stoccaggio"] = StoccaggioFrame(container, self.logger)
        self.frames["Backup"] = BackupFrame(container, self.logger)
        self.frames["Etichette"] = EtichetteFrame(container, self.logger)
        self.frames["Fatture"] = FattureFrame(container, self.archivio_fatture, self.logger)
        self.frames["Clienti"] = ClientiFrame(container, self.logger)


        # Nascondi tutti i frame
        for frame in self.frames.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            frame.lower()

    def create_menu_buttons(self):
        """Crea i pulsanti del menu laterale con icone ed effetto hover"""
        btns = [
            ("Clienti", "👥"),
            ("Prodotti", "📦"),
            ("Consegne", "🚚"),
            ("Note", "📝"),
            ("Stoccaggio", "🏗️"),
            ("Backup", "💾"),
            ("Etichette", "🏷️"),
            ("Fatture", "🧾"),
            ("Produzione", "🏭")
        ]

        for name, emoji in btns:
            btn = tb.Button(
                self.menu_frame,
                text=f"{emoji} {name}",
                bootstyle=INFO,  # colore moderno
                width=18,
                command=lambda n=name: self.show_frame(n)
            )
            btn.pack(fill="x", pady=4)

    def show_frame(self, name):
        for frame in self.frames.values():
            frame.lower()
        frame = self.frames[name]
        frame.lift()
        if self.logger:
            self.logger.log(f"🔄 Selezionato pannello: {name}")


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
    