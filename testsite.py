from flask import Flask, abort
import time

app = Flask(__name__)

@app.route("/")
def home():
    return "Site AutoFixer OK"

@app.route("/error500")
def error_500():
    abort(500)  # Erreur interne serveur

@app.route("/error403")
def error_403():
    abort(403)  # Accès interdit

@app.route("/error404")
def error_404():
    abort(404)  # Page non trouvée

@app.route("/timeout")
def timeout():
    time.sleep(10)  # délai long pour simuler timeout
    return "Timeout simulé"

if __name__ == "__main__":
    app.run(debug=False, port=15650, host="0.0.0.0")



# fait en sorte que je peux declencher chaque erreur que je veux parmi celle ecrite dans ce code pour que lors de la demo dans la soutenance je peux simuler differente erreur gpt  

