"""
Script one-shot : génère un refresh token Dropbox permanent.
À lancer UNE SEULE FOIS sur ton PC, puis supprimer.
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from dropbox import DropboxOAuth2FlowNoRedirect
except ImportError:
    sys.exit("Installe dropbox d'abord : pip install dropbox")

print("""
=== Génération du refresh token Dropbox ===

Tu as besoin de l'App Key et l'App Secret de ton app Dropbox.
Trouve-les sur : https://www.dropbox.com/developers/apps
-> Clique sur ton app 'second-cerveau-bot' -> onglet Settings
""")

app_key    = input("App Key    : ").strip()
app_secret = input("App Secret : ").strip()

auth_flow = DropboxOAuth2FlowNoRedirect(
    app_key,
    app_secret,
    token_access_type="offline",
)

url = auth_flow.start()
print(f"\n1. Ouvre cette URL dans ton navigateur :\n   {url}")
print("\n2. Autorise l'app et copie le code affiché.")
code = input("\nColle le code ici : ").strip()

try:
    result = auth_flow.finish(code)
    print(f"""
=== SUCCÈS ===

Ajoute ces 3 variables dans Railway (et supprime DROPBOX_ACCESS_TOKEN) :

  DROPBOX_APP_KEY      = {app_key}
  DROPBOX_APP_SECRET   = {app_secret}
  DROPBOX_REFRESH_TOKEN = {result.refresh_token}

Tu peux supprimer ce script ensuite.
""")
except Exception as e:
    print(f"\nErreur : {e}")
