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


# ============================================================
# Costanti per colori e font
# ============================================================
BG_COLOR = "white"
MENU_BG = "#002fff"
MENU_BTN_BG = "#03cbea"
MENU_BTN_ACTIVE = "#0a84d5"
FG_COLOR = "white"
FONT_NORMAL = ("Segoe UI", 12)
FONT_BOLD = ("Segoe UI", 12, "bold")

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



# ================= MAIN APP CORRETTO =================

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Archivio aziendale – Produzione Varutti Gabriele – Vietata la copia")
        self.geometry("1000x700")
        self.configure(bg=BG_COLOR)

        # Applica lo stile personalizzato
        set_style(self)

        # Logger
        self.logger = LoggerFrame(self)
        self.logger.pack(side="bottom", fill="x")

        # Menu laterale
        self.menu_frame = ttk.Frame(self, padding=5, style="TFrame")
        self.menu_frame.pack(side="left", fill="y")

        self.frames = {}

        # Bottoni menu
        self.create_menu_buttons()

        # Container centrale
        container = ttk.Frame(self, style="TFrame")
        container.pack(side="right", expand=True, fill="both")
        self.container = container

        # Inizializza archivio fatture (gestione documenti)
        self.archivio_fatture = ArchivioFatture()

        # Inizializza tutti i frame
        self.frames["Clienti"] = BaseDataFrame(container, FILE_CLIENTI,
            ["Nome", "Cognome", "Telefono", "Email", "P.IVA", "Indirizzo", "Comune"], self.logger)

        self.frames["Prodotti"] = BaseDataFrame(container, FILE_PRODOTTI,
            ["Codice", "Descrizione", "Prezzo", "Quantità", "Data di Scadenza", "Fornitore"], self.logger)

        self.frames["Consegne"] = BaseDataFrame(container, FILE_CONSEGNE,
            ["Cliente", "Prodotto", "Data Consegna", "Quantità", "Comune e indirizzo",
             "Pagato si o no?", "Prezzo"], self.logger)
        
        # QUI usiamo ProduzioneFrame (non più BaseDataFrame!)
        self.frames["Produzione"] = ProduzioneFrame(container, FILE_PRODUZIONE, self.logger)

        self.frames["Note"] = NoteFrame(container, self.logger)
        self.frames["Stoccaggio"] = StoccaggioFrame(container, self.logger)
        self.frames["Backup"] = BackupFrame(container, self.logger)
        self.frames["Etichette"] = EtichetteFrame(container, self.logger)

        # Frame Fatture
        self.frames["Fatture"] = FattureFrame(container, self.archivio_fatture, self.logger)

        # Nascondi tutti i frame
        for frame in self.frames.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            frame.lower()

        # Mostra il primo frame
        self.show_frame("Clienti")

    def create_menu_buttons(self):
        btns = [
            ("Clienti", "👥"),
            ("Prodotti", "📦"),
            ("Consegne", "🚚"),
            ("Note", "📝"),
            ("Stoccaggio", "📦"),
            ("Backup", "💾"),
            ("Etichette", "🏷️"),
            ("Fatture", "🧾"),
            ("Produzione", "🏭")
        ]
        for name, emoji in btns:
            btn = ttk.Button(
                self.menu_frame,
                text=f"{emoji} {name}",
                command=lambda n=name: self.show_frame(n),
                style="TButton"
            )
            btn.pack(fill="x", pady=3)

    def show_frame(self, name):
        for frame in self.frames.values():
            frame.lower()
        frame = self.frames[name]
        frame.lift()
        if self.logger:
            self.logger.log(f"Selezionato pannello: {name} 🔄")


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
