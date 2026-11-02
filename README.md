needs Python 3.11, run python detector.py data/originals/eva-11-51.txt from this folder to get a passage scored.

to run copy detector.py, experiment.py, synonyms.json, experiment-key.hex, and data/ into an empty folder and run python experiment.py run there.

After completing review/answers.csv, run python experiment.py summarize to get all the results together.

The detector uses the saved key to color words and flags a green-word score above 0.65; the full write-up is in [the report](output/pdf/milestone-1-report.pdf).

Data sources (Project Gutenberg, public domain in the US): Pride and Prejudice (1342), Frankenstein (84), The Adventures of Sherlock Holmes (1661), Alice's Adventures in Wonderland (11), A Tale of Two Cities (98), Great Expectations (1400). Per-passage sources are in data/manifest.json.

Contribution statement: this is a solo project by Ian Smaglinski, with no other team members. All project files are in this repository's commit.
