import csv
import hashlib
import json
import random
import secrets
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from detector import WORD_PATTERN, normalize, score, word_color, words


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def watermark(row, key, settings, synonyms):
    start = time.perf_counter()
    original = read_text(row["path"])
    text = unicodedata.normalize("NFC", original)
    folder = "data/versions/" + row["id"]
    Path(folder).mkdir(parents=True, exist_ok=True)
    Path(folder + "/v00.txt").write_text(text, encoding="utf-8")
    edits = []
    version_paths = [folder + "/v00.txt"]
    for match in reversed(list(WORD_PATTERN.finditer(text))):
        if score(text, key, settings["threshold"])["green_fraction"] >= settings["target"]:
            break
        if len(edits) >= settings["max_changed_words"]:
            break
        old = match.group()
        word = normalize(old)
        if word_color(word, key) == 1 or (not old.islower() and not old.istitle()):
            continue
        for synonym in synonyms.get(word, []):
            if word_color(synonym, key) == 1:
                replacement = synonym
                if old.istitle():
                    replacement = synonym.capitalize()
                text = text[:match.start()] + replacement + text[match.end():]
                edits.append({"original_word_index": len(words(original[:match.start()])),
                              "before": old, "after": replacement})
                version = f"{folder}/v{len(edits):02d}.txt"
                Path(version).write_text(text, encoding="utf-8")
                version_paths.append(version)
                break
    before = score(original, key, settings["threshold"])
    after = score(text, key, settings["threshold"])
    output = folder + "/output.txt"
    Path(output).write_text(text, encoding="utf-8")
    stop_reason = "end_of_pass"
    if after["green_fraction"] >= settings["target"]:
        stop_reason = "target"
    elif len(edits) >= settings["max_changed_words"]:
        stop_reason = "edit_limit"
    return {
        "id": row["id"], "split": row["split"], "before": before, "after": after,
        "target_reached": after["green_fraction"] >= settings["target"],
        "changed_words": len(edits), "changes": edits,
        "elapsed_seconds": time.perf_counter() - start,
        "manual_passage_editing_minutes": 0,
        "editing_method": "Automatic fixed synonym list; one right-to-left pass.",
        "output_path": output,
        "output_sha256": digest(output), "version_paths": version_paths,
        "stop_reason": stop_reason,
    }


def score_unmarked(passages, split, key, threshold):
    results = []
    for row in passages:
        if row["split"] == split and row["collection"] == "unmarked":
            result = score(read_text(row["path"]), key, threshold)
            result["id"] = row["id"]
            result["length_group"] = row["length_group"]
            results.append(result)
    return results


def watermark_all(passages, split, key, settings, synonyms):
    attempts = []
    for row in passages:
        if row["split"] == split and row["collection"] == "watermark":
            attempts.append(watermark(row, key, settings, synonyms))
    return attempts


def make_review_packet(attempts, passages):
    Path("review").mkdir(exist_ok=True)
    order = list(attempts)
    random.Random(1101).shuffle(order)
    paths = {}
    for row in passages:
        paths[row["id"]] = row["path"]
    mapping = {}
    packets = ["# Passage quality review\n",
               "Compare the original and edited passage. Record meaning and readability in answers.csv before looking at detector scores. Both must be yes to pass. Do not infer quality from whether a watermark was detected.\n"]
    with open("review/answers.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["review_id", "reviewer", "review_type", "meaning_preserved", "readable", "review_seconds", "notes"])
        for index, attempt in enumerate(order, 1):
            rid = f"R{index:02d}"
            mapping[rid] = attempt["id"]
            original = read_text(paths[attempt["id"]])
            edited = read_text(attempt["output_path"])
            packets.extend([f"\n## {rid}\n", "### Original\n", original, "\n### Edited\n", edited])
            writer.writerow([rid, "", "", "", "", "", ""])
    Path("review/pairs.md").write_text("\n".join(packets), encoding="utf-8")
    save_json("results/review-map.json", mapping)


def run():
    if Path("settings.json").exists() or Path("results/evaluation.json").exists():
        sys.exit("Existing experiment preserved. Use 'summarize' to update review results.")
    Path("results").mkdir(exist_ok=True)
    passages = read_json("data/manifest.json")["passages"]
    if Path("experiment-key.hex").exists():
        key = bytes.fromhex(Path("experiment-key.hex").read_text().strip())
    else:
        key = secrets.token_bytes(32)
        Path("experiment-key.hex").write_text(key.hex() + "\n", encoding="ascii")
    settings = {
        "key_file": "experiment-key.hex", "key_sha256": hashlib.sha256(key).hexdigest(),
        "threshold": 0.60, "target": 0.70, "max_changed_words": 30,
        "stopping_rule": "Stop on reaching target, 30 changed occurrences, or end of one right-to-left pass, whichever comes first. Keep final output even if target is missed.",
        "word_processing": "NFC Unicode normalization, lowercase, then maximal Unicode letter runs using [^\\W\\d_]+. Apostrophes, hyphens, punctuation, digits, underscores and zero-width format characters separate words. No casefold or NFKC. Repeated occurrences counted.",
        "candidate_thresholds": [0.55, 0.60, 0.65],
        "threshold_selection": "Minimize (unmarked calibration false positives / 150) + (unflagged calibration outputs / 5); tie favors higher threshold. Quality is reviewed separately, not assumed.",
        "manifest_sha256": digest("data/manifest.json"),
        "synonyms_sha256": digest("synonyms.json"),
        "detector_sha256": digest("detector.py"),
        "experiment_sha256": digest("experiment.py"),
    }
    synonyms = read_json("synonyms.json")

    unmarked = score_unmarked(passages, "calibration", key, settings["threshold"])
    attempts = watermark_all(passages, "calibration", key, settings, synonyms)
    candidates = []
    best = None
    for threshold in settings["candidate_thresholds"]:
        false_positives = 0
        for row in unmarked:
            if row["green_fraction"] > threshold:
                false_positives += 1
        misses = 0
        for row in attempts:
            if row["after"]["green_fraction"] <= threshold:
                misses += 1
        candidate = {"threshold": threshold, "flagged_unmarked": false_positives,
                     "unflagged_outputs": misses,
                     "selection_loss": false_positives / 150 + misses / 5}
        candidates.append(candidate)
        if best is None or candidate["selection_loss"] <= best["selection_loss"]:
            best = candidate
    settings["threshold"] = best["threshold"]
    for row in unmarked:
        row["flagged"] = row["green_fraction"] > settings["threshold"]
    for row in attempts:
        row["before"]["flagged"] = row["before"]["green_fraction"] > settings["threshold"]
        row["after"]["flagged"] = row["after"]["green_fraction"] > settings["threshold"]
    save_json("results/calibration.json", {"unmarked": unmarked, "attempts": attempts,
                                           "candidates": candidates,
                                           "procedure_versions": ["v1: fixed synonyms, target 0.70, at most 30 changes, one pass; no calibration revisions"]})
    settings["frozen_utc"] = datetime.now(timezone.utc).isoformat()
    save_json("settings.json", settings)

    evaluation_unmarked = score_unmarked(passages, "evaluation", key, settings["threshold"])
    evaluation_attempts = watermark_all(passages, "evaluation", key, settings, synonyms)
    repetition = []
    for word in ["the", "book", "water", "garden"]:
        result = score(" ".join([word] * 1000), key, settings["threshold"])
        result["word"] = word
        repetition.append(result)
    save_json("results/evaluation.json", {
        "started_after_settings_frozen": True,
        "settings_sha256": digest("settings.json"),
        "unmarked": evaluation_unmarked, "attempts": evaluation_attempts,
        "artificial_repetition_examples_excluded_from_rates": repetition,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    })
    make_review_packet(attempts + evaluation_attempts, passages)
    print("Calibration complete. Fixed threshold:", settings["threshold"])
    print("Evaluation saved. Complete the score-free review packet before summarizing.")


def summarize():
    evaluation = read_json("results/evaluation.json")
    mapping = read_json("results/review-map.json")
    reviews = {}
    with open("review/answers.csv", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            reviews[mapping[row["review_id"]]] = row
    attempts = evaluation["attempts"]
    false_positives = 0
    for row in evaluation["unmarked"]:
        if row["flagged"]:
            false_positives += 1
    flagged = 0
    target_reached = 0
    usable_and_flagged = 0
    quality_reviews = []
    for attempt in attempts:
        review = reviews[attempt["id"]]
        usable = review["meaning_preserved"] == "yes" and review["readable"] == "yes"
        is_flagged = attempt["after"]["flagged"]
        if is_flagged:
            flagged += 1
        if attempt["target_reached"]:
            target_reached += 1
        if usable and is_flagged:
            usable_and_flagged += 1
        quality_reviews.append({"id": attempt["id"], "quality_pass": usable,
                                "review_type": review["review_type"], "reviewer": review["reviewer"],
                                "notes": review["notes"], "flagged": is_flagged})
    groups = []
    for label in ["30-99", "100-199", "200-400"]:
        tested = 0
        group_flagged = 0
        for row in evaluation["unmarked"]:
            if row["length_group"] == label:
                tested += 1
                if row["flagged"]:
                    group_flagged += 1
        groups.append({"length_group": label, "flagged": group_flagged, "tested": tested})
    summary = {
        "false_positives": false_positives, "unmarked_tested": 150,
        "false_positive_rate": false_positives / 150,
        "flagged_outputs": flagged, "watermarking_attempts": 10,
        "detection_rate": flagged / 10,
        "target_reached": target_reached,
        "reviewed_usable_and_flagged": usable_and_flagged,
        "reviewed_usable_success_rate": usable_and_flagged / 10,
        "quality_status": "preliminary checks; solo project",
        "assumed_annual_unmarked_submissions": 10000,
        "expected_annual_false_flags": 10000 * false_positives / 150,
        "length_groups": groups, "quality_reviews": quality_reviews,
    }
    save_json("results/summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["run", "summarize"]:
        sys.exit("Usage: python experiment.py run|summarize")
    if sys.argv[1] == "run":
        run()
    else:
        summarize()
