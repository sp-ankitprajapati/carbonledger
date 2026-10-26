"""Exploratory stratified CV on the small synthetic training corpus; no LLM calls."""

from pathlib import Path
import argparse
import json
import numpy as np
from sklearn.base import clone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score
from app.classifier import load_training_data, CONFIDENCE_THRESHOLD


def evaluate():
    texts, labels = load_training_data()
    texts, labels = np.asarray(texts), np.asarray(labels)
    folds = min(3, int(np.unique(labels, return_counts=True)[1].min()))
    if folds < 2:
        raise ValueError(
            "Every class needs at least two examples for stratified evaluation"
        )
    rows = []
    for name, estimator in [
        (
            "mlp",
            MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=2000, random_state=42),
        ),
        ("logistic_regression", LogisticRegression(max_iter=2000, random_state=42)),
    ]:
        predicted = np.empty(len(labels), dtype=object)
        confidence = np.zeros(len(labels))
        for train, test in StratifiedKFold(folds, shuffle=True, random_state=42).split(
            texts, labels
        ):
            model = Pipeline(
                [
                    (
                        "tfidf",
                        TfidfVectorizer(ngram_range=(1, 2), stop_words="english"),
                    ),
                    ("classifier", clone(estimator)),
                ]
            )
            model.fit(texts[train], labels[train])
            probability = model.predict_proba(texts[test])
            predicted[test] = model.classes_[probability.argmax(axis=1)]
            confidence[test] = probability.max(axis=1)
        accepted = confidence >= CONFIDENCE_THRESHOLD
        rows.append(
            {
                "model": name,
                "n_samples": len(labels),
                "accuracy": float(accuracy_score(labels, predicted)),
                "macro_f1": float(f1_score(labels, predicted, average="macro")),
                "threshold": CONFIDENCE_THRESHOLD,
                "fraction_accepted_locally": float(accepted.mean()),
                "accepted_accuracy": float(
                    accuracy_score(labels[accepted], predicted[accepted])
                )
                if accepted.any()
                else None,
            }
        )
    return {
        "design": f"{folds}-fold stratified CV, seed42; vectorizer fits each training fold only",
        "limitations": "48 synthetic examples across15 classes. No independent invoice holdout or live LLM benchmark. Confidence uncalibrated. Not evidence of90% API savings.",
        "models": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/classifier_cv.json")
    args = parser.parse_args()
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(evaluate(), indent=2, allow_nan=False) + "\n")
    print(f"Saved {p}")
