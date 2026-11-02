import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from detector import words


SOURCES = [
    (1342, "Pride and Prejudice", "Jane Austen", "calibration", 2),
    (84, "Frankenstein", "Mary Shelley", "calibration", 2),
    (1661, "The Adventures of Sherlock Holmes", "Arthur Conan Doyle", "calibration", 1),
    (11, "Alice's Adventures in Wonderland", "Lewis Carroll", "evaluation", 4),
    (98, "A Tale of Two Cities", "Charles Dickens", "evaluation", 3),
    (1400, "Great Expectations", "Charles Dickens", "evaluation", 3),
]
GROUPS = [("30-99", 30, 99, 60), ("100-199", 100, 199, 140), ("200-400", 200, 400, 260)]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def get_passage(blocks, cursor, minimum, maximum, target):
    selected = []
    count = 0
    start = None
    selected_end = None
    while cursor < len(blocks):
        begin, end, block = blocks[cursor]
        size = len(words(block))
        if count + size > maximum:
            if count >= minimum:
                break
            selected = []
            count = 0
            start = None
            cursor += 1
            continue
        cursor += 1
        if start is None:
            start = begin
        selected.append(block)
        selected_end = end
        count += size
        if count >= target:
            break
    if count < minimum:
        raise ValueError("Not enough prose in source.")
    return "\n\n".join(selected), cursor, start, selected_end, count


def main():
    if Path("data/manifest.json").exists():
        raise SystemExit("Dataset already exists; keeping the original split and passages.")
    Path("data/sources").mkdir(parents=True, exist_ok=True)
    Path("data/originals").mkdir(exist_ok=True)
    passages = []
    source_info = []
    selected_forgery = 0
    for book, title, author, split, watermark_count in SOURCES:
        url = f"https://www.gutenberg.org/ebooks/{book}.txt.utf-8"
        source_path = f"data/sources/{book}.txt"
        if not Path(source_path).exists():
            request = urllib.request.Request(url, headers={"User-Agent": "University watermark experiment"})
            Path(source_path).write_bytes(urllib.request.urlopen(request, timeout=60).read())
        raw = Path(source_path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        start_match = re.search(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", raw)
        end_match = re.search(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", raw)
        body_start, body_end = start_match.end(), end_match.start()
        cutoff = body_start + (body_end - body_start) // 10
        blocks = []
        for match in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", raw):
            if match.start() < cutoff or match.end() > body_end:
                continue
            block = " ".join(match.group().split())
            if len(words(block)) >= 20 and re.search(r"[.!?][\"'”’]*$", block):
                blocks.append((match.start(), match.end(), block))
        cursor = 0
        requests = []
        for index in range(50):
            requests.append(("unmarked", GROUPS[index % 3]))
        for _ in range(watermark_count):
            requests.append(("watermark", ("100-200", 100, 200, 150)))
        for number, (collection, group) in enumerate(requests, 1):
            group_name, minimum, maximum, target = group
            text, cursor, start, end, count = get_passage(blocks, cursor, minimum, maximum, target)
            pid = f"{split[:3]}-{book}-{number:02d}"
            path = f"data/originals/{pid}.txt"
            Path(path).write_text(text + "\n", encoding="utf-8")
            forgery = False
            if split == "evaluation" and collection == "watermark" and selected_forgery < 5:
                forgery = True
                selected_forgery += 1
            passages.append({
                "id": pid, "source_id": book, "split": split, "collection": collection,
                "length_group": group_name, "total_words": count,
                "distinct_words": len(set(words(text))),
                "query_forgery_selected": forgery,
                "path": path,
                "source_start_character": start, "source_end_character": end,
                "sha256": digest(path),
            })
        source_info.append({
            "id": book, "title": title, "author": author, "split": split,
            "source_page": f"https://www.gutenberg.org/ebooks/{book}",
            "download_url": url, "path": source_path,
            "sha256": digest(source_path),
            "rights": "Public domain in the United States; Gutenberg notice retained in source file.",
        })
        print(f"{book}: saved 50 unmarked and {watermark_count} watermarking originals")
    manifest = {
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "selection": "Sources assigned to splits before scoring. Skip first 10% of each ebook body; take consecutive prose paragraph blocks of at least 20 words, ending in sentence punctuation. Cycle length groups; then take watermarking originals. No score-based selection.",
        "forgery_selection": "First five evaluation watermarking originals in source-list order, before any scores: four from Alice and one from A Tale of Two Cities. This convenience sample is not representative.",
        "sources": source_info, "passages": passages,
    }
    Path("data/manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
