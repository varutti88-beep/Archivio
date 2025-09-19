import json
import os

class StatisticheManager:
    def __init__(self,
                 file_clienti="clienti.json",
                 file_prodotti="prodotti.json",
                 file_consegne="consegne.json",
                 file_stoccaggio="stoccaggio.json"):

        self.file_clienti = file_clienti
        self.file_prodotti = file_prodotti
        self.file_consegne = file_consegne
        self.file_stoccaggio = file_stoccaggio

        # Caricamento iniziale dei dati
        self.clienti = self._load_json(file_clienti)
        self.prodotti = self._load_json(file_prodotti)
        self.consegne = self._load_json(file_consegne)
        self.stoccaggio = self._load_json(file_stoccaggio)

    # -------------------- Utility --------------------
    def _load_json(self, path: str):
        """Carica un file JSON in lista di dict"""
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _to_float(self, value, default=0.0) -> float:
        try:
            return float(str(value).replace(",", "."))
        except Exception:
            return default

    def _to_int(self, value, default=0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    # -------------------- Calcoli --------------------
    def totale_clienti(self) -> int:
        return len(self.clienti)

    def totale_spesa_prodotti(self) -> float:
        totale = 0.0
        for p in self.prodotti:
            prezzo = self._to_float(p.get("Prezzo", 0))
            quantita = self._to_float(p.get("Quantità", 1))
            totale += prezzo * quantita
        return totale

    def totale_guadagno_consegne(self) -> float:
        totale = 0.0
        for c in self.consegne:
            prezzo = self._to_float(c.get("Prezzo", 0))
            totale += prezzo
        return totale

    def totale_stoccaggio(self) -> int:
        return len(self.stoccaggio)

    # -------------------- Riepilogo --------------------
    def riepilogo(self) -> dict:
        return {
            "Totale Clienti": self.totale_clienti(),
            "Totale Spesa Prodotti": f"{self.totale_spesa_prodotti():.2f} €",
            "Totale Guadagno Consegne": f"{self.totale_guadagno_consegne():.2f} €",
            "Totale Merce in Stoccaggio": self.totale_stoccaggio()
        }


