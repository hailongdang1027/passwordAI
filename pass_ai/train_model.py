"""Command-line training & private-password inspection (never argv for secrets)."""
from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path

from ml_ranker import PasswordStrengthModel, train_model

HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Defensive, supervised password-strength model")
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("train", help="Train and evaluate from labelled CSV")
    train.add_argument("--data", type=Path, required=True, help="CSV with password,label")
    train.add_argument("--model", type=Path, default=HERE / "models/password_strength.json")
    train.add_argument("--report", type=Path, default=HERE / "output/password_strength_metrics.json")
    train.add_argument("--seed", type=int, default=42)
    explain = commands.add_parser("explain", help="Interactively assess a password without logging it")
    explain.add_argument("--model", type=Path, default=HERE / "models/password_strength.json")
    args = parser.parse_args()
    if args.command == "train":
        report = train_model(args.data, args.model, args.report, random_state=args.seed)
        test = report["test"]
        print(f"Model: {args.model}\nMetrics: {args.report}")
        print(f"Unseen test: n={test['count']}, balanced_accuracy={test['balanced_accuracy']:.3f}, "
              f"F1={test['f1_strong']:.3f}, ROC-AUC={test['roc_auc']:.3f}")
    else:
        model = PasswordStrengthModel.load(args.model)
        prediction = model.explain(getpass("Nhập mật khẩu để đánh giá (không hiển thị): "))
        print(f"Dự đoán: {prediction['prediction']}, xác suất nhãn mạnh="
              f"{prediction['probability_strong']:.2%}")
        for row in prediction["contributions"]:
            print(f" - {row['label']}: {row['contribution_log_odds']:+.3f} log-odds")
        print("Dự đoán thống kê, không bảo đảm an toàn mật khẩu.")


if __name__ == "__main__":
    main()
