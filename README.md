# Campus Placement AI Chatbot (own-trained model)

## Run
```
pip install -r requirements.txt
python train_model.py     # trains the model from data/intents.json  (app.py also does this automatically the first time)
python app.py             # open http://127.0.0.1:5000
```

## How the model is "trained by us"
- Dataset: `data/intents.json` (our own sentences grouped by intent)
- Algorithm: TF-IDF (word 1-2 grams + character 2-5 grams) -> Logistic Regression (scikit-learn)
- `train_model.py` trains, evaluates (20% hold-out + 3-fold cross-validation) and saves `model/chatbot_model.joblib`
- If the prediction confidence is below 35%, the bot says it does not know and logs the question to `logs/unknown_queries.csv`
- "Train the model" tab: add a new sentence/intent and retrain from the browser (admin key: `admin123`, change with env var `ADMIN_KEY`)

## New features
1. Resume check - score + missing skills for a chosen role (paste text or upload PDF/TXT)
2. Eligibility checker - company-wise eligibility from CGPA, 10th/12th %, backlogs, branch (`data/companies.json`)
3. Mock aptitude quiz - random questions with scoring and explanations (`data/quiz.json`)

## Files
app.py (Flask API) | chatbot.py (prediction) | train_model.py (training) | features.py (3 features) | data/ | templates/ | static/
