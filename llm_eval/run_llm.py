"""Ask a language model to label proposals from the gold set, and save its answers.

    set GROQ_API_KEY=your_key            (Windows CMD; never put the key in a file here)
    python llm_eval/run_llm.py --prompt v1_zero_shot --split dev
    python llm_eval/run_llm.py --prompt v2_with_guidance --split dev
    python llm_eval/run_llm.py --prompt v2_with_guidance --split test   (once, at the end)

Answers are cached per model, prompt and proposal, so a stopped run continues where it left off
and a finished run costs nothing to repeat. Use --mock to test the plumbing without calling a model.
"""
import argparse
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).parent
URL = "https://api.groq.com/openai/v1/chat/completions"
VALID = {"supports", "opposes", "unclear"}


def cache_path(model, prompt):
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", model).strip("-")
    return HERE / "runs" / f"{safe}__{prompt}.jsonl"


def load_cache(path):
    done = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                done[row["id"]] = row["label"]
    return done


def parse_reply(text):
    """Pull the labels out of the model's reply, tolerating extra text around the JSON."""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    labels = {}
    for item in data.get("labels", []):
        label = str(item.get("label", "")).strip().lower()
        if label in VALID and "id" in item:
            labels[str(item["id"])] = label
    return labels


def ask(model, system_prompt, batch, key):
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(batch, ensure_ascii=False)},
        ],
    }
    for attempt in range(6):
        response = requests.post(URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=120)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"] or ""
        if response.status_code == 429:
            wait = float(response.headers.get("retry-after", 20)) + 1
            print(f"    rate limit reached, waiting {wait:.0f}s")
            time.sleep(wait)
            continue
        if response.status_code >= 500:
            time.sleep(5 * (attempt + 1))
            continue
        raise SystemExit(f"The service refused the request ({response.status_code}): {response.text[:400]}")
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="name of a file in llm_eval/prompts, without .txt")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--batch", type=int, default=15)
    parser.add_argument("--mock", action="store_true", help="skip the model and reuse the keyword-rule label")
    args = parser.parse_args()

    gold = pd.read_csv(HERE / "gold_set.csv")
    gold = gold[gold["split"] == args.split]
    system_prompt = (HERE / "prompts" / f"{args.prompt}.txt").read_text(encoding="utf-8")
    model = "mock" if args.mock else args.model
    path = cache_path(model, args.prompt)
    path.parent.mkdir(exist_ok=True)
    done = load_cache(path)
    todo = gold[~gold["id"].isin(done)]
    print(f"{len(gold)} proposals in the {args.split} split, {len(todo)} still to label with {model}")

    key = os.environ.get("GROQ_API_KEY", "")
    if not args.mock and not key and len(todo):
        raise SystemExit("GROQ_API_KEY is not set. In CMD run:  set GROQ_API_KEY=your_key")

    with open(path, "a", encoding="utf-8") as out:
        for start in range(0, len(todo), args.batch):
            rows = todo.iloc[start:start + args.batch]
            batch = [{"id": r.id, "company": r.company, "title": r.title} for r in rows.itertuples()]
            if args.mock:
                labels = dict(zip(rows["id"], rows["rule_label"]))
            else:
                labels = parse_reply(ask(model, system_prompt, batch, key))
                time.sleep(2)
            for item in batch:
                # A missing or malformed answer is recorded as "no answer" and counts as wrong when scored.
                label = labels.get(item["id"], "no answer")
                out.write(json.dumps({"id": item["id"], "label": label}) + "\n")
            out.flush()
            answered = sum(1 for item in batch if item["id"] in labels)
            print(f"  {min(start + args.batch, len(todo)):>4}/{len(todo)}  answered {answered}/{len(batch)}")
    print(f"Saved to {path}")


if __name__ == "__main__":
    main()
