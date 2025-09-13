import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json, os
import pandas as pd
from datetime import datetime

FILE_ARCHIVIO = "archivio.json"
FILE_CLIENTI = "clienti.json"
FILE_CONSEGNE = "consegne.json"


class FilterableFrame(tk.Frame):
    def __init__(self, parent, file_path, columns, use_popup_filter=False):
        super().__init__(parent, bg="white")
        self.file_path = file_path
        self.columns = columns
        self.data = []
        self.filtered_data = []
        self.entries = {}

        # Form per inserimento dati
        form_frame = tk.Frame(self, bg="white")
        form_frame.pack(pady=10, fill="x")

        for i, col in enumerate(self.columns):
            tk.Label(form_frame, text=col, bg="white", font=("Segoe UI", 11)).grid(row=i, column=0, sticky="w")
            entry = tk.Entry(form_frame, font=("Segoe UI", 11))
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.entries[col] = entry

        form_frame.columnconfigure(1, weight=1)

        # Pulsanti aggiungi/modifica/cancella
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Aggiungi", command=self.add, font=("Segoe UI", 11)).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Modifica", command=self.edit, font=("Segoe UI", 11)).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancella", command=self.delete, font=("Segoe UI", 11)).pack(side="left", padx=5)

        # Popup filter solo se richiesto
        self.use_popup_filter = use_popup_filter
        self.col_filters = {}  # colonna -> filtro selezionato o None per tutti

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), foreground="black")
        style.configure("Treeview",
                        font=("Segoe UI", 11),
                        background="white",
                        foreground="black",
                        fieldbackground="white",
                        bordercolor="#555555",
                        borderwidth=1,
                        rowheight=26)
        style.map("Treeview", background=[('selected', '#347083')])

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", style="Treeview")
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=140)  # allinea a sinistra
            if self.use_popup_filter:
                # collega click heading a filtro popup
                self.tree.heading(col, command=lambda c=col: self.show_popup_filter(c))
        self.tree.pack(expand=True, fill="both", pady=10)

        # Abilita linee orizzontali e verticali grigie scure (tramite style)
        self.tree["show"] = "headings"  # già impostato
        # Aggiungiamo bordi tramite tag rows
        self.tree.tag_configure('oddrow', background='#f9f9f9')
        self.tree.tag_configure('evenrow', background='white')

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.load()

    def add(self):
        record = {k: self.entries[k].get().strip() for k in self.columns}
        if "Prezzo" in record:
            val = record["Prezzo"].replace("€", "").strip()
            if val:
                record["Prezzo"] = f"{val} €"
            else:
                record["Prezzo"] = ""
        self.data.append(record)
        self.save()
        self.refresh()
        self.clear_entries()

    def edit(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Selezione", "Seleziona un elemento da modificare.")
            return
        idx = self.tree.index(sel[0])
        record = {k: self.entries[k].get().strip() for k in self.columns}
        if "Prezzo" in record:
            val = record["Prezzo"].replace("€", "").strip()
            if val:
                record["Prezzo"] = f"{val} €"
            else:
                record["Prezzo"] = ""
        self.data[idx] = record
        self.save()
        self.refresh()
        self.clear_entries()

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Selezione", "Seleziona un elemento da cancellare.")
            return
        idx = self.tree.index(sel[0])
        del self.data[idx]
        self.save()
        self.refresh()
        self.clear_entries()

    def refresh(self):
        # Applica filtro su dati completi e mostra quelli filtrati
        self.apply_filter()

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list) and all(isinstance(r, dict) for r in loaded):
                        self.data = loaded
            except Exception as e:
                messagebox.showerror("Errore", f"Errore caricando {self.file_path}: {e}")
        self.refresh()

    def on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        for k in self.columns:
            val = self.data[idx].get(k, "")
            if k == "Prezzo":
                val = val.replace(" €", "")
            self.entries[k].delete(0, tk.END)
            self.entries[k].insert(0, val)

    def apply_filter(self):
        # Filtra self.data secondo self.col_filters
        self.filtered_data = []
        for record in self.data:
            match = True
            for col, filt in self.col_filters.items():
                val = record.get(col, "")
                if col == "Prezzo":
                    val = val.replace(" €", "")
                if filt is not None:
                    if str(val) != filt:
                        match = False
                        break
            if match:
                self.filtered_data.append(record)

        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.filtered_data):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=[row.get(c, "") for c in self.columns], tags=(tag,))

    def clear_entries(self):
        for ent in self.entries.values():
            ent.delete(0, tk.END)

    def show_popup_filter(self, col):
        # Crea menu popup con valori univoci più opzione "Tutti"
        values = set()
        for r in self.data:
            val = r.get(col, "")
            if col == "Prezzo":
                val = val.replace(" €", "")
            values.add(str(val))
        values = sorted(values)

        menu = tk.Menu(self, tearoff=0)
        def set_filter(v):
            if v == "(Tutti)":
                self.col_filters[col] = None
            else:
                self.col_filters[col] = v
            self.apply_filter()
        menu.add_command(label="(Tutti)", command=lambda: set_filter("(Tutti)"))
        for v in values:
            menu.add_command(label=v, command=lambda val=v: set_filter(val))

        # Posiziona il menu sotto l'intestazione cliccata
        heading_id = self.columns.index(col)
        x_col = 0
        for i in range(heading_id):
            x_col += self.tree.column(self.columns[i], option='width')
        x_root = self.tree.winfo_rootx() + x_col
        y_root = self.tree.winfo_rooty() + 25  # sotto intestazione

        try:
            menu.tk_popup(x_root, y_root)
        finally:
            menu.grab_release()


class StatisticheFrame(tk.Frame):
    def __init__(self, parent, archivio_frame):
        super().__init__(parent, bg="white")
        self.archivio_frame = archivio_frame

        tk.Label(self, text="Statistiche Quantità Archivio", bg="white", font=("Segoe UI", 14, "bold")).pack(pady=10)

        filter_frame = tk.Frame(self, bg="white")
        filter_frame.pack(pady=5)

        tk.Label(filter_frame, text="Anno:", bg="white", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", padx=5)
        self.anno_var = tk.StringVar()
        self.anno_cb = ttk.Combobox(filter_frame, textvariable=self.anno_var, font=("Segoe UI", 11), state="readonly")
        self.anno_cb.grid(row=0, column=1, sticky="ew", padx=5)

        tk.Label(filter_frame, text="Mese:", bg="white", font=("Segoe UI", 11)).grid(row=0, column=2, sticky="w", padx=5)
        self.mese_var = tk.StringVar()
        self.mese_cb = ttk.Combobox(filter_frame, textvariable=self.mese_var, font=("Segoe UI", 11), state="readonly")
        self.mese_cb.grid(row=0, column=3, sticky="ew", padx=5)

        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)

        tk.Button(self, text="Mostra Report", command=self.mostra_report, font=("Segoe UI", 11)).pack(pady=10)

        self.report_text = tk.Text(self, height=15, font=("Segoe UI", 11))
        self.report_text.pack(fill="both", expand=True, padx=10, pady=10)

        self.carica_anni_mesi()

    def carica_anni_mesi(self):
        anni = set()
        mesi = set()
        for r in self.archivio_frame.data:
            d = r.get("Data", "")
            try:
                dt = datetime.strptime(d, "%d-%m-%Y")
                anni.add(dt.year)
                mesi.add(dt.month)
            except:
                continue
        anni = sorted(list(anni))
        mesi = sorted(list(mesi))

        self.anno_cb['values'] = ["Tutti"] + [str(a) for a in anni]
        self.anno_cb.current(0)
        self.mese_cb['values'] = ["Tutti"] + [str(m).zfill(2) for m in mesi]
        self.mese_cb.current(0)

    def mostra_report(self):
        anno_sel = self.anno_var.get()
        mese_sel = self.mese_var.get()

        tot_quantita = 0
        righe = []

        for r in self.archivio_frame.data:
            d = r.get("Data", "")
            try:
                dt = datetime.strptime(d, "%d-%m-%Y")
            except:
                continue

            if (anno_sel != "Tutti" and str(dt.year) != anno_sel):
                continue
            if (mese_sel != "Tutti" and str(dt.month).zfill(2) != mese_sel):
                continue
            q = r.get("Quantità", "0")
            try:
                q_int = int(q)
            except:
                q_int = 0
            tot_quantita += q_int
            righe.append(f"{d} - {r.get('Nome','')} - Quantità: {q_int}")

        report = f"Report per anno: {anno_sel}, mese: {mese_sel}\n\n"
        report += "\n".join(righe)
        report += f"\n\nTotale quantità: {tot_quantita}"

        self.report_text.delete("1.0", tk.END)
        self.report_text.insert(tk.END, report)


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestione Archivio")
        self.geometry("1100x650")
        self.configure(bg="white")

        menu_frame = tk.Frame(self, bg="#3498db")
        menu_frame.pack(side="left", fill="y")

        self.content_frame = tk.Frame(self, bg="white")
        self.content_frame.pack(side="left", fill="both", expand=True)

        self.archivio_frame = FilterableFrame(self.content_frame, FILE_ARCHIVIO,
                                              ["Nome", "Descrizione", "Data", "Categoria", "Quantità", "Prezzo"],
                                              use_popup_filter=True)
        self.clienti_frame = FilterableFrame(self.content_frame, FILE_CLIENTI,
                                            ["Nome", "Email", "Telefono", "Indirizzo", "Comune"])
        self.statistiche_frame = StatisticheFrame(self.content_frame, self.archivio_frame)
        self.consegne_frame = FilterableFrame(self.content_frame, FILE_CONSEGNE,
                                              ["Data", "Cliente", "Descrizione", "Quantità"])

        buttons = [
            ("Archivio", self.show_archivio),
            ("Clienti", self.show_clienti),
            ("Statistiche", self.show_statistiche),
            ("Consegne", self.show_consegne),
            ("Aggiorna", self.refresh_all),
            ("Salva Excel", self.save_excel),
            ("Importa Archivio da Excel", self.importa_archivio_excel)
        ]

        for text, cmd in buttons:
            tk.Button(menu_frame, text=text, width=22, bg="#2980b9", fg="white", font=("Segoe UI", 11), command=cmd).pack(pady=5)

        self.show_archivio()

    def _clear(self):
        for widget in self.content_frame.winfo_children():
            widget.pack_forget()

    def show_archivio(self):
        self._clear()
        self.archivio_frame.pack(fill="both", expand=True)

    def show_clienti(self):
        self._clear()
        self.clienti_frame.pack(fill="both", expand=True)

    def show_statistiche(self):
        self._clear()
        self.statistiche_frame.pack(fill="both", expand=True)
        self.statistiche_frame.carica_anni_mesi()

    def show_consegne(self):
        self._clear()
        self.consegne_frame.pack(fill="both", expand=True)

    def refresh_all(self):
        self.archivio_frame.load()
        self.clienti_frame.load()
        self.consegne_frame.load()
        messagebox.showinfo("Aggiornato", "Dati ricaricati con successo.")

    def save_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel file", "*.xlsx")])
        if not path:
            return
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame(self.archivio_frame.data).to_excel(writer, sheet_name="Archivio", index=False)
            pd.DataFrame(self.clienti_frame.data).to_excel(writer, sheet_name="Clienti", index=False)
            pd.DataFrame(self.consegne_frame.data).to_excel(writer, sheet_name="Consegne", index=False)
        messagebox.showinfo("Salvato", f"Dati salvati in {path}")

    def importa_archivio_excel(self):
        file_path = filedialog.askopenfilename(title="Seleziona file Excel archivio", filetypes=[("Excel files", "*.xlsx *.xls")])
        if not file_path:
            return
        try:
            df = pd.read_excel(file_path, sheet_name="Archivio")
            colonne_richieste = {"Nome", "Descrizione", "Data", "Categoria", "Quantità", "Prezzo"}
            if not colonne_richieste.issubset(df.columns):
                messagebox.showerror("Errore", f"Il file Excel deve contenere le colonne: {', '.join(colonne_richieste)}")
                return
            dati_nuovi = []
            for _, r in df.iterrows():
                prezzo = str(r["Prezzo"]).strip()
                if prezzo and not prezzo.endswith("€"):
                    prezzo += " €"
                dati_nuovi.append({
                    "Nome": str(r["Nome"]),
                    "Descrizione": str(r["Descrizione"]),
                    "Data": str(r["Data"]),
                    "Categoria": str(r["Categoria"]),
                    "Quantità": int(r["Quantità"]),
                    "Prezzo": prezzo,
                })
            self.archivio_frame.data = dati_nuovi
            self.archivio_frame.save()
            self.archivio_frame.refresh()
            messagebox.showinfo("Importazione", "Archivio importato con successo da Excel.")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante importazione Excel: {e}")


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()



