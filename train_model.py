"""
Trains the chatbot's intent-classification model FROM SCRATCH on data/intents.json.

Pipeline:  text -> TF-IDF (word 1-2 grams + character 2-5 grams, so spelling mistakes still work)
                -> Logistic Regression classifier

Run:  python train_model.py
Output: model/chatbot_model.joblib  and  model/metrics.json
"""
import json, re, time
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

BASE = Path(__file__).parent
DATA = BASE / "data" / "intents.json"
MODEL = BASE / "model" / "chatbot_model.joblib"
METRICS = BASE / "model" / "metrics.json"


def clean(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_dataset():
    with open(DATA, encoding="utf-8") as f:
        intents = json.load(f)["intents"]
    X, y = [], []
    for intent in intents:
        for pattern in intent["patterns"]:
            X.append(clean(pattern))
            y.append(intent["tag"])
    return X, y


PREFIXES = ["", "", "please ", "can you tell me ", "i want to know ", "tell me ", "sir ", "bro ", "hey "]
SUFFIXES = ["", "", " please", " ?", " pls", " in placement"]


def augment(X, y):
    """Cheap data augmentation: wrap each sentence in common conversational phrasing.
    Applied ONLY to training data so the test score stays honest."""
    X2, y2 = [], []
    for text, label in zip(X, y):
        for pre in PREFIXES:
            for suf in SUFFIXES[:3]:
                X2.append(clean(pre + text + suf))
                y2.append(label)
    pairs = list(dict.fromkeys(zip(X2, y2)))   # drop duplicates
    return [p[0] for p in pairs], [p[1] for p in pairs]


def build_pipeline():
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
    ])
    clf = LogisticRegression(C=20, max_iter=3000)
    return Pipeline([("features", features), ("clf", clf)])


def train():
    X, y = load_dataset()
    print(f"Dataset: {len(X)} training sentences, {len(set(y))} intents")

    # Intents with fewer than 4 sentences (e.g. a brand-new one you just taught) are still
    # trained on, but left out of the accuracy estimate because they can't be split fairly.
    from collections import Counter
    counts = Counter(y)
    keep = [i for i, label in enumerate(y) if counts[label] >= 4]
    Xe, ye = [X[i] for i in keep], [y[i] for i in keep]

    # 1) Honest evaluation: hold out 20% the model never sees
    X_tr, X_te, y_tr, y_te = train_test_split(Xe, ye, test_size=0.2, random_state=42, stratify=ye)
    Xa, ya = augment(X_tr, y_tr)
    eval_model = build_pipeline().fit(Xa, ya)
    test_acc = accuracy_score(y_te, eval_model.predict(X_te))

    # 2) 3-fold cross-validation (every class has >= 9 samples)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    scores = []
    for tr, te in cv.split(Xe, ye):
        Xa, ya = augment([Xe[i] for i in tr], [ye[i] for i in tr])
        m = build_pipeline().fit(Xa, ya)
        scores.append(accuracy_score([ye[i] for i in te], m.predict([Xe[i] for i in te])))
    import numpy as np
    cv_scores = np.array(scores)

    print(f"Hold-out test accuracy : {test_acc:.2%}")
    print(f"3-fold CV accuracy     : {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")
    print("\nPer-intent report (hold-out set):")
    print(classification_report(y_te, eval_model.predict(X_te), zero_division=0))

    # 3) Final model uses ALL data
    t0 = time.time()
    Xa, ya = augment(X, y)
    final = build_pipeline().fit(Xa, ya)
    MODEL.parent.mkdir(exist_ok=True)
    joblib.dump(final, MODEL)

    metrics = {
        "samples": len(X),
        "intents": len(set(y)),
        "test_accuracy": round(test_acc, 4),
        "cv_accuracy": round(float(cv_scores.mean()), 4),
        "algorithm": "TF-IDF (word + char n-grams) + Logistic Regression",
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "train_seconds": round(time.time() - t0, 2),
    }
    METRICS.write_text(json.dumps(metrics, indent=2))
    print(f"Saved model -> {MODEL}")
    return metrics


if __name__ == "__main__":
    train()
