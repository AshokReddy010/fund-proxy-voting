"""Score the keyword rules and every saved model run against the gold set.

    python llm_eval/score.py --split dev
    python llm_eval/score.py --split test

Writes llm_eval/results_<split>.md and llm_eval/errors_<split>.csv.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def metrics(truth, predicted):
    correct = (truth == predicted)
    row = {"proposals": len(truth), "accuracy": correct.mean()}
    for label in ("supports", "opposes"):
        said = predicted == label
        real = truth == label
        row[f"{label} precision"] = (said & real).sum() / said.sum() if said.sum() else float("nan")
        row[f"{label} recall"] = (said & real).sum() / real.sum() if real.sum() else float("nan")
    row["no clear answer"] = (~predicted.isin(["supports", "opposes"])).mean()
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    args = parser.parse_args()

    gold = pd.read_csv(HERE / "gold_set.csv")
    gold = gold[gold["split"] == args.split].set_index("id")
    systems = {"Keyword rules": gold["rule_label"]}
    for path in sorted((HERE / "runs").glob("*.jsonl")):
        answers = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                answers[row["id"]] = row["label"]
        covered = gold.index.intersection(list(answers))
        if len(covered) == len(gold):
            model, prompt = path.stem.split("__")
            llm = pd.Series(answers).reindex(gold.index)
            systems[f"{model} / {prompt}"] = llm
            # Hybrid: keep the keyword rule where it gives an answer, ask the model only where it does not.
            systems[f"Rules, then {prompt} where rules are unclear"] = gold["rule_label"].where(gold["rule_label"] != "unclear", llm)
        elif len(covered):
            print(f"Skipping {path.name}: only {len(covered)} of {len(gold)} {args.split} proposals labelled")

    table = pd.DataFrame({name: metrics(gold["label"], predicted) for name, predicted in systems.items()}).T
    shown = table.copy()
    for column in shown.columns:
        if column != "proposals":
            shown[column] = (100 * shown[column]).round(1).astype(str) + "%"
    shown["proposals"] = shown["proposals"].astype(int)

    lines = [
        f"# Direction labels scored on the {args.split} split",
        "",
        "The correct answer for each proposal is how ten specialist ESG fund houses voted on it.",
        "",
        shown.to_markdown(),
        "",
    ]
    for name, predicted in systems.items():
        lines += [f"## {name}: what it said against the correct answer", "",
                  pd.crosstab(gold["label"], predicted, rownames=["correct"], colnames=["said"]).to_markdown(), ""]
    (HERE / f"results_{args.split}.md").write_text("\n".join(lines), encoding="utf-8")

    errors = gold[["company", "title", "label"]].copy()
    for name, predicted in systems.items():
        errors[name] = predicted
    wrong = errors[[c for c in errors.columns if c not in ("company", "title", "label")]].ne(errors["label"], axis=0).any(axis=1)
    errors[wrong].to_csv(HERE / f"errors_{args.split}.csv")
    print("\n".join(lines[:6]))
    print(f"\n{int(wrong.sum())} proposals where at least one system was wrong: llm_eval/errors_{args.split}.csv")


if __name__ == "__main__":
    main()
