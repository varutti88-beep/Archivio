import os
import json

files = [
    "clienti.json",
    "consegne.json",
    "prodotti.json",
    "note.json",
    "stoccaggio.json"
]

def check_file(file):
    if not os.path.exists(file):
        print(f"{file}: non esiste, lo creo vuoto.")
        with open(file, "w", encoding="utf-8") as f:
            f.write("[]")
        return

    try:
        with open(file, "r", encoding="utf-8") as f:
            json.load(f)
        print(f"{file}: file JSON valido.")
    except Exception as e:
        print(f"{file}: file corrotto o non valido. Resetto a vuoto.")
        with open(file, "w", encoding="utf-8") as f:
            f.write("[]")

if __name__ == "__main__":
    for f in files:
        check_file(f)
    print("Controllo completato.")
