# Classifier model card

Task: classify free-text activity descriptions into15 demonstration factor keys. Training corpus:48 synthetic examples, with the smallest class containing only2 examples. Model: TF-IDF unigrams/bigrams plus MLP (64, 32), seed 42, max 2000 iterations. Logistic regression provides a simple baseline.

Evaluation: two-fold stratified CV, seed 42. Each fold fits its own vocabulary and weights. MLP accuracy 0.3958, macro F1 0.3474. At 0.55 confidence,13/48 examples pass the gate and5/13 are correct. Logistic accuracy 0.2083, macro F1 0.1107; no logistic prediction meets0.55. This corpus provides extremely sparse per-class training coverage and no independent invoice generalization estimate.

Current use: category suggestions with human confirmation by default. Explicit structured activity keys bypass the classifier and are labeled provided_activity_key, not ML predictions. An experimental opt-in allows automatic model choices for demonstrations. Confidence is uncalibrated. No 90% API reduction, production reliability or compliance guarantee is established.

The calculation engine remains deterministic, but incorrect category, quantity, unit, boundary or factor assumptions can still produce wrong accounting. Unsupported units are rejected, retrieved candidate membership is enforced, invalid extraction fails visibly, and every accepted/rejected item is recorded. Source factors remain illustrative and unverified for actual disclosures.

Reproduction: `python scripts/evaluate_classifier.py`; exact output and local runtime are under results/. Next work: independently labeled invoices, per-class confusion/error analysis, calibrated abstention, appropriate factors and end-to-end extraction/call-count evaluation. Keep final holdout data separate from routing-threshold selection.
