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
import os
import json
from tkinter import messagebox



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

class StoccaggioFrame(tb.Frame):
    def __init__(self, parent, logger=None, file_path="stoccaggio.json"):
        super().__init__(parent)
        self.logger = logger
        self.file_path = file_path
        self.stoccaggi = []

        # campi principali
        self.fields = ["Descrizione", "DataProduzione", "DataScadenza", "Lotto", "NumeroScatola"]

        # titolo
        title = tb.Label(self, text="📦 Gestione Stoccaggio", font=("Segoe UI", 20, "bold"))
        title.pack(fill="x", pady=(8, 6))

        main = tb.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=6)

        # form a sinistra
        frm_left = tb.Labelframe(main, text="Dati Stoccaggio", padding=8, bootstyle=SECONDARY)
        frm_left.pack(side="left", fill="y", padx=(0, 12))

        self.entries = {}
        for f in self.fields:
            r = tb.Frame(frm_left)
            r.pack(fill="x", pady=4)
            tb.Label(r, text=f + ":", width=14, anchor="w").pack(side="left")
            e = tb.Entry(r, bootstyle="secondary")  # usa solo bootstyle, non Style globale
            e.pack(side="left", fill="x", expand=True)
            self.entries[f] = e

        # pulsanti CRUD + Import/Export
        btns = tb.Frame(frm_left)
        btns.pack(fill="x", pady=(8, 0))
        tb.Button(btns, text="➕ Aggiungi", bootstyle=SUCCESS, command=self.add_stoccaggio).pack(fill="x", pady=3)
        tb.Button(btns, text="✏️ Modifica", bootstyle=INFO, command=self.edit_stoccaggio).pack(fill="x", pady=3)
        tb.Button(btns, text="🗑️ Elimina", bootstyle=DANGER, command=self.del_stoccaggio).pack(fill="x", pady=3)
        tb.Button(btns, text="🧹 Pulisci campi", bootstyle=SECONDARY, command=self.clear_fields).pack(fill="x", pady=3)

        tb.Separator(frm_left).pack(fill="x", pady=6)

        tb.Button(btns, text="📥 Importa Excel", bootstyle=PRIMARY, command=self.import_excel).pack(fill="x", pady=3)
        tb.Button(btns, text="📤 Esporta Excel", bootstyle=PRIMARY, command=self.export_excel).pack(fill="x", pady=3)

        # tabella a destra
        right = tb.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        self.tree = ttk.Treeview(right, columns=self.fields, show="headings", selectmode="browse")
        for col in self.fields:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")

        vsb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")

        # colori righe alternate
        self.tree.tag_configure('odd', background='#ffffff')
        self.tree.tag_configure('even', background='#f7f9fb')

        # eventi
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # carica dati iniziali
        self.load_stoccaggi()
        self.populate_tree()

    # ---------------- IMPORT / EXPORT EXCEL ----------------
    def import_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.read_excel(path)
            self.stoccaggi = df.to_dict(orient="records")
            self.save_stoccaggi()
            self.populate_tree()
            messagebox.showinfo("Import Excel", "Stoccaggi importati correttamente.")
            if self.logger:
                self.logger.log(f"Importati stoccaggi da {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'importazione Excel:\n{e}")

    def export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.DataFrame(self.stoccaggi)
            df.to_excel(path, index=False)
            messagebox.showinfo("Export Excel", f"Stoccaggi esportati in {path}")
            if self.logger:
                self.logger.log(f"Esportati stoccaggi in {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'esportazione Excel:\n{e}")

    # ---------------- CRUD ----------------
    def add_stoccaggio(self):
        data = {f: self.entries[f].get() for f in self.fields}
        if not data["Descrizione"] or not data["Lotto"]:
            messagebox.showwarning("Attenzione", "Inserisci almeno Descrizione e Lotto")
            return
        self.stoccaggi.append(data)
        self.save_stoccaggi()
        self.populate_tree()
        self.clear_fields()
        if self.logger:
            self.logger.log(f"Stoccaggio aggiunto: {data['Descrizione']} - Lotto {data['Lotto']}")

    def edit_stoccaggio(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona uno stoccaggio da modificare")
            return
        index = self.tree.index(sel[0])
        data = {f: self.entries[f].get() for f in self.fields}
        self.stoccaggi[index] = data
        self.save_stoccaggi()
        self.populate_tree()
        self.clear_fields()
        if self.logger:
            self.logger.log(f"Stoccaggio modificato: {data['Descrizione']} - Lotto {data['Lotto']}")

    def del_stoccaggio(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona uno stoccaggio da eliminare")
            return
        index = self.tree.index(sel[0])
        stoccaggio = self.stoccaggi.pop(index)
        self.save_stoccaggi()
        self.populate_tree()
        self.clear_fields()
        if self.logger:
            self.logger.log(f"Stoccaggio eliminato: {stoccaggio['Descrizione']} - Lotto {stoccaggio['Lotto']}")

    # ---------------- SUPPORTO ----------------
    def clear_fields(self):
        for f in self.fields:
            self.entries[f].delete(0, tk.END)

    def on_tree_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        values = item["values"]
        for i, f in enumerate(self.fields):
            self.entries[f].delete(0, tk.END)
            self.entries[f].insert(0, values[i])

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, s in enumerate(self.stoccaggi):
            values = [s.get(f, "") for f in self.fields]
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert("", "end", values=values, tags=(tag,))

    def load_stoccaggi(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.stoccaggi = json.load(f)
            for s in self.stoccaggi:
                for f in self.fields:
                    if f not in s:
                        s[f] = ""
        else:
            self.stoccaggi = []

    def save_stoccaggi(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.stoccaggi, f, indent=2, ensure_ascii=False)


class BackupFrame(ttk.Frame):
    def __init__(self, parent, logger=None):
        super().__init__(parent)
        self.logger = logger
        self.config_file = "backup_config.json"
        self.log_file = "backup_log.json"
        self.load_config()
        self.load_log()

        lbl_info = ttk.Label(self, text="Backup dati archivio", font=FONT_BOLD)
        lbl_info.pack(pady=10)

        frm_buttons = ttk.Frame(self)
        frm_buttons.pack(pady=10)

        btn_backup = ttk.Button(frm_buttons, text="Crea Backup ZIP", command=self.create_backup)
        btn_backup.pack(side="left", padx=5)

        btn_import = ttk.Button(frm_buttons, text="Importa Backup ZIP", command=self.import_backup)
        btn_import.pack(side="left", padx=5)

        btn_cartella = ttk.Button(frm_buttons, text="📂 Scegli cartella backup", command=self.choose_folder)
        btn_cartella.pack(side="left", padx=5)

        # Intervallo backup
        frm_schedule = ttk.Frame(self)
        frm_schedule.pack(pady=10)
        ttk.Label(frm_schedule, text="Intervallo automatico (minuti):").pack(side="left")
        self.var_interval = tk.IntVar(value=self.config.get("interval", 60))
        ent_interval = ttk.Entry(frm_schedule, textvariable=self.var_interval, width=6)
        ent_interval.pack(side="left", padx=5)
        ttk.Button(frm_schedule, text="Avvia automatico", command=self.start_auto_backup).pack(side="left", padx=5)
        ttk.Button(frm_schedule, text="Ferma", command=self.stop_auto_backup).pack(side="left", padx=5)

        self.lbl_status = ttk.Label(self, text="", font=FONT_NORMAL)
        self.lbl_status.pack(pady=10)

        # 🔹 Storico backup
        lbl_storico = ttk.Label(self, text="Storico Backup:", font=FONT_BOLD)
        lbl_storico.pack(pady=(10, 5))

        cols = ("#", "Data e ora", "Percorso")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=8)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200 if col != "#" else 50, anchor="center")
        self.tree.pack(expand=True, fill="both", padx=10, pady=5)

        self.refresh_log()

        self.job = None  # per gestire il ciclo after()

    # ---------------- CONFIG ----------------
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {"folder": os.getcwd(), "interval": 60}

    def save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    # ---------------- LOG ----------------
    def load_log(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, "r", encoding="utf-8") as f:
                self.log = json.load(f)
        else:
            self.log = []

    def save_log(self):
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(self.log, f, indent=2)

    def refresh_log(self):
        self.tree.delete(*self.tree.get_children())
        for idx, entry in enumerate(self.log, start=1):
            self.tree.insert("", "end", values=(idx, entry["time"], entry["path"]))

    def add_log(self, path):
        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "path": path
        }
        self.log.append(entry)
        self.save_log()
        self.refresh_log()

    # ---------------- BACKUP ----------------
    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.config["folder"] = folder
            self.save_config()
            self.lbl_status.config(text=f"Cartella backup: {folder}")

    def create_backup(self):
        folder = self.config.get("folder", os.getcwd())
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
        try:
            with zipfile.ZipFile(path, 'w') as backup_zip:
                for file in [FILE_CLIENTI, FILE_CONSEGNE, FILE_PRODOTTI, FILE_NOTE, FILE_STOCCAGGIO]:
                    if os.path.exists(file):
                        backup_zip.write(file)
            self.lbl_status.config(text=f"Backup creato: {path}")
            self.add_log(path)  # 🔹 aggiungi allo storico
            if self.logger:
                self.logger.log(f"Backup creato in {path} 🗃️")
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

    # ---------------- AUTO BACKUP ----------------
    def start_auto_backup(self):
        interval_ms = self.var_interval.get() * 60 * 1000
        self.config["interval"] = self.var_interval.get()
        self.save_config()
        self._schedule_backup(interval_ms)
        self.lbl_status.config(text=f"Backup automatico ogni {self.var_interval.get()} minuti avviato ⏱️")

    def _schedule_backup(self, interval_ms):
        self.create_backup()
        self.job = self.after(interval_ms, lambda: self._schedule_backup(interval_ms))

    def stop_auto_backup(self):
        if self.job:
            self.after_cancel(self.job)
            self.job = None
            self.lbl_status.config(text="Backup automatico fermato ⛔")

            

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
    # gl import li tengo qui perchè sto lavorando sul modulo clienti e mi va più comodo 
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

        # 🔹 Stile personalizzato per Entry dei clienti
        style = ttk.Style()
        style.theme_use("clam")  # usiamo clam per permettere override
        style.configure(
            "ClientEntry.TEntry",
            fieldbackground="#d9d9d9",  # sfondo interno
            background="#d9d9d9",       # bordo
            foreground="black",         # testo
            insertcolor="black"         # cursore
        )

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

            # 🔹 Entry con stile grigio personalizzato
            e = ttk.Entry(r, style="ClientEntry.TEntry")
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
        self.tree.bind("<Double-1>", self.on_tree_double_click)

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

class ProdottiFrame(tb.Frame):
    def __init__(self, parent, logger=None, file_path="prodotti.json"):
        super().__init__(parent)
        self.logger = logger
        self.file_path = file_path
        self.products = []

        # colonne
        self.fields = ["Codice", "Descrizione", "Prezzo", "Quantità", "DataScadenza", "Fornitore"]

        # titolo
        title = tb.Label(self, text="📦 Gestione Prodotti", font=("Segoe UI", 20, "bold"))
        title.pack(fill="x", pady=(8, 6))

        main = tb.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=6)

        # form a sinistra
        frm_left = tb.Labelframe(main, text="Dati Prodotto", padding=8, bootstyle=SECONDARY)
        frm_left.pack(side="left", fill="y", padx=(0, 12))

        self.entries = {}
        for f in self.fields:
            r = tb.Frame(frm_left)
            r.pack(fill="x", pady=4)
            tb.Label(r, text=f + ":", width=14, anchor="w").pack(side="left")
            e = tb.Entry(r)
            e.pack(side="left", fill="x", expand=True)
            self.entries[f] = e

        # pulsanti CRUD
        btns = tb.Frame(frm_left)
        btns.pack(fill="x", pady=(8, 0))
        tb.Button(btns, text="➕ Aggiungi", bootstyle=SUCCESS, command=self.add_prodotto).pack(fill="x", pady=3)
        tb.Button(btns, text="✏️ Modifica", bootstyle=INFO, command=self.edit_prodotto).pack(fill="x", pady=3)
        tb.Button(btns, text="🗑️ Elimina", bootstyle=DANGER, command=self.del_prodotto).pack(fill="x", pady=3)
        tb.Button(btns, text="🧹 Pulisci campi", bootstyle=SECONDARY, command=self.clear_fields).pack(fill="x", pady=3)

        tb.Separator(frm_left).pack(fill="x", pady=6)

        tb.Button(btns, text="📥 Importa Excel", bootstyle=PRIMARY, command=self.import_excel).pack(fill="x", pady=3)
        tb.Button(btns, text="📤 Esporta Excel", bootstyle=PRIMARY, command=self.export_excel).pack(fill="x", pady=3)

        # tabella a destra
        right = tb.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        self.tree = ttk.Treeview(right, columns=self.fields, show="headings", selectmode="browse")
        for col in self.fields:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")

        vsb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")

        # colori righe alternate
        self.tree.tag_configure('odd', background='#ffffff')
        self.tree.tag_configure('even', background='#f7f9fb')

        # eventi
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # carica dati iniziali
        self.load_products()
        self.populate_tree()

    # ---------------- IMPORT / EXPORT EXCEL ----------------
    def import_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.read_excel(path)
            self.products = df.to_dict(orient="records")
            self.save_products()
            self.populate_tree()
            messagebox.showinfo("Import Excel", "Prodotti importati correttamente.")
            if self.logger:
                self.logger.log(f"Importati prodotti da {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'importazione Excel:\n{e}")

    def export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.DataFrame(self.products)
            df.to_excel(path, index=False)
            messagebox.showinfo("Export Excel", f"Prodotti esportati in {path}")
            if self.logger:
                self.logger.log(f"Esportati prodotti in {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'esportazione Excel:\n{e}")

    # ---------------- CRUD ----------------
    def add_prodotto(self):
        data = {f: self.entries[f].get() for f in self.fields}
        if not data["Codice"] or not data["Descrizione"]:
            messagebox.showwarning("Attenzione", "Inserisci almeno Codice e Descrizione")
            return
        try:
            data["Prezzo"] = float(data["Prezzo"].replace(",", "."))
        except:
            data["Prezzo"] = 0.0
        self.products.append(data)
        self.save_products()
        self.populate_tree()
        self.clear_fields()
        if self.logger:
            self.logger.log(f"Prodotto aggiunto: {data['Codice']} - {data['Descrizione']}")

    def edit_prodotto(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un prodotto da modificare")
            return
        index = self.tree.index(sel[0])
        data = {f: self.entries[f].get() for f in self.fields}
        try:
            data["Prezzo"] = float(data["Prezzo"].replace(",", "."))
        except:
            data["Prezzo"] = 0.0
        self.products[index] = data
        self.save_products()
        self.populate_tree()
        self.clear_fields()
        if self.logger:
            self.logger.log(f"Prodotto modificato: {data['Codice']} - {data['Descrizione']}")

    def del_prodotto(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un prodotto da eliminare")
            return
        index = self.tree.index(sel[0])
        prodotto = self.products.pop(index)
        self.save_products()
        self.populate_tree()
        self.clear_fields()
        if self.logger:
            self.logger.log(f"Prodotto eliminato: {prodotto['Codice']} - {prodotto['Descrizione']}")

    # ---------------- SUPPORTO ----------------
    def clear_fields(self):
        for f in self.fields:
            self.entries[f].delete(0, tk.END)

    def on_tree_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        values = item["values"]
        for i, f in enumerate(self.fields):
            self.entries[f].delete(0, tk.END)
            if f == "Prezzo":
                self.entries[f].insert(0, str(values[i]).replace(" €", ""))
            else:
                self.entries[f].insert(0, values[i])

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, p in enumerate(self.products):
            values = [
                p.get("Codice", ""),
                p.get("Descrizione", ""),
                f"{float(p.get('Prezzo', 0)):.2f} €",
                p.get("Quantità", ""),
                p.get("DataScadenza", ""),
                p.get("Fornitore", "")
            ]
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert("", "end", values=values, tags=(tag,))

    def load_products(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.products = json.load(f)
            # allinea vecchi record ai campi nuovi
            for p in self.products:
                for f in self.fields:
                    if f not in p:
                        p[f] = ""
        else:
            self.products = []

    def save_products(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.products, f, indent=2, ensure_ascii=False)


 # Area CONSEGNE 

from urllib.parse import quote  # metti questo import in cima al file


class ConsegneFrame(tb.Frame):
    def __init__(self, parent, logger=None, file_path="consegne.json"):
        super().__init__(parent)
        self.logger = logger
        self.file_path = file_path
        self.consegne = []

        # campi principali
        self.fields = ["Cliente", "Prodotto", "DataConsegna", "Quantità", "Comune", "Indirizzo"]

        # titolo
        title = tb.Label(self, text="🚚 Gestione Consegne", font=("Segoe UI", 20, "bold"))
        title.pack(fill="x", pady=(8, 6))

        main = tb.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=6)

        # form a sinistra
        frm_left = tb.Labelframe(main, text="Dati Consegna", padding=8, bootstyle=SECONDARY)
        frm_left.pack(side="left", fill="y", padx=(0, 12))

        self.entries = {}
        for f in self.fields:
            r = tb.Frame(frm_left)
            r.pack(fill="x", pady=4)
            tb.Label(r, text=f + ":", width=14, anchor="w").pack(side="left")
            e = tb.Entry(r)
            e.pack(side="left", fill="x", expand=True)
            self.entries[f] = e

        # pulsanti CRUD + Import/Export + Pianificazione
        btns = tb.Frame(frm_left)
        btns.pack(fill="x", pady=(8, 0))
        tb.Button(btns, text="➕ Aggiungi", bootstyle=SUCCESS, command=self.add_consegna).pack(fill="x", pady=3)
        tb.Button(btns, text="✏️ Modifica", bootstyle=INFO, command=self.edit_consegna).pack(fill="x", pady=3)
        tb.Button(btns, text="🗑️ Elimina", bootstyle=DANGER, command=self.del_consegna).pack(fill="x", pady=3)
        tb.Button(btns, text="🧹 Pulisci campi", bootstyle=SECONDARY, command=self.clear_fields).pack(fill="x", pady=3)

        tb.Separator(frm_left).pack(fill="x", pady=6)

        tb.Button(btns, text="📥 Importa Excel", bootstyle=PRIMARY, command=self.import_excel).pack(fill="x", pady=3)
        tb.Button(btns, text="📤 Esporta Excel", bootstyle=PRIMARY, command=self.export_excel).pack(fill="x", pady=3)


        # tabella a destra
        right = tb.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        self.tree = ttk.Treeview(right, columns=self.fields, show="headings", selectmode="browse")
        for col in self.fields:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")

        vsb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")

        # colori righe alternate
        self.tree.tag_configure('odd', background='#ffffff')
        self.tree.tag_configure('even', background='#f7f9fb')

        # eventi
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_double_click)

        # carica dati iniziali
        self.load_consegne()
        self.populate_tree()

    # ---------------- IMPORT / EXPORT EXCEL ----------------
    def import_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.read_excel(path)
            self.consegne = df.to_dict(orient="records")
            self.save_consegne()
            self.populate_tree()
            messagebox.showinfo("Import Excel", "Consegne importate correttamente.")
            if self.logger:
                self.logger.log(f"Importate consegne da {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'importazione Excel:\n{e}")

    def export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return
        try:
            df = pd.DataFrame(self.consegne)
            df.to_excel(path, index=False)
            messagebox.showinfo("Export Excel", f"Consegne esportate in {path}")
            if self.logger:
                self.logger.log(f"Esportate consegne in {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'esportazione Excel:\n{e}")

    # ---------------- CRUD ----------------
    def add_consegna(self):
        data = {f: self.entries[f].get() for f in self.fields}
        if not data["Cliente"] or not data["Prodotto"]:
            messagebox.showwarning("Attenzione", "Inserisci almeno Cliente e Prodotto")
            return
        self.consegne.append(data)
        self.save_consegne()
        self.populate_tree()
        self.clear_fields()
        if self.logger:
            self.logger.log(f"Consegna aggiunta: {data['Cliente']} - {data['Prodotto']}")

    def edit_consegna(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona una consegna da modificare")
            return
        index = self.tree.index(sel[0])
        data = {f: self.entries[f].get() for f in self.fields}
        self.consegne[index] = data
        self.save_consegne()
        self.populate_tree()
        self.clear_fields()
        if self.logger:
            self.logger.log(f"Consegna modificata: {data['Cliente']} - {data['Prodotto']}")

    def del_consegna(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona una consegna da eliminare")
            return
        index = self.tree.index(sel[0])
        consegna = self.consegne.pop(index)
        self.save_consegne()
        self.populate_tree()
        self.clear_fields()
        if self.logger:
            self.logger.log(f"Consegna eliminata: {consegna['Cliente']} - {consegna['Prodotto']}")

    # ---------------- SUPPORTO ----------------
    def clear_fields(self):
        for f in self.fields:
            self.entries[f].delete(0, tk.END)

    def on_tree_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        values = item["values"]
        for i, f in enumerate(self.fields):
            self.entries[f].delete(0, tk.END)
            self.entries[f].insert(0, values[i])

    def on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        col = self.tree.identify_column(event.x)
        col_index = int(col.replace("#", "")) - 1
        if self.fields[col_index] in ("Comune", "Indirizzo"):
            item = self.tree.item(sel[0])
            comune = item["values"][self.fields.index("Comune")]
            indirizzo = item["values"][self.fields.index("Indirizzo")]
            query = f"{indirizzo}, {comune}"
            url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            webbrowser.open(url)

    def pianifica_consegne(self):
        data = simpledialog.askstring("Pianifica consegne", "Quando andrai in consegna? (formato AAAA-MM-GG)")
        if not data:
            return

        partenza = simpledialog.askstring("Pianifica consegne", "Da che comune parte la consegna?")
        if not partenza:
            return

        consegne_filtrate = [c for c in self.consegne if c.get("DataConsegna") == data]
        if not consegne_filtrate:
            messagebox.showinfo("Nessuna consegna", f"Nessuna consegna trovata per il {data}")
            return

        tappe = [f"{c['Indirizzo']}, {c['Comune']}" for c in consegne_filtrate]

        # codifica URL con quote
        partenza_enc = quote(partenza)
        tappe_enc = [quote(t) for t in tappe]

        url = f"https://www.google.com/maps/dir/{partenza_enc}/" + "/".join(tappe_enc)
        webbrowser.open(url)

        if self.logger:
            self.logger.log(f"Pianificate consegne del {data} da {partenza}")

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, c in enumerate(self.consegne):
            values = [c.get(f, "") for f in self.fields]
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert("", "end", values=values, tags=(tag,))

    def load_consegne(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.consegne = json.load(f)
            for c in self.consegne:
                for f in self.fields:
                    if f not in c:
                        c[f] = ""
        else:
            self.consegne = []

    def save_consegne(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.consegne, f, indent=2, ensure_ascii=False)

class AssistenteFrame(tb.Frame):
    def __init__(self, parent, logger=None):
        super().__init__(parent)
        self.logger = logger
        self.expanded = None  # tiene traccia della sezione espansa

        # titolo
        title = tb.Label(self, text="🤖 Assistente Intelligente", font=("Segoe UI", 20, "bold"))
        title.pack(fill="x", pady=(8, 6))

        # barra di ricerca
        search_frame = tb.Frame(self)
        search_frame.pack(fill="x", pady=6, padx=8)

        self.search_var = tk.StringVar()
        entry = tb.Entry(search_frame, textvariable=self.search_var, width=80)
        entry.pack(side="left", padx=(0, 6), fill="x", expand=True)
        entry.bind("<Return>", self.search)

        tb.Button(search_frame, text="🔍 Cerca", bootstyle=INFO, command=self.search).pack(side="left")

        # contenitore
        self.container = tb.Frame(self)
        self.container.pack(fill="both", expand=True, padx=8, pady=6)
        self.container.grid_columnconfigure(0, weight=1)

        # sezioni
        self.sections = {}
        self.section_frames = {}
        self.buttons = {}

        labels = ["CLIENTI", "PRODOTTI", "CONSEGNE", "STOCCAGGIO"]

        for i, label in enumerate(labels):
            lf = tb.Labelframe(self.container, text=label, padding=8, bootstyle=INFO)
            lf.grid(row=i, column=0, sticky="nsew", padx=6, pady=6)

            lf.grid_rowconfigure(0, weight=1)
            lf.grid_columnconfigure(0, weight=1)

            tree = ttk.Treeview(lf, show="headings", height=6)  # 👈 base più alta
            tree.grid(row=0, column=0, sticky="nsew")

            vsb = ttk.Scrollbar(lf, orient="vertical", command=tree.yview)
            tree.configure(yscroll=vsb.set)
            vsb.grid(row=0, column=1, sticky="ns")

            # pulsante espandi/comprimi
            btn = tb.Button(lf, text="⤵ Espandi", bootstyle=SECONDARY,
                            command=lambda l=label: self.toggle_section(l))
            btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))

            # colonna placeholder
            tree["columns"] = ["Attesa"]
            tree.heading("Attesa", text="In attesa di ricerca...")
            tree.column("Attesa", width=400, anchor="center")
            tree.insert("", "end", values=["—"])

            self.sections[label] = tree
            self.section_frames[label] = lf
            self.buttons[label] = btn

        # layout iniziale con pesi uguali
        for i in range(len(labels)):
            self.container.grid_rowconfigure(i, weight=1)

    def toggle_section(self, label):
        """Espande o comprime la sezione scelta"""
        if self.expanded == label:
            # già espansa → comprime e torna normale
            for i, lf in enumerate(self.section_frames.values()):
                lf.grid(row=i, column=0, sticky="nsew", padx=6, pady=6)
                self.container.grid_rowconfigure(i, weight=1)
                self.buttons[list(self.section_frames.keys())[i]].config(text="⤵ Espandi")
            self.expanded = None
        else:
            # espande solo quella
            for lf in self.section_frames.values():
                lf.grid_remove()
            lf = self.section_frames[label]
            lf.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
            self.container.grid_rowconfigure(0, weight=3)  # 👈 più grande
            self.buttons[label].config(text="⬆ Comprimi")
            self.expanded = label

    def search(self, event=None):
        query = self.search_var.get().lower().strip()
        if not query:
            messagebox.showwarning("Attenzione", "Inserisci uno o più termini da cercare")
            return

        terms = query.split()  # 👈 multi-parola attiva

        file_map = {
            "CLIENTI": FILE_CLIENTI,
            "PRODOTTI": FILE_PRODOTTI,
            "CONSEGNE": FILE_CONSEGNE,
            "STOCCAGGIO": "stoccaggio.json",
        }

        for label, file_path in file_map.items():
            tree = self.sections[label]
            tree.delete(*tree.get_children())

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        dati = json.load(f)
                        matches = []
                        for d in dati:
                            testo = " ".join(str(v).lower() for v in d.values())
                            if all(term in testo for term in terms):  # 👈 TUTTE le parole
                                matches.append(d)

                        if matches:
                            cols = list(matches[0].keys())
                            tree["columns"] = cols
                            for c in cols:
                                tree.heading(c, text=c)
                                tree.column(c, width=150, anchor="w")

                            for m in matches:
                                tree.insert("", "end", values=[m[c] for c in cols])
                        else:
                            tree["columns"] = ["Nessun risultato"]
                            tree.heading("Nessun risultato", text="Nessun risultato")
                            tree.column("Nessun risultato", width=400, anchor="center")
                            tree.insert("", "end", values=["—"])

                    except Exception as e:
                        if self.logger:
                            self.logger.log(f"Errore lettura {file_path}: {e}")
            else:
                tree["columns"] = ["File mancante"]
                tree.heading("File mancante", text="File non trovato")
                tree.column("File mancante", width=400, anchor="center")
                tree.insert("", "end", values=["—"])

        if self.logger:
            self.logger.log(f"Assistente: ricerca '{query}' completata")


           





from ttkbootstrap.style import Style

class MainApp(tb.Window):
    def __init__(self):
        super().__init__(themename="minty")
        self.title("Archivio aziendale – Produzione Varutti Gabriele – Vietata la copia")
        self.geometry("1100x750")
        self.resizable(True, True)

        # stile bootstrap
        self.app_style = Style()
        self.current_bootstyle = "info"

        # 🎨 Menù in alto per temi e stili
        menubar = tk.Menu(self)

        theme_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🎨 Tema", menu=theme_menu)
        for t in ["flatly", "minty", "pulse", "darkly", "superhero", "forest"]:
            theme_menu.add_command(label=t, command=lambda th=t: self.change_theme(th))

        style_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🖌️ Stile", menu=style_menu)
        for s in ["info", "success", "danger", "secondary", "warning"]:
            style_menu.add_command(label=s, command=lambda st=s: self.change_bootstyle(st))

        self.config(menu=menubar)

        # Logger in basso
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

    # 🔹 Cambia tema globale
    def change_theme(self, theme_name):
        if theme_name == "forest":
            # 🎨 Palette personalizzata FOREST
            forest_palette = {
                "primary": "#2e7d32",     # verde foresta
                "secondary": "#81c784",   # verde chiaro
                "success": "#388e3c",     # verde scuro
                "info": "#4caf50",        # verde medio
                "warning": "#fbc02d",     # giallo sole
                "danger": "#d32f2f",      # rosso allarme
                "light": "#e8f5e9",       # sfondo verde chiaro
                "dark": "#1b5e20"         # verde molto scuro
            }

            # Applica i colori
            for role, color in forest_palette.items():
                self.app_style.colors.update({role: color})

            # Forziamo a usare una base chiara
            self.app_style.theme_use("flatly")

            if self.logger:
                self.logger.log("🌲 Tema cambiato in: forest (verde natura)")
        else:
            self.app_style.theme_use(theme_name)
            if self.logger:
                self.logger.log(f"🎨 Tema cambiato in: {theme_name}")

    # 🔹 Cambia stile bottoni
    def change_bootstyle(self, bootstyle):
        self.current_bootstyle = bootstyle
        for child in self.menu_frame.winfo_children():
            if isinstance(child, tb.Button):
                child.configure(bootstyle=bootstyle)
        if self.logger:
            self.logger.log(f"🖌️ Stile cambiato in: {bootstyle}")

    def init_frames(self, container):
        """Inizializza tutti i frame"""
        self.frames["Clienti"] = ClientiFrame(container, self.logger)
        self.frames["Prodotti"] = ProdottiFrame(container, self.logger)
        self.frames["Consegne"] = ConsegneFrame(container, self.logger)
        self.frames["Produzione"] = ProduzioneFrame(container, FILE_PRODUZIONE, self.logger)
        self.frames["Note"] = NoteFrame(container, self.logger)
        self.frames["Stoccaggio"] = StoccaggioFrame(container, self.logger)
        self.frames["Backup"] = BackupFrame(container, self.logger)
        self.frames["Etichette"] = EtichetteFrame(container, self.logger)
        self.frames["Fatture"] = FattureFrame(container, self.archivio_fatture, self.logger)
        self.frames["Assistente"] = AssistenteFrame(container, self.logger)

        # Nascondi tutti i frame
        for frame in self.frames.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            frame.lower()

    def create_menu_buttons(self):
        """Crea i pulsanti del menu laterale"""
        btns = [
            ("Clienti", "👥"),
            ("Prodotti", "📦"),
            ("Consegne", "🚚"),
            ("Note", "📝"),
            ("Stoccaggio", "🏗️"),
            ("Backup", "💾"),
            ("Etichette", "🏷️"),
            ("Fatture", "🧾"),
            ("Assistente", "🤖"),
            ("Produzione", "🏭")
        ]

        for name, emoji in btns:
            btn = tb.Button(
                self.menu_frame,
                text=f"{emoji} {name}",
                bootstyle=self.current_bootstyle,
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
