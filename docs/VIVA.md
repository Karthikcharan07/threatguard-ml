# Viva questions and answers

## 1. What does ThreatGuard classify?

Labelled network-flow records as normal/attack, or attack categories when selected. It does not inspect raw packets itself.

## 2. What is UNSW-NB15?

An official UNSW intrusion-detection benchmark containing labelled flow features and attack categories. This implementation supports its prepared headered CSV partitions.

## 3. Was a real UNSW-NB15 evaluation run?

No CSV was provided or available locally. Retained evaluation uses explicitly labelled synthetic development data only.

## 4. Why Random Forest?

It is a practical reproducible baseline for nonlinear tabular relationships and works with numerical plus encoded categorical fields.

## 5. How are categorical features handled?

Train-only constant imputation followed by one-hot encoding. Unseen values are accepted and encoded with unknown-category ignore.

## 6. How are numerical nulls handled?

A training-only median imputer fills missing values. An all-empty feature is retained consistently.

## 7. What is data leakage?

Information from targets or evaluation data reaching training. Both labels, identifiers and unrecognized fields are excluded or rejected; preprocessing sees training data only.

## 8. How are duplicate rows handled?

Identical feature groups stay in one internal partition. For external testing, feature overlaps with training and duplicate test pairs are excluded and their counts recorded.

## 9. Why report class distributions?

Accuracy can conceal weak attack detection when classes are imbalanced. Distributions make metric interpretation and splitting choices visible.

## 10. Define precision.

True positives divided by predicted positives. Attack precision measures how often an attack prediction is correct.

## 11. Define recall.

True positives divided by actual positives. Attack recall measures how many labelled attacks were detected.

## 12. Define F1.

The harmonic mean of precision and recall: 2PR/(P+R), with zero-division handled explicitly.

## 13. What is the confusion-matrix order?

Rows are actual classes and columns are predicted classes. The stored class_order defines both axes; binary order is 0 then 1.

## 14. How is the prediction threshold chosen?

A binary threshold is fixed before evaluation, default 0.5. The test set is never used to tune it. Multiclass uses maximum probability.

## 15. What does the quality gate do?

It compares held-out F1 and recall with configured minimums. A failing candidate is saved for review but cannot replace CURRENT.

## 16. How is the API secured?

Environment API key, constant-time comparison, protected endpoints, bounded bodies and batches, strict feature/type validation, safe errors and a per-process rate bucket.

## 17. Why is joblib a trust boundary?

It can execute code during loading. Only administrator-controlled local artifacts are permitted; a checksum is not a signature against malicious replacement.

## 18. What is PSI?

Population Stability Index compares binned numerical distributions. Fixed training bins and smoothing handle empty bins and missingness.

## 19. Does drift prove degraded accuracy?

No. It signals input-distribution change. Measure performance on new suitable labelled data before claiming degradation.

## 20. What does /metrics report?

Process counters and readiness. It does not report real-time accuracy because prediction requests lack verified labels.

## 21. What is versioned?

Each training run has an independent model and metadata version, dataset digests, seed, schema, preprocessing, library versions and evaluation.

## 22. What would production require?

A flow extractor, representative labelled validation, TLS, external state/rate limits, signed artifacts, monitored performance, calibrated outputs and governed retraining.

