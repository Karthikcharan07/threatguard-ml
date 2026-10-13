import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


def predict_labels(pipeline, x, target, threshold):
    probability = pipeline.predict_proba(x)
    classes = pipeline.classes_.astype(str)
    if target == "label":
        attack_index = list(classes).index("1")
        labels = np.where(probability[:, attack_index] >= threshold, "1", "0")
    else:
        labels = classes[probability.argmax(axis=1)]
    return labels, probability


def evaluate(pipeline, x, y, target, threshold):
    labels, _ = predict_labels(pipeline, x, target, threshold)
    classes = pipeline.classes_.astype(str).tolist()
    report = classification_report(y, labels, labels=classes, output_dict=True, zero_division=0)
    score = report["1"] if target == "label" else report["macro avg"]
    return {
        "accuracy": float(accuracy_score(y, labels)),
        "precision": score["precision"],
        "recall": score["recall"],
        "f1": score["f1-score"],
        "score_average": "attack class 1" if target == "label" else "macro",
        "confusion_matrix": confusion_matrix(y, labels, labels=classes).tolist(),
        "class_order": classes,
        "per_class": report,
        "test_rows": len(y),
    }
