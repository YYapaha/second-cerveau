import sys
import time
import logging
from pathlib import Path

# Force UTF-8 sur Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from capture import detecter_type, recuperer_contenu, analyser_contenu, sauvegarder_fiche

INBOX_DIR = Path(__file__).parent / "inbox"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
)

EXTENSIONS_SUPPORTEES = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".ogg", ".m4a", ".md", ".txt"}


class InboxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        chemin = Path(event.src_path)
        if chemin.suffix.lower() not in EXTENSIONS_SUPPORTEES:
            print(f"⏭️  Ignoré (format non supporté) : {chemin.name}")
            return

        # Attendre que le fichier soit complètement écrit
        time.sleep(1)

        print(f"\n📥 Nouveau fichier détecté : {chemin.name}")
        try:
            type_entree = detecter_type(str(chemin))
            contenu = recuperer_contenu(str(chemin), type_entree)
            fiche_md = analyser_contenu(contenu, str(chemin))
            sauvegarder_fiche(fiche_md, str(chemin))
        except Exception as e:
            print(f"❌ Erreur lors du traitement de {chemin.name} : {e}")


def main():
    INBOX_DIR.mkdir(exist_ok=True)
    print(f"👀 Watchdog démarré — surveillance de : {INBOX_DIR}")
    print("   Déposez un fichier dans ce dossier pour le capturer automatiquement.")
    print("   Ctrl+C pour arrêter.\n")

    handler = InboxHandler()
    observer = Observer()
    observer.schedule(handler, str(INBOX_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 Watchdog arrêté.")
    observer.join()


if __name__ == "__main__":
    main()
