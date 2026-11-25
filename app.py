import csv, io, json, os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import features
import train_model
from chatbot import INTENTS_PATH, UNKNOWN_LOG, ChatBot

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
ADMIN_KEY = os.environ.get("ADMIN_KEY", "admin123")   # change this!
METRICS = Path(__file__).parent / "model" / "metrics.json"

if not (Path(__file__).parent / "model" / "chatbot_model.joblib").exists():
    train_model.train()
bot = ChatBot()


@app.get("/")
def index():
    return render_template("index.html", roles=list(features.ROLES["roles"]),
                           categories=sorted({q["category"] for q in features.QUIZ}))


@app.post("/api/chat")
def chat():
    msg = (request.get_json(silent=True) or {}).get("message", "")
    return jsonify(bot.reply(msg[:500]))


# ---- Feature 1: resume analyzer ----
@app.post("/api/resume")
def resume():
    text, role = "", request.form.get("role") or (request.get_json(silent=True) or {}).get("role")
    f = request.files.get("file")
    if f and f.filename:
        if f.filename.lower().endswith(".pdf"):
            from pypdf import PdfReader
            text = "\n".join((p.extract_text() or "") for p in PdfReader(f).pages)
        else:
            text = f.read().decode("utf-8", errors="ignore")
    else:
        text = request.form.get("text") or (request.get_json(silent=True) or {}).get("text", "")
    if len(text.strip()) < 30:
        return jsonify(error="Please paste or upload your resume text (at least a few lines)."), 400
    try:
        return jsonify(features.analyze_resume(text, role))
    except ValueError as e:
        return jsonify(error=str(e)), 400


# ---- Feature 2: eligibility ----
@app.post("/api/eligibility")
def eligibility():
    d = request.get_json(silent=True) or {}
    try:
        res = features.check_eligibility(float(d["cgpa"]), float(d["tenth"]), float(d["twelfth"]),
                                         int(d["backlogs"]), d["branch"])
    except (KeyError, ValueError, TypeError):
        return jsonify(error="Please fill all fields with valid numbers."), 400
    return jsonify(results=res, eligible_count=sum(r["eligible"] for r in res), total=len(res))


# ---- Feature 3: mock quiz ----
@app.get("/api/quiz")
def quiz():
    return jsonify(questions=features.get_quiz(request.args.get("category"), int(request.args.get("n", 5))))


@app.post("/api/quiz/submit")
def quiz_submit():
    return jsonify(features.grade_quiz((request.get_json(silent=True) or {}).get("answers", {})))


# ---- Train-it-yourself: model info, teach, retrain ----
@app.get("/api/model-info")
def model_info():
    info = json.loads(METRICS.read_text()) if METRICS.exists() else {}
    unknown = []
    if UNKNOWN_LOG.exists():
        unknown = list(csv.DictReader(open(UNKNOWN_LOG, encoding="utf-8")))[-10:]
    info["recent_unknown"] = unknown
    info["intents_list"] = sorted(bot.intents)
    return jsonify(info)


@app.post("/api/teach")
def teach():
    d = request.get_json(silent=True) or {}
    if d.get("key") != ADMIN_KEY:
        return jsonify(error="Wrong admin key."), 403
    sentence, tag = (d.get("sentence") or "").strip(), (d.get("intent") or "").strip()
    if not sentence or not tag:
        return jsonify(error="Sentence and intent are required."), 400
    data = json.loads(INTENTS_PATH.read_text(encoding="utf-8"))
    intent = next((i for i in data["intents"] if i["tag"] == tag), None)
    if intent is None:
        answer = (d.get("answer") or "").strip()
        if not answer:
            return jsonify(error="New intent needs an answer text."), 400
        intent = {"tag": tag, "patterns": [], "responses": [answer]}
        data["intents"].append(intent)
    if sentence not in intent["patterns"]:
        intent["patterns"].append(sentence)
    INTENTS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    metrics = train_model.train()      # retrain on the enlarged dataset
    bot.reload()
    return jsonify(ok=True, metrics=metrics)


if __name__ == "__main__":
    app.run(debug=True)
