# Keyed Text Watermarking: Detection, Attacks, and Policy

- Teams of up to 4 students; two milestones over 8 weeks. Week numbers refer to the project schedule.
- Prerequisite: Python. The project uses a standard-library keyed hash function, counts, fractions, and a guideline for interpreting error rates from small samples.
- Compute: a laptop.

## 1. Objectives

Text watermarking embeds a detectable signal in text. In a keyed scheme, the signal depends on a secret key. A detector reports a match to that signal. Authorship and policy violations require separate evidence.

Implement the word-based watermarking scheme below, build a detection service, test attacks, and write a deployment policy supported by your results.

Project objectives:

1. Explain how a secret key determines word colors, how substitutions embed a watermark, and how the detector scores text.
2. Identify the attacker's objective, knowledge, and system access.
3. Explain how access to the secret key and detector responses helps an attacker remove or forge a watermark.
4. Measure detection errors and attack costs, and explain the limits of the experiments.
5. Specify who may query the detector, what data the service retains, and how a person can appeal a detection result.

## 2. The watermarking scheme

Assign each word a label, **green** or **red**, using a secret key. Watermark prose by replacing red words with green synonyms. The detector flags text when its fraction of green words exceeds a chosen threshold.

Define how your program splits text into words (**tokenization**) and converts them to a consistent form (**normalization**). For example, lowercasing makes `Book` and `book` the same word. Document how you handle case, punctuation, and Unicode. Use the same rules for watermarking and detection.

Generate one random 32-byte key `K`. Use HMAC, a keyed hash function, to assign each normalized word a color:

```python
import hmac
import secrets

K = secrets.token_bytes(32)  # Generate once and save for the experiment.

def word_color(word, key):
    # Pass in a word already normalized using your rules.
    return hmac.digest(key, word.encode("utf-8"), "sha256")[-1] & 1
```

Call `word_color(word, K)` for each normalized word: 1 means green; 0 means red. Every occurrence of a word has the same color under the same key.

Score a document by counting green word occurrences:

```
green_fraction = number of green word occurrences / total word occurrences
flag the document when green_fraction > threshold
```

For example, 65 green words out of 100 gives a score of 0.65, which exceeds a threshold of 0.60. A score equal to the threshold is unflagged. Reject input containing no words with an explicit error. Count repeated words in the score and record the number of distinct normalized words.

The keyed hash assigns approximately half of distinct words to each color, but document scores depend on word frequency. Repeating one word 1,000 times produces a score of either 0 or 1. Those occurrences represent one color assignment.

Replace red words with green synonyms while preserving meaning and readability. You may use a hand-built synonym list or automate rewriting. Define a **watermarking target** (the desired green fraction) and a **stopping rule**. For example, stop at a score of 0.70 or after 15 minutes, whichever comes first. Keep the best output even if it misses the target.

Set the target strictly above the detection threshold if reaching it should produce a flag. Choose these settings during calibration and keep them fixed during evaluation (Section 4).

## 3. Reading

Required:

- Kirchenbauer et al., [*A Watermark for Large Language Models*](https://arxiv.org/abs/2301.10226) (2023). Read the introduction and scheme description. Compare generation-time watermarking with this project's word substitutions.

Optional:

- Zhao et al., [*Provable Robust Watermarking for AI-Generated Text*](https://arxiv.org/abs/2306.17439) (ICLR 2024). Introduces a fixed-group, or unigram, watermark for language models.
- Jovanović et al., [*Watermark Stealing in Large Language Models*](https://proceedings.mlr.press/v235/jovanovic24a.html) (2024). Learns watermark rules through queries to a watermarked generation API. Compare that access with the detector queries used here.
- Christ, Gunn, and Zamir, [*Undetectable Watermarks for Language Models*](https://proceedings.mlr.press/v247/christ24a.html) (2024). Studies a cryptographic notion of undetectability.

## 4. Milestone 1: detector, evaluation, and threat model (weeks 1–4)

**Deliverable:** detector code and a report of at most 6 pages. Set up a shared repository in week 1. Include a README with run instructions, data sources, and a contribution statement naming each member's work with links to relevant commits. References and the contribution statement are outside the page limit; additional experiment outputs may be stored in the repository.

### 4.1 Prepare the experiment

Collect **300 unmarked prose passages** from public-domain or otherwise reusable sources to measure false positives. You may extract passages with a script. Use three length groups: 30–99, 100–199, and 200–400 normalized words, counted using your rules from Section 2.

Collect **15 additional public-domain passages**, each 100–200 normalized words, for watermarking and attacks. Keep all **315 passages** distinct. Save the originals and every edited version.

Before running the detector, divide the passages into two sets:

- **Calibration:** passages used to choose the threshold and adjust the watermarking procedure.
- **Evaluation:** passages used to measure detection and watermarking success after fixing those settings.

Use the following allocation:

| Passage collection                    | Calibration                           | Evaluation                              |
| ------------------------------------- | ------------------------------------- | --------------------------------------- |
| 300 passages kept unmarked            | 150 to help choose the threshold      | 150 to measure false-positive rate      |
| 15 passages selected for watermarking | 5 to practice and adjust watermarking | 10 to test watermarking and run attacks |

Include at least 30 unmarked passages from each length group in each set. Record each passage's source and the number of source documents. Assign all passages from a given book or source document to the same set, including those selected for watermarking.

Before seeing detector scores, select and label **5 of the 10 watermarking evaluation passages** for query-access forgery (Section 5.2). Record the selection method. Use their unmarked originals in all three service configurations. Use all 10 passages for watermarking evaluation and the other attacks.

### 4.2 Calibrate, then evaluate

Use one randomly generated key throughout; selecting a key based on its scores would bias the results. Save the settings, inputs, and outputs needed to reproduce each run.

1. **Score unmarked calibration text.** Run the detector on the 150 unmarked calibration passages.
2. **Practice watermarking.** Attempt to watermark the 5 calibration passages. Record the target, stopping rule, final scores, editing effort, and quality-check results. Adjust the procedure using only calibration passages. Save each version and its settings.
3. **Choose the threshold.** Test candidate thresholds, such as 0.55, 0.60, and 0.65, against both calibration collections. For each, count flagged unmarked passages and unflagged watermarking outputs. Explain your choice using those counts.
4. **Fix the settings.** Record the key, word-processing rules, threshold, watermarking target, and stopping rule. Keep them unchanged during evaluation.
5. **Evaluate.** Score the 150 unmarked evaluation passages and attempt to watermark all 10 watermarking evaluation passages. Record each original's score and each output's score and quality. Follow the fixed stopping rule even when an output remains unflagged.

Report these measurements from step 5. A **false positive** is a flagged unmarked passage. A **usable** output passes the quality check below.

| Measurement                            | Calculation                                                                |
| -------------------------------------- | -------------------------------------------------------------------------- |
| Unmarked false-positive rate           | Flagged unmarked evaluation passages / 150                                 |
| Detection rate on watermarking outputs | Flagged outputs / all 10 watermarking attempts                             |
| Usable watermarking success rate       | Outputs that both pass the quality check and are flagged / all 10 attempts |

Report how many attempts reached the target and the scores before and after watermarking. Include failed attempts and outputs that changed the meaning or reduced readability.

**Quality check.** For watermarking and attacks, a teammate who did not edit the passage compares the original and edited versions: Is the main meaning preserved? Is the prose readable? Both answers must be yes for the output to be usable. Hide scores, detector decisions, and whether the target was reached until the reviewer records the answers. Report changed-word counts and your counting method. Explain how a teammate's knowledge of the project could influence the review.

**Length and repetition.** For each length group, report flagged and tested counts for unmarked evaluation passages. Record total and distinct normalized word counts for each passage. Analyze how repetition affects the score of at least one highly repetitive example.

**Small samples.** With a fixed detector and `n` independent, representative test passages, zero observed errors gives an approximate 95% confidence upper bound of `3/n` on the error rate. For 150 passages, this bound is about 2%, even if none were flagged incorrectly. Passages from the same source may share vocabulary and style, so their results may be correlated. Explain how sample size and shared sources limit your error-rate estimates.

**Annual false flags.** For the policy memo, choose an operator's annual volume of unmarked submissions and multiply it by your measured false-positive rate. For example, 10,000 submissions at 1% gives 100 expected false flags. State the assumed volume, uncertainty in the rate, and how closely your test passages resemble those submissions.

If you change the design after evaluation, preserve the original results and report new runs separately. Explain which changes used information from the evaluation passages. Testing those passages again measures performance on text already used to adjust the design.

### 4.3 Build the threat model

A **threat model** specifies the attacker's goals, knowledge, and access. Consider two goals:

| Goal    | Meaning                                                                                                                                |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Removal | Make an initially flagged, usable watermarked passage stop being flagged while preserving meaning and readability.                     |
| Forgery | Make unmarked source prose become flagged without using the legitimate watermarking service, while preserving meaning and readability. |

Consider three access levels. A **query** submits text to the detector and returns a response.

| Access | Adversary's capabilities                                                                                                                                   |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| None   | Knows the algorithm and rules but has neither the key nor detector access.                                                                                 |
| Query  | Knows the algorithm and rules and can submit chosen text to the detection service. Sees its permitted responses but cannot read its key or internal state. |
| Key    | Has query access and also knows the watermark key, so can compute word colors locally. Has no additional service administrator privileges.                 |

Make a table with the two goals as rows and the three access levels as columns. In each cell, describe an attack, expected query count and editing effort, likely effect on text quality, and a defense or condition that could prevent success. Label predictions and measured results. Milestone 2 tests query-access removal, query-access forgery, and key-access forgery.

Address three short design questions:

- **Key distribution:** Who can watermark, detect locally, and submit queries? Anyone holding the detection key can also compute colors for forgery. Explain what document content the operator can access during detection and how an independent reviewer could check a disputed result.
- **Context dependence:** Some schemes use preceding tokens to determine a word's color. Explain how that would affect your proposed attacks.
- **Digital signatures:** Compare watermarking with signing a document at its source. Discuss key compromise, editing, and what verification establishes about the text's origin and authorship.

## 5. Milestone 2: service, attacks, and policy (weeks 5–8)

**Deliverable:** service and attack code, a report of at most 6 pages, and a policy memo of at most 2 pages. Update the README and contribution statement. Code must run from a fresh clone with documented dependencies and setup steps. References and the contribution statement are outside the page limits.

### 5.1 Build a local service

Build an interface to your Milestone 1 detector that accepts an account credential and a passage, checks access, and returns a detection response. Use a command-line client and local service module, or an equivalent interface.

Implement these controls:

- **Authentication** identifies the account. Create at least two accounts with different roles. Random access tokens are sufficient.
- **Authorization** checks permitted actions. For example, let submitters request detection and auditors also inspect query metadata. If you enforce document ownership, assign stored document IDs to owners and check those assignments.
- **Logging** records requests. Store the account, timestamp, outcome, and rate-limit status. Omit document text by default and explain your logging choices.
- **Rate limiting** restricts request frequency. Set a per-account allowance, such as 20 requests per minute. Store counters and time windows so they survive client restarts. You may simulate time during experiments.
- **Response modes** determine what the detector returns. Support a score response (green fraction and decision) and a binary response (decision only). Document how many digits of the score are returned. Binary mode must hide scores from all attacker-accessible output, including logs.

Keep service code and secrets separate from attack code. Query-access attacks may use only the service interface: they may not read the key, call internal color functions, alter logs or counters, or advance the clock. Key-access attacks may also use the watermark key.

Use a separate experiment driver to set up runs, reset service state between configurations, advance simulated time, and record measurements. The driver may load the key for evaluation but must keep hidden scores and secrets from query-access attack code. Enforce this simulated security boundary through code separation.

Show that the service rejects invalid credentials, denies actions that an account's role does not permit, and enforces the rate limit after a client restart. Explain how additional accounts affect an attacker's total request allowance.

### 5.2 Run the attacks

Use the 10 watermarking evaluation passages from Milestone 1, retaining their unmarked originals and watermarking outputs. Keep the detector and watermarking settings fixed.

A passage is **eligible** for an attack when it meets the starting condition:

| Attack                    | Starting text                                    | Eligible when                                      |
| ------------------------- | ------------------------------------------------ | -------------------------------------------------- |
| Removal with query access | Each of the 10 watermarking outputs              | The output is flagged and passes the quality check |
| Forgery with the key      | Each of the 10 unmarked originals                | The original is not flagged                        |
| Forgery with query access | The 5 unmarked originals selected in Section 4.1 | The original is not flagged                        |

Set query and editing-time budgets before each attack. Suggested limits are 100 requests and 15 minutes per passage for each variant or configuration. The three character-change tests share one budget per passage. Manual and automated attacks must follow the assigned access level. Query-access attacks must not reuse word colors or editing records learned during keyed watermarking.

#### Attack 1: remove the watermark using detector queries

For every eligible watermarked output, run both variants:

- **Word substitution:** use detector responses to guide replacements that preserve meaning and readability.
- **Character changes:** test letter case, punctuation, and zero-width characters separately. Zero-width Unicode characters occupy no visible space but may affect tokenization or normalization.

Start each variant and character-change test from a fresh copy of the watermarked output. Predict which character changes your word-processing rules will remove or ignore, then submit the edited text and record the response.

Removal succeeds when the detector returns an unflagged decision and the edited text passes the quality check against **both** the watermarked input and original prose. This checks for meaning changes across both editing stages. Errors and rejected requests do not count as successful removal.

Report successes and costs separately for word substitution and each character-change test. For the overall character-change rate, count a passage as successful if any of its three tests succeeds; include costs from all three. Divide each success count by eligible watermarked outputs. Explain results using your tokenization and normalization rules.

#### Attack 2: forge a watermark using the key

Score all 10 unmarked originals. Record already-flagged originals as false positives and exclude them from attack-success calculations.

For each eligible original, use the key to find green synonyms and trigger the detector. This tests forgery after key disclosure. Success requires a flagged output that passes the quality check against the original.

Report successes divided by eligible originals, including separate results for the 5 selected for query-access forgery.

#### Attack 3: forge a watermark using detector queries

Demonstrate color disclosure by submitting repetitions of one word. Its score is either 0 or 1. For any threshold `0 <= threshold < 1`, a binary response reveals the color: flagged means green; unflagged means red. Explain why score hiding and minimum total word counts fail to prevent this disclosure.

Use colors learned through detector queries to guide substitutions in each eligible original among the 5 passages selected in Section 4.1. Forgery requires flagged prose that passes the quality check against the original. Report already-flagged originals as false positives and exclude them from the attack without selecting replacement passages.

Run this attack under all three service configurations:

| Configuration | Response visible to attacker | Rate limit          |
| ------------- | ---------------------------- | ------------------- |
| A             | Green fraction and decision  | Disabled            |
| B             | Green fraction and decision  | Enabled             |
| C             | Decision only                | Same allowance as B |

For each configuration:

1. Reset service state, including request counters, through the experiment driver. Clear the attacker's learned word colors.
2. Set a separate preparation budget, such as 100 requests, for learning colors. Include the repeated-word demonstration queries.
3. Attempt forgery on every eligible original within the per-passage budgets. Learned colors may be reused across passages within a configuration.
4. Report preparation and editing queries separately, with elapsed time for each. Rate limits may increase time without increasing the required queries.

Use the same key, passages, and budgets across configurations. Compare what the attacker learned, requests used, elapsed time, and successful forgeries within budget. Compare key and query access on the same eligible originals from the selected 5 passages.

#### Record and interpret the results

For every attack variant or configuration, report:

- The number of eligible passages, attempts, and successes. Include failed attempts when calculating success rates.
- Submitted requests, including rejections, and elapsed or simulated time. Record manual editing effort and automated work.
- Changed-word counts and quality-check results.
- For removal, the starting score and how far it was above the threshold. The experiment driver may record a score for analysis even when the attacker cannot see it.

If no passages are eligible, report the rate as **not applicable** and explain why. Demonstrate the attack on one labeled artificial example, excluded from prose success rates.

Apply the small-sample guidance in Section 4.2. Comparisons between access levels and service configurations use at most 5 eligible passages. Explain what the results show about these passages and what remains untested.

Optional experiments may test faster color-learning methods, defenses, or alternate normalization rules. Explain each method and measure query cost under your service's score precision and input limits. Measure defenses' effects on legitimate queries. Report alternate normalization results separately.

### 5.3 Write the policy memo

Advise a hypothetical operator whether and under what conditions to deploy the service. Support the recommendation with your error measurements and attack results. Address:

- **Recommended use:** whether to deploy the service and which uses you would refuse, based on measured errors and attack results. A recommendation against deployment can earn full credit when justified by those results.
- **Detection errors:** the chosen threshold, measured error counts, uncertainty, and annual false-flag estimate from Section 4.2. Explain how differences between your test data and the intended submissions affect that estimate.
- **Access:** who may submit text and inspect logs, and how the service enforces those permissions.
- **Retention:** which data and query metadata are stored, for how long, and who can access them.
- **Review:** how an affected person can learn the basis of a flag and appeal it, and what additional evidence a cheating allegation would require.
- **Key disclosure:** what the operator should do if someone obtains the secret key, including how to reassess earlier detection results.

Assess a proposal to assign each account a different watermark key and test documents against those keys to identify matching accounts. Discuss tracking risks, copying, forgery, false positives, and the increased opportunity for false matches when testing multiple keys. Include this written assessment in the memo.

## 6. Grading

The project is graded out of 100 points. Milestone 1 contributes 45 points and Milestone 2 contributes 55 points.

| Component                             |        Points | Basis for assessment                                                                                                                                                                                       |
| ------------------------------------- | ------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1: detector                          |            10 | Correct scoring and threshold comparison (5); documented word processing, counts, and empty-input handling (5).                                                                                            |
| M1: evaluation                        |            15 | Separate calibration and evaluation with fixed settings (5); complete detection and quality results, including failures (5); length, repetition, uncertainty, and false-flag interpretation (5).          |
| M1: threat model                      |            20 | All six goal/access cells with strategies and costs (12); key distribution, context dependence, and signature comparison (8).                                                                              |
| M2: service                           |            10 | Authentication and role enforcement (4); logging and persistent rate limiting (4); documented boundary and response modes (2).                                                                             |
| M2: attacks                           |            20 | Removal variants (5); key-access forgery (5); query-access leakage, usable forgery attempts, and three-configuration comparison (10). Each part requires costs, quality checks, and unsuccessful attempts. |
| M2: policy memo                       |            20 | Evidence and deployment limits (5); authorization and retention (5); appeals and key disclosure (5); account tracking and refused uses (5).                                                                |
| M2: reproducibility and contributions |             5 | Runnable setup, documented data sources, and saved outputs (3); contribution statements and relevant commit history for both milestones (2).                                                                       |
| **Total**                       | **100** |                                                                                                                                                                                                            |

Complete all listed deliverables and attack attempts. Missing work earns no credit for its criteria. Partial credit depends on the code, measurements, and explanations submitted. Failed attacks can earn full credit if the code follows the specified access rules, the budgets and results are recorded, and the report explains the failure. Optional color-learning methods count toward the query-access attack criteria. For each conclusion, identify the supporting results and the conditions under which it applies.

## 7. Ethics and conduct

Attack only your team's local service. Use fictional attribution scenarios and cite reusable source material. Obtain consent before submitting real student or employee work. Do not accuse real authors or publish fabricated attribution claims.

Submit attack code with the project. Discuss any relevance to real services and appropriate disclosure in the report; testing those services or releasing tools targeting them is prohibited. Use demonstration credentials and keys.

## 8. Suggested work schedule

- **Week 1:** form the team, create the repository, read the watermarking introduction and required reading, implement word processing and scoring, and identify data sources.
- **Week 2:** divide the passages into calibration and evaluation sets, select the 5 passages for query-access forgery, practice watermarking, choose the detection threshold, and draft the threat table.
- **Week 3:** fix the settings, run evaluation, and record quality checks and limitations.
- **Week 4:** complete Milestone 1 and its contribution statement.
- **Week 5:** build the service interface, account controls, logs, and rate limit that persists across client restarts.
- **Week 6:** run the required attacks and preserve all outputs, including failures.
- **Week 7:** compare service configurations and draft the policy memo.
- **Week 8:** check reproducibility, complete the analysis, and submit Milestone 2.

Share implementation, experiments, and writing across team members.
