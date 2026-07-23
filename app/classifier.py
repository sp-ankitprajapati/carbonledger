"""
classifier.py
-------------
A genuine feedforward neural network (Multi-Layer Perceptron) that takes
free-text line items from invoices/expense reports ("diesel generator fuel
purchase invoice") and classifies them into one of the emission activity
categories defined in emission_factors.py ("diesel_litre").

Pipeline: TF-IDF text vectorization -> MLPClassifier (neural network with
hidden layers + backprop, trained via sklearn's implementation of
stochastic gradient-based optimization).

Why this design instead of calling an LLM for every line item:
  - Cost: classifying thousands of supplier line items via LLM API calls
    is slow and expensive at scale; a trained local classifier is near-free
    and millisecond-fast at inference time.
  - This is also the realistic production pattern at companies like
    Watershed/Persefoni: cheap local models triage/classify the bulk of
    data, expensive LLM calls are reserved for ambiguous cases (see
    agent.py for how the agent falls back to Gemini when confidence is low).
"""

import json
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "line_item_classifier.joblib")
TRAINING_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "training_data.json")

CONFIDENCE_THRESHOLD = 0.55  # below this, agent.py escalates to Gemini for review


def load_training_data():
    with open(TRAINING_DATA_PATH) as f:
        data = json.load(f)
    texts = [d["text"] for d in data]
    labels = [d["label"] for d in data]
    return texts, labels


def train_classifier(save: bool = True) -> Pipeline:
    texts, labels = load_training_data()

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")),
        ("nn", MLPClassifier(
            hidden_layer_sizes=(64, 32),   # two hidden layers -> real neural network
            activation="relu",
            solver="adam",
            max_iter=2000,
            random_state=42,
        )),
    ])

    pipeline.fit(texts, labels)

    if save:
        joblib.dump(pipeline, MODEL_PATH)

    return pipeline


def load_classifier() -> Pipeline:
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return train_classifier(save=True)


def classify_line_item(text: str, model: Pipeline = None) -> dict:
    """Returns predicted activity_key, confidence score, and whether it
    needs escalation to the LLM agent for manual/AI review."""
    if model is None:
        model = load_classifier()

    proba = model.predict_proba([text])[0]
    classes = model.classes_
    best_idx = proba.argmax()
    predicted_label = classes[best_idx]
    confidence = float(proba[best_idx])

    return {
        "text": text,
        "predicted_activity_key": predicted_label,
        "confidence": round(confidence, 3),
        "needs_llm_review": confidence < CONFIDENCE_THRESHOLD,
    }


if __name__ == "__main__":
    model = train_classifier(save=True)
    test_cases = [
        "diesel fuel bill for backup generator at plant",
        "invoice for cotton fabric supplier payment",
        "monthly DISCOM electricity invoice",
        "weird ambiguous line item about office supplies",  # should trigger low confidence
    ]
    for t in test_cases:
        result = classify_line_item(t, model)
        print(result)
