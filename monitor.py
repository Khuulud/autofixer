import requests
import time
from ollama import chat
from requests.auth import HTTPBasicAuth

print("✅ Script monitor.py lancé avec succès.")

SITE_URL = "http://127.0.0.1:5000/"
CHECK_INTERVAL = 10  

# === JENKINS ===
JENKINS_URL = "http://localhost:8080/job/RestartFlask/build"
JENKINS_USER = "admin"
JENKINS_TOKEN = "11fbd68950652cdc4b502c0ca8c4fe189b"  

# === GITLAB ===
GITLAB_PROJECT_ID = "72534612"  
GITLAB_API_URL = f"https://gitlab.com/api/v4/projects/{GITLAB_PROJECT_ID}/issues"
GITLAB_TOKEN = "glpat-lgCSLhpf1gYNpJtnFmYl4W86MQp1OmhreHdmCw.01.120dv9q62"

# === FICHIER LOG ===
LOG_FILE = "autofixer.log"

# === ANALYSE IA ===
def analyser_erreur(code):
    if code == 403:
        message = "Le site répond avec un code 403. Pourquoi un site peut-il retourner ce code ?"
    elif code == 500:
        message = "Le site répond avec une erreur 500. Quelles sont les causes possibles ?"
    else:
        message = f"Le site a retourné le code {code}. Quelle est la cause possible ?"

    print("🤖 Appel à l'IA pour analyser le problème...")
    try:
        reponse = chat(model="mistral", messages=[
            {"role": "user", "content": message}
        ])
        return reponse['message']['content']
    except Exception as e:
        return f"Erreur de communication avec l'IA : {e}"

# === JOB JENKINS ===
def redemarrer_jenkins():
    print("🚀 Déclenchement du job Jenkins : RestartFlask")
    try:
        response = requests.post(JENKINS_URL, auth=HTTPBasicAuth(JENKINS_USER, JENKINS_TOKEN))
        if response.status_code == 201:
            print("✅ Job Jenkins déclenché avec succès.")
        else:
            print(f"❌ Erreur Jenkins : {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Échec Jenkins : {e}")

# === TICKET GITLAB ===
def creer_ticket_gitlab(titre, description):
    headers = {
        "PRIVATE-TOKEN": GITLAB_TOKEN
    }
    data = {
        "title": titre,
        "description": description
    }

    try:
        response = requests.post(GITLAB_API_URL, headers=headers, data=data)
        if response.status_code == 201:
            print("📌 Ticket GitLab créé avec succès.")
        else:
            print(f"❌ Échec création ticket GitLab : {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Exception lors de la création du ticket GitLab : {e}")

# === LOG LOCAL ===
def enregistrer_log(message):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        print(f"❌ Impossible d’écrire dans le fichier log : {e}")

def surveiller_site():
    DUREE_MAX = 5 * 60  # 5 minutes = 300 secondes
    start_time = time.time()

    while time.time() - start_time < DUREE_MAX:
        print("\n🔄 Nouvelle boucle de surveillance")
        print("🔎 Vérification de l'état du site...")

        try:
            response = requests.get(SITE_URL)
            code = response.status_code

            if code == 200:
                print("✅ Le site fonctionne correctement.")
                enregistrer_log("Site OK")
            else:
                print(f"⚠️ Le site répond mais avec le code : {code}")
                analyse = analyser_erreur(code)
                print("📄 Réponse de l'IA :")
                print(analyse)
                enregistrer_log(f"Erreur détectée : {code} - IA : {analyse}")

                if any(mot in analyse.lower() for mot in ["serveur", "inaccessible", "erreur", "indisponible"]):
                    print("🧠 Mot-clé détecté → lancement réparation Jenkins")
                    redemarrer_jenkins()

                    titre = f"Incident détecté – Code {code}"
                    description = (
                        f"🔎 Une erreur a été détectée lors de la surveillance du site.\n"
                        f"➡️ Code HTTP retourné : **{code}**\n"
                        f"🧠 Réponse IA :\n```\n{analyse}\n```\n"
                        f"🔁 Action corrective : redémarrage automatique via Jenkins.\n"
                        f"🕒 Heure : {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    creer_ticket_gitlab(titre, description)

        except Exception as e:
            message = f"❌ Exception détectée : {e}"
            print(message)
            enregistrer_log(message)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    surveiller_site()