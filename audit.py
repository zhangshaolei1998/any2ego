#!/usr/bin/env python3
"""AI-writing-pattern audit for main.tex: banned vocabulary, the 25 patterns,
and self-undermining or pre-emptive hedging."""
import re, sys
from collections import defaultdict

PATH = sys.argv[1] if len(sys.argv) > 1 else "main.tex"
raw = open(PATH, encoding="utf-8").read()

body = raw.split(r"\begin{abstract}")[1].split(r"\bibliographystyle")[0]
body = re.sub(r"\n%[^\n]*", "", body)

lines = body.split("\n")
issues = defaultdict(list)
def add(cat, ln, txt): issues[cat].append((ln, txt))

BANNED = """accentuate adorn amass ameliorate amplify alleviate ascertain advocate articulate
bolster bustling cherish conceptualize conjecture consolidate convey culminate decipher
demonstrate demonstrates demonstrating depict depicts devise delineate delve diverge disseminate
elucidate endeavor enumerate envision enduring exacerbate expedite foster galvanize harmonize
hone innovate inscription interpolate intricate lasting leverage leverages leveraging manifest mediate
nurture nuance nuanced perpetuate permeate pivotal ponder prescribe prevailing profound
recapitulate reconcile rectify rekindle reimagine scrutinize substantiate tapestry testament
transcend traverse underscore underscores unveil vibrant showcase showcases showcasing""".split()
# context-dependent members of the list, flagged but judged by hand
SOFT = {"integrate", "integrates", "integrating", "engage", "engages", "opt", "opts",
        "perceive", "perceives", "obscure", "bear", "bears", "originates"}

PATTERNS = [
    (1, "not X but Y", r"\b(?:and|is|are|was|were)\s+not\s+(?:a|an|the|only|just|merely|as)\b|\bnot\s+\w+\s+but\b|\bdoes\s+not\s+\w+\s+it\b"),
    (3, "saying that sounds deep", r"\bat its core\b|\bat the heart of\b|\bthe key insight is\b|\bfundamentally,"),
    (4, "staged run-up", r"\blet us\b|\blet's\b|\bit is worth noting\b|\bnote that\b|\bimportantly,\s"),
    (5, "arguing with no one", r"\ba tempting\b|\bone might (?:think|argue|expect)\b|\bthis is not mainly\b|\bit would be tempting\b"),
    (9, "stacked qualifiers", r"\b(?:could|may|might)\s+(?:potentially|possibly|conceivably)\b|\bpotentially possibly\b"),
    (12, "inflated significance", r"\bmarking a\b|\bpaves? the way\b|\ba major step\b|\bthe future looks\b|\bgroundbreaking\b|\bremarkable\b|\bcompelling\b"),
    (14, "vague connection", r"\bassociated with\b|\bin connection with\b|\brelated to the fact\b"),
    (15, "shallow -ing rider", r",\s+(?:reflecting|symbolizing|highlighting|emphasizing|underlining)\b"),
    (16, "sales language", r"\bstate-of-the-art\b|\bcutting-edge\b|\bpowerful\b|\bseamless\b|\bnestled\b"),
    (17, "borrowed authority", r"\bexperts? (?:believe|agree|say)\b|\bit is (?:widely|generally) (?:believed|accepted)\b"),
    (18, "avoiding is/are/has", r"\bserves? as\b|\bboasts?\b|\bfeatures? a\b|\bcomes? with\b"),
    (22, "chatbot residue", r"\bgreat question\b|\bi hope this helps\b|\bin conclusion,\s|\bto summarize,\s"),
    (23, "knowledge-limit disclaimer", r"\bwhile details are limited\b|\bit appears that\b|\bto the extent that we can\b|\bas far as we can tell\b"),
    (25, "writing about the previous version", r"\bwas (?:added|changed|replaced) to\b|\bpreviously,? (?:we|the)\b|\bin an earlier\b"),
]

DEFENSIVE = [
    ("self-undermining", r"\bwe do not claim\b|\bnot as a contribution\b|\bnot a (?:bit-exact|direct) reproduction\b|\bwe make no claim\b|\bthis is not a\b"),
    ("pre-emptive disclaimer", r"\brather than a claim\b|\bshould not be (?:read|taken) as\b|\bwe caution\b|\bfor completeness\b|\bwe report the effect\b"),
    ("hedged own result", r"\bonly approximates\b|\bmay not\b|\bis limited to\b|\bwe cannot\b|\bremains? open\b|\bremains? a separate question\b"),
]

for i, l in enumerate(lines, 1):
    s = l.strip()
    if not s or s.startswith("%") or s.startswith("\\label"):
        continue
    low = s.lower()
    for w in re.findall(r"[A-Za-z][A-Za-z-]+", low):
        if w in BANNED: add("V-banned", i, w)
        elif w in SOFT: add("V-soft", i, w)
    for num, name, pat in PATTERNS:
        m = re.search(pat, low)
        if m: add(f"P{num:02d} {name}", i, m.group(0))
    for name, pat in DEFENSIVE:
        m = re.search(pat, low)
        if m: add(f"D  {name}", i, m.group(0))

# 6. forced triads of abstract nouns
for m in re.finditer(r"\b(\w+), (\w+), and (\w+)\b", body):
    a, b, c = m.groups()
    if all(len(x) > 6 and not x[0].isupper() and not x[0].isdigit() for x in (a, b, c)):
        ln = body[:m.start()].count("\n") + 1
        add("P06 forced triad", ln, m.group(0))

# 7. repeated sentence openings within a paragraph
for para in re.split(r"\n\s*\n", body):
    sents = re.split(r"(?<=[.!?])\s+", " ".join(para.split()))
    heads = [" ".join(x.split()[:2]).lower() for x in sents if len(x.split()) > 3]
    for h in set(heads):
        if heads.count(h) > 1 and h.split()[0] not in ("the", "a", "we", "it", "this"):
            add("P07 repeated opening", 0, f"{h!r} x{heads.count(h)}")

# 8/21. dashes and curly quotes
for i, l in enumerate(lines, 1):
    if "---" in l or "\u2014" in l: add("P08 dash", i, "em dash")
    if "\u201c" in l or "\u201d" in l: add("P21 curly quote", i, "curly quote")

# 19/20. decorative bold and headings
for m in re.finditer(r"\\(?:sub)?section\*?\{([^}]*)\}", body):
    t = m.group(1)
    if re.search(r"[\U0001F300-\U0001FAFF]|→|✓", t): add("P20 decorative heading", 0, t)

# 24. heading echoed by the first sentence
for m in re.finditer(r"\\(?:sub)?section\*?\{([^}]*)\}\s*(?:\\label\{[^}]*\}\s*)?\n+([^\n]{0,120})", body):
    head, first = m.group(1).lower(), m.group(2).lower()
    key = [w for w in re.findall(r"[a-z]{5,}", head)]
    if key and sum(w in first for w in key) >= 2:
        add("P24 heading echoed", 0, f"{m.group(1)} -> {m.group(2)[:60]}")

total = 0
for k in sorted(issues):
    seen = issues[k]
    total += len(seen)
    print(f"\n## {k}  ({len(seen)})")
    for ln, t in seen[:25]:
        print(f"   L{ln}: {t}")
    if len(seen) > 25: print(f"   ... {len(seen)-25} more")
print(f"\nTOTAL: {total}")
