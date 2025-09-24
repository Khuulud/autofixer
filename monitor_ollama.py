import os, sys, time, json, requests

SITE = os.environ.get("SITE_URL", "http://127.0.0.1:15650")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "mistral:latest")  
TIMEOUT = 5
CHECKS = [
    "/",             # doit répondre 200
    "/error500",     # simule 500
    "/error404",     # simule 404
    "/timeout",      # simule délai dépassé
]

def probe(url):
    try:
        r = requests.get(url, timeout=TIMEOUT)
        return {"url": url, "status": r.status_code, "ok": (200 <= r.status_code < 300), "error": None}
    except requests.exceptions.ReadTimeout:
        return {"url": url, "status": None, "ok": False, "error": f"Read timed out. (read timeout={TIMEOUT})"}
    except requests.exceptions.RequestException as e:
        return {"url": url, "status": None, "ok": False, "error": str(e)}

def choose_worst(results):
    # Priorité des problèmes
    order = {
        "timeout": 100,
        "server_error": 90,   # 5xx
        "not_found": 40,      # 404
        "ok": 0
    }
    worst = None
    for r in results:
        if r["ok"]:
            score = order["ok"]
        elif r["error"] and "timed out" in r["error"].lower():
            score = order["timeout"]
        elif r["status"] and 500 <= r["status"] <= 599:
            score = order["server_error"]
        elif r["status"] == 404:
            score = order["not_found"]
        else:
            score = 50  # inconnu

        tag = {"score": score, "data": r}
        if (worst is None) or (score > worst["score"]):
            worst = tag
    return worst

SYSTEM = (
    "Tu es un assistant SRE. "
    "On te fournit l'état de plusieurs URLs d'un service local. "
    "Réponds STRICTEMENT en JSON compact avec une seule clé 'action' parmi: "
    "'restart_flask' si le service semble en panne (timeout, 5xx répétés), sinon 'noop'."
)

def ask_ollama(worst):
    user = {
        "role": "user",
        "content": (
            "Voici le contrôle du service web (une seule synthèse du pire cas):\n"
            + json.dumps(worst, ensure_ascii=False)
            + "\nRappelle-toi: réponds uniquement JSON sous la forme {\"action\":\"restart_flask\"} ou {\"action\":\"noop\"}."
        ),
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            user
        ],
        "stream": False,
        "options": {"temperature": 0.1},
        "format": "json",  # demande à Ollama un JSON
    }
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    # Suivant la version d’Ollama/modèle, le champ peut être "message" -> "content"
    content = data.get("message", {}).get("content", "") or data.get("content", "")
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and parsed.get("action") in ("restart_flask", "noop"):
            return parsed
    except Exception:
        pass

    # Sécurité : si non compréhensible mais gros souci détecté, on force restart
    return {"action": "restart_flask" if worst and worst["score"] >= 90 else "noop"}

def main():
    print("── Début d'un cycle ──")
    results = [probe(SITE + path) for path in CHECKS]
    print("Checks:", results)

    worst = choose_worst(results)
    decision = ask_ollama(worst)
    print("IA:", decision)

    if decision.get("action") == "restart_flask":
        print("IA: redémarrage demandé")
        sys.exit(1)  # échec volontaire -> déclenche le job suivant dans Jenkins
    else:
        print("IA: tout va bien (noop)")
        sys.exit(0)  # succès -> aucune action

if __name__ == "__main__":
    main()