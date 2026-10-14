"""Trainable, validated, explainable password-STRENGTH classifier.

No hand-authored scoring formula, no password guess ranking, no raw examples
in saved model/metrics. Inference uses learned logistic-regression parameters.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from feature_extractor import FEATURE_LABELS, FEATURE_NAMES, extract_features

SCHEMA_VERSION = "password-strength-logreg-v1"


def _probability(log_odds: float) -> float:
    if log_odds >= 0:
        return 1.0 / (1.0 + math.exp(-log_odds))
    e = math.exp(log_odds)
    return e / (1 + e)


@dataclass(frozen=True)
class PasswordStrengthModel:
    """Read-only, trusted-data model; JSON contains coefficients only."""

    feature_names: tuple[str, ...]
    mean: tuple[float, ...]
    scale: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float
    threshold: float
    metadata: dict

    def __post_init__(self):
        n = len(FEATURE_NAMES)
        if (self.feature_names != FEATURE_NAMES or
                any(len(row) != n for row in (self.mean, self.scale, self.coefficients))):
            raise ValueError("Phiên bản đặc trưng mô hình không tương thích.")
        if not (0 < self.threshold < 1):
            raise ValueError("Ngưỡng phân loại không hợp lệ.")
        if any(not math.isfinite(float(v)) for row in (self.mean, self.scale, self.coefficients) for v in row):
            raise ValueError("Tham số mô hình không hợp lệ.")
        if any(v <= 0 for v in self.scale) or not math.isfinite(self.intercept):
            raise ValueError("Tham số chuẩn hóa mô hình không hợp lệ.")

    def probability_strong(self, password: str) -> float:
        features = extract_features(password)
        log_odds = self.intercept + sum(
            coef * (value - mean) / scale
            for value, coef, mean, scale in zip(features, self.coefficients, self.mean, self.scale)
        )
        return _probability(log_odds)

    def explain(self, password: str, *, top_n: int = 6) -> dict:
        """Log-odds feature contributions are exact for the linear model."""
        features = extract_features(password)
        explanations = [
            {
                "feature": key,
                "label": FEATURE_LABELS[key],
                "value": round(value, 5),
                "contribution_log_odds": round(coef * (value - mean) / scale, 5),
            }
            for key, value, coef, mean, scale
            in zip(FEATURE_NAMES, features, self.coefficients, self.mean, self.scale)
        ]
        explanations.sort(key=lambda row: abs(row["contribution_log_odds"]), reverse=True)
        probability = self.probability_strong(password)
        return {
            "probability_strong": round(probability, 6),
            "prediction": "strong" if probability >= self.threshold else "weak",
            "decision_threshold": self.threshold,
            "baseline_log_odds": round(self.intercept, 5),
            "contributions": explanations[:max(0, top_n)],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "feature_names": list(self.feature_names),
            "mean": list(self.mean),
            "scale": list(self.scale),
            "coefficients": list(self.coefficients),
            "intercept": self.intercept,
            "threshold": self.threshold,
            "metadata": self.metadata,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "PasswordStrengthModel":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Tệp mô hình không đúng định dạng/phiên bản.")
        return cls(
            feature_names=tuple(payload["feature_names"]),
            mean=tuple(map(float, payload["mean"])),
            scale=tuple(map(float, payload["scale"])),
            coefficients=tuple(map(float, payload["coefficients"])),
            intercept=float(payload["intercept"]),
            threshold=float(payload["threshold"]),
            metadata=dict(payload["metadata"]),
        )


def read_labelled_csv(path: str | Path) -> tuple[list[str], list[int], dict]:
    """Require independent binary ground-truth labels; drop exact duplicates.

    No labels are generated from rules or from the unlabeled password dictionary.
    """
    seen: dict[str, tuple[int, str | None]] = {}
    total = 0
    use_groups = False
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {"password", "label"}.issubset(reader.fieldnames):
            raise ValueError("CSV phải có hai cột: password,label (0=yếu; 1=mạnh).")
        use_groups = "group_id" in reader.fieldnames
        for row in reader:
            total += 1
            password = row.get("password", "")
            label = (row.get("label") or "").strip()
            if not isinstance(password, str) or not password or label not in ("0", "1"):
                raise ValueError(f"Dòng dữ liệu {total + 1} trống hoặc nhãn ngoài 0/1.")
            if len(password) > 4096:
                raise ValueError(f"Dòng {total + 1} vượt quá 4096 ký tự.")
            value = int(label)
            group = (row.get("group_id") or "").strip() if use_groups else None
            if use_groups and not group:
                raise ValueError("Nếu dùng group_id, tất cả các dòng phải có nhóm không trống.")
            if password in seen and seen[password] != (value, group):
                raise ValueError("Cùng một chuỗi có nhãn hoặc nhóm mâu thuẫn. Hãy sửa CSV.")
            seen[password] = (value, group)
    passwords = list(seen)
    labels = [row[0] for row in seen.values()]
    groups = [row[1] for row in seen.values()] if use_groups else None
    count_weak = labels.count(0)
    count_strong = labels.count(1)
    if len(passwords) < 60 or min(count_weak, count_strong) < 20:
        raise ValueError("Cần ít nhất 60 mẫu riêng biệt và 20 mẫu cho mỗi nhãn để chia 3 tập.")
    return passwords, labels, groups, {
        "read_rows": total,
        "distinct_samples": len(passwords),
        "duplicates_removed": total - len(passwords),
        "group_id_supplied": use_groups,
        "distinct_groups": len(set(groups)) if groups is not None else None,
        "class_counts": {"weak": count_weak, "strong": count_strong},
    }


def _metrics(labels, probabilities, threshold):
    from sklearn.metrics import (accuracy_score, balanced_accuracy_score, brier_score_loss,
                                 confusion_matrix, f1_score, precision_score,
                                 recall_score, roc_auc_score)
    predictions = [int(p >= threshold) for p in probabilities]
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel().tolist()
    return {
        "count": len(labels),
        "accuracy": float(accuracy_score(labels, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "precision_strong": float(precision_score(labels, predictions, zero_division=0)),
        "recall_strong": float(recall_score(labels, predictions, zero_division=0)),
        "recall_weak": (float(tn / (tn + fp)) if tn + fp else 0.0),
        "false_strong_rate": (float(fp / (tn + fp)) if tn + fp else 0.0),
        "f1_strong": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "brier_score": float(brier_score_loss(labels, probabilities)),
        "confusion_matrix_weak_strong": [[int(tn), int(fp)], [int(fn), int(tp)]],
    }


def train_model(dataset_path: str | Path, model_path: str | Path,
                report_path: str | Path, *, random_state: int = 42) -> dict:
    """60/20/20 split with validation-tuned threshold and untouched test.

    Optional group_id keeps related password families out of different sets.
    No metrics are claimed from data used to fit or select the threshold.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split, StratifiedGroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import balanced_accuracy_score

    passwords, labels, groups, profile = read_labelled_csv(dataset_path)
    X = [extract_features(pwd) for pwd in passwords]
    # Raw strings are discarded before split; only numeric features are fitted.
    if groups is None:
        X_train, X_remaining, y_train, y_remaining = train_test_split(
            X, labels, test_size=0.4, stratify=labels, random_state=random_state,
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_remaining, y_remaining, test_size=0.5, stratify=y_remaining,
            random_state=random_state,
        )
    else:
        if len(set(groups)) < 15:
            raise ValueError("group_id cần ít nhất 15 nhóm khác nhau để tách 3 tập.")
        indices = list(range(len(X)))
        splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=random_state)
        remaining_idx, test_idx = next(splitter.split(X, labels, groups))
        remaining_idx = list(remaining_idx)
        val_splitter = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=random_state)
        sub_train_idx, sub_val_idx = next(val_splitter.split(
            [X[i] for i in remaining_idx],
            [labels[i] for i in remaining_idx],
            [groups[i] for i in remaining_idx],
        ))
        train_idx = [remaining_idx[i] for i in sub_train_idx]
        val_idx = [remaining_idx[i] for i in sub_val_idx]
        X_train, y_train = [X[i] for i in train_idx], [labels[i] for i in train_idx]
        X_val, y_val = [X[i] for i in val_idx], [labels[i] for i in val_idx]
        X_test, y_test = [X[i] for i in test_idx], [labels[i] for i in test_idx]
        split_groups = [set(groups[i] for i in idx) for idx in (train_idx, val_idx, test_idx)]
        if any(a & b for n, a in enumerate(split_groups) for b in split_groups[n + 1:]):
            raise AssertionError("Group leakage: group_id trùng giữa các tập.")
        profile["group_leakage_check"] = "PASS: train/validation/test group_id disjoint"
    if any(set(subset) != {0, 1} for subset in (y_train, y_val, y_test)):
        raise ValueError("Mỗi tập huấn luyện/kiểm định/kiểm thử cần cả 2 nhãn; hãy tăng hoặc cân đối group_id.")
    pipeline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=random_state))
    pipeline.fit(X_train, y_train)
    probabilities_val = pipeline.predict_proba(X_val)[:, 1].tolist()
    # Choose threshold solely on validation set, never test set.
    candidates = sorted(set([0.5] + [float(p) for p in probabilities_val]))
    candidates = [p for p in candidates if 0 < p < 1]
    threshold = max(
        candidates,
        key=lambda t: (balanced_accuracy_score(y_val, [int(p >= t) for p in probabilities_val]),
                       -abs(t - 0.5)),
    )
    scaler = pipeline.named_steps["standardscaler"]
    reg = pipeline.named_steps["logisticregression"]
    model = PasswordStrengthModel(
        feature_names=FEATURE_NAMES,
        mean=tuple(map(float, scaler.mean_)),
        scale=tuple(map(float, scaler.scale_)),
        coefficients=tuple(map(float, reg.coef_[0])),
        intercept=float(reg.intercept_[0]),
        threshold=float(threshold),
        metadata={
            "trained_utc": datetime.now(timezone.utc).isoformat(),
            "algorithm": "StandardScaler + LogisticRegression",
            "label_semantics": "0=weak, 1=strong (provided by dataset author)",
            "training_samples": len(X_train),
            "feature_version": SCHEMA_VERSION,
        },
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "source": "provided labelled CSV",
        "evaluation_note": "Held-out results measure agreement with dataset labels, NOT resistance to cracking.",
        "dataset": profile,
        "split": {"method": ("stratified group-disjoint ~60/20/20" if groups is not None else
                             "stratified 60/20/20, exact duplicates removed"), "seed": random_state,
                  "train": len(X_train), "validation": len(X_val), "test": len(X_test)},
        "threshold_selected_on": "validation",
        "threshold": model.threshold,
        "validation": _metrics(y_val, probabilities_val, model.threshold),
        "test": _metrics(y_test, pipeline.predict_proba(X_test)[:, 1], model.threshold),
        "global_explanation": [
            {"feature": feature, "label": FEATURE_LABELS[feature], "coefficient_standardized": round(float(coef), 6)}
            for feature, coef in zip(FEATURE_NAMES, model.coefficients)
        ],
    }
    # Serialize coefficients safely as JSON, not pickle; no individual passwords in artifacts.
    model.save(model_path)
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report
