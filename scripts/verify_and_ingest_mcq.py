"""Verify, clean, balance, and ingest MCQ.csv into data/questions/mcq_bank.csv."""

import csv
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_CSV = ROOT / "MCQ.csv"
OUTPUT_DIR = ROOT / "data" / "questions"
TARGET_CSV = OUTPUT_DIR / "mcq_bank.csv"

# Category normalization map
CATEGORY_FIXES = {
    " Electronics & Communication Engineering": "Electronics & Communication Engineering",
    "Corporate Management, Finance & Investment Associate": "Corporate Management, Finance & Law",
}

HEADER = [
    "category",
    "role_or_stream",
    "topic",
    "difficulty",
    "question",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_option",
    "explanation",
    "bloom_level",
]


def clean_and_ingest():
    if not SOURCE_CSV.exists():
        print(f"Error: {SOURCE_CSV} does not exist.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)  # Deterministic shuffling for reproducibility

    cleaned_rows = []
    skipped_rows = 0
    repaired_rows = 0

    with open(SOURCE_CSV, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        try:
            next(reader)
        except StopIteration:
            print("CSV file is empty.")
            return

        for line_no, row in enumerate(reader, start=2):
            # 1. Skip completely empty rows
            if not row or not any(field.strip() for field in row):
                skipped_rows += 1
                continue

            # 2. Skip repeated header rows
            if row[0].strip().lower() == "category" and "role" in row[1].lower():
                skipped_rows += 1
                continue

            # 3. Handle row 963-style missing role_or_stream column shift
            if len(row) == 11 and row[0].strip() == "Computer Science":
                # Shift: category, topic, difficulty, question, option_a...
                row = [
                    row[0],
                    "Database Administrator (DBA)",
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    row[9],
                    row[10],
                ]
                repaired_rows += 1

            if len(row) != 12:
                print(f"Warning: Line {line_no} has {len(row)} columns, skipping: {row[:3]}")
                skipped_rows += 1
                continue

            category = row[0].strip()
            category = CATEGORY_FIXES.get(category, category)
            role = row[1].strip()
            topic = row[2].strip()
            difficulty = row[3].strip().lower()
            if difficulty not in ("easy", "medium", "hard"):
                difficulty = "medium"

            question = row[4].strip()
            raw_options = [row[5].strip(), row[6].strip(), row[7].strip(), row[8].strip()]
            correct_opt = row[9].strip().upper()
            explanation = row[10].strip()
            bloom = row[11].strip().lower()
            if bloom not in ("remember", "understand", "apply", "analyze"):
                bloom = "understand"

            # Map letter to index (A=0, B=1, C=2, D=3)
            letter_to_idx = {"A": 0, "B": 1, "C": 2, "D": 3}
            if correct_opt not in letter_to_idx:
                # If value is numeric string '0', '1', '2', '3'
                if correct_opt in ("0", "1", "2", "3"):
                    correct_idx = int(correct_opt)
                else:
                    msg = f"Warning: Line {line_no} has invalid option '{correct_opt}', skipping."
                    print(msg)
                    skipped_rows += 1
                    continue
            else:
                correct_idx = letter_to_idx[correct_opt]

            # 4. Shuffle options to prevent LLM Option A bias
            # Pair each option with whether it's correct
            items = [(opt, i == correct_idx) for i, opt in enumerate(raw_options)]
            random.shuffle(items)

            new_options = [item[0] for item in items]
            new_correct_idx = next(i for i, item in enumerate(items) if item[1])
            new_correct_letter = ["A", "B", "C", "D"][new_correct_idx]

            cleaned_rows.append(
                [
                    category,
                    role,
                    topic,
                    difficulty,
                    question,
                    new_options[0],
                    new_options[1],
                    new_options[2],
                    new_options[3],
                    new_correct_letter,
                    explanation,
                    bloom,
                ]
            )

    # Write cleaned rows
    with open(TARGET_CSV, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(HEADER)
        writer.writerows(cleaned_rows)

    print(f"Cleaned and saved {len(cleaned_rows)} questions to {TARGET_CSV}")
    print(f"Repaired rows: {repaired_rows}, Skipped/Header rows: {skipped_rows}")

    # Summary Statistics
    cat_counter = Counter(r[0] for r in cleaned_rows)
    opt_counter = Counter(r[9] for r in cleaned_rows)
    diff_counter = Counter(r[3] for r in cleaned_rows)

    print("\n--- Summary by Domain ---")
    for cat, count in sorted(cat_counter.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} questions")

    print("\n--- Option Distribution (After Balancing) ---")
    for opt, count in sorted(opt_counter.items()):
        pct = (count / len(cleaned_rows)) * 100
        print(f"  Option {opt}: {count} ({pct:.1f}%)")

    print("\n--- Difficulty Distribution ---")
    for diff, count in sorted(diff_counter.items()):
        pct = (count / len(cleaned_rows)) * 100
        print(f"  {diff.capitalize()}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    clean_and_ingest()
