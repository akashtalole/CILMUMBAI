# Ward audit rubric

- `/mnt/session/outputs/ward-brief.md` exists, is at most about 450 words, and names the ward.
- Every amount, date, tender or work number and contractor name in the brief and in each case file is followed by a fact id in square brackets, taken from a tool result.
- Each case file has an evidence table, a "what is not known" section, and a record that would settle it with the office that holds it.
- Each case file has a `.challenge.md` review beside it ending in `Verdict: publish`, `Verdict: publish with changes` or `Verdict: hold`.
- Every change a review asked for has been made in the case file it reviews.
- Case files with `Verdict: hold` are in `held/`, not in `cases/`.
- No file uses the words fraud, scam, corrupt, cartel, nexus or siphoned, or Marathi or Hindi words with the same meaning, and no official is named except by post.
- `/mnt/session/outputs/gaps.jsonl` has one JSON object per missing record, with `record_needed` and `holder`.
- Each gap has an RTI application in `drafts/`, addressed to a Public Information Officer and asking for documents by name and period.
- `drafts/questions.md` has three questions, each with fact ids.
- Where a check found nothing, the brief says so instead of leaving the section out.
