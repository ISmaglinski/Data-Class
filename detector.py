import hmac
import json
import re
import sys
import unicodedata


WORD_PATTERN = re.compile(r"[^\W\d_]+")


def normalize(text):
    return unicodedata.normalize("NFC", text).lower()


def words(text):
    return WORD_PATTERN.findall(normalize(text))


def word_color(word, key):
    return hmac.digest(key, word.encode("utf-8"), "sha256")[-1] & 1


def score(text, key, threshold):
    tokens = words(text)
    if len(tokens) == 0:
        raise ValueError("Input contains no words.")
    green = 0
    for word in tokens:
        green += word_color(word, key)
    fraction = green / len(tokens)
    return {
        "total_words": len(tokens),
        "distinct_words": len(set(tokens)),
        "green_words": green,
        "green_fraction": fraction,
        "flagged": fraction > threshold,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python detector.py text_file.txt")
    settings = json.load(open("settings.json", encoding="utf-8"))
    key = bytes.fromhex(open(settings["key_file"]).read().strip())
    text = open(sys.argv[1], encoding="utf-8").read()
    try:
        print(json.dumps(score(text, key, settings["threshold"]), indent=2))
    except ValueError as error:
        sys.exit(f"Error: {error}")
