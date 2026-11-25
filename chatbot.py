"""Loads the trained model and answers messages."""
import csv, json, random, re, time
from pathlib import Path

import joblib

BASE = Path(__file__).parent
MODEL_PATH = BASE / "model" / "chatbot_model.joblib"
INTENTS_PATH = BASE / "data" / "intents.json"
UNKNOWN_LOG = BASE / "logs" / "unknown_queries.csv"
CONFIDENCE_THRESHOLD = 0.35


def clean(text):
    text = re.sub(r"[^a-z0-9+#\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


class ChatBot:
    def __init__(self):
        self.reload()

    def reload(self):
        self.model = joblib.load(MODEL_PATH)
        data = json.loads(INTENTS_PATH.read_text(encoding="utf-8"))["intents"]
        self.intents = {i["tag"]: i for i in data}

    def reply(self, message):
        text = clean(message)
        if not text:
            return {"reply": "Please type something.", "intent": None, "confidence": 0}
        probs = self.model.predict_proba([text])[0]
        idx = int(probs.argmax())
        tag, conf = self.model.classes_[idx], float(probs[idx])

        if conf < CONFIDENCE_THRESHOLD:
            self._log_unknown(message, tag, conf)
            return {
                "reply": "Sorry, I'm not sure about that yet. Try asking about eligibility, resume, interview, aptitude, salary or companies. (I've saved your question so my trainer can teach me.)",
                "intent": "unknown", "confidence": round(conf, 3), "action": None,
            }
        intent = self.intents[tag]
        return {
            "reply": random.choice(intent["responses"]),
            "intent": tag, "confidence": round(conf, 3), "action": intent.get("action"),
        }

    def _log_unknown(self, message, guess, conf):
        new = not UNKNOWN_LOG.exists()
        UNKNOWN_LOG.parent.mkdir(exist_ok=True)
        with open(UNKNOWN_LOG, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["time", "message", "best_guess", "confidence"])
            w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), message, guess, round(conf, 3)])
