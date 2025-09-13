import shutil
import os

def aggiungi_documento(percorso_file, cartella_destinazione="documenti"):
    """
    Aggiunge un documento esterno alla cartella dell'applicazione.
    """
    # Crea la cartella destinazione se non esiste
    if not os.path.exists(cartella_destinazione):
        os.makedirs(cartella_destinazione)

    # Nome del file
    nome_file = os.path.basename(percorso_file)

    # Percorso completo del nuovo file
    nuovo_percorso = os.path.join(cartella_destinazione, nome_file)

    # Copia il file
    shutil.copy2(percorso_file, nuovo_percorso)

    print(f"Documento '{nome_file}' aggiunto in '{cartella_destinazione}'.")

    return nuovo_percorso
