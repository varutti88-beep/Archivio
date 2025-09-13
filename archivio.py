import pandas as pd

# Lista per salvare i dati
dati = []

def inserisci_dato():
    nome = input("Nome: ")
    data = input("Data (YYYY-MM-DD): ")
    descrizione = input("Descrizione: ")
    dati.append({
        "Nome": nome,
        "Data": data,
        "Descrizione": descrizione
    })
    print("Dati salvati!\n")

def visualizza_dati():
    if not dati:
        print("Nessun dato inserito.")
        return
    for i, record in enumerate(dati, start=1):
        print(f"{i}. {record}")

def esporta_excel():
    if not dati:
        print("Nessun dato da esportare.")
        return
    df = pd.DataFrame(dati)
    df.to_excel("dati_archiviati.xlsx", index=False)
    print("Esportazione completata! File: dati_archiviati.xlsx")

def menu():
    while True:
        print("\n--- Menu ---")
        print("1. Inserisci dato")
        print("2. Visualizza dati")
        print("3. Esporta su Excel")
        print("4. Esci")

        scelta = input("Scegli un'opzione: ")

        if scelta == "1":
            inserisci_dato()
        elif scelta == "2":
            visualizza_dati()
        elif scelta == "3":
            esporta_excel()
        elif scelta == "4":
            print("Arrivederci!")
            break
        else:
            print("Scelta non valida.")

if __name__ == "__main__":
    menu()
