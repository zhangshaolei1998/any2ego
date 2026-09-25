#!/usr/bin/env python3
"""Style and consistency linter for main.tex (Any2Ego / ICLR 2027).

Checks the hard requirements:
  A. banned AI-ish tokens in prose (em dash, semicolon, prose colon, "rather")
  B. vague / hedging phrasing
  C. table hygiene (font size, footnote markers, caption on top)
  D. figure caption on top
  E. numeric consistency across tables and prose
  F. structural requirements (5 intro paragraphs, 3 contributions, paragraph caps)
"""
import re
import sys
from collections import defaultdict

PATH = sys.argv[1] if len(sys.argv) > 1 else "main.tex"
src = open(PATH, encoding="utf-8").read()
lines = src.split("\n")

issues = defaultdict(list)


def add(cat, ln, msg):
    issues[cat].append((ln, msg))


# ---------- helpers: identify prose vs non-prose lines ----------
def prose_mask():
    """Return set of line numbers that are prose (outside tables, math, verbatim, bib)."""
    ok = set()
    depth_env = []
    in_bib = False
    for i, l in enumerate(lines, 1):
        s = l.strip()
        if s.startswith("%"):
            continue
        if "\\begin{thebibliography}" in s:
            in_bib = True
        if "\\end{thebibliography}" in s:
            in_bib = False
            continue
        if in_bib:
            continue
        m = re.findall(r"\\begin\{(\w+\*?)\}", s)
        for e in m:
            depth_env.append(e)
        blocked = {"tabular", "equation", "align", "aligned", "lstlisting",
                   "verbatim", "table", "table*", "figure", "figure*", "gather"}
        if not (set(depth_env) & blocked):
            ok.add(i)
        for e in re.findall(r"\\end\{(\w+\*?)\}", s):
            if e in depth_env:
                depth_env.remove(e)
    return ok


PROSE = prose_mask()

# ---------- A. banned tokens ----------
for i, l in enumerate(lines, 1):
    s = l.strip()
    if s.startswith("%") or i not in PROSE:
        continue
    if "---" in s:
        add("A-emdash", i, "em dash '---'")
    if re.search(r"(?<!\\);", s):
        add("A-semicolon", i, "semicolon")
    if re.search(r"\brather\b", s, re.I):
        add("A-rather", i, '"rather"')
    # prose colon: a colon followed by space+lowercase/uppercase word, not in \item label,
    # not in url/ref/citation
    for m in re.finditer(r"(?<!\\):(?!=)", s):
        seg = s[max(0, m.start() - 40):m.start()]
        if ("\\item" in seg or "http" in s or "\\url" in s or "\\ref" in seg
                or "\\title" in s or "\\texttt" in seg):
            continue
        if re.match(r"\s+\S", s[m.end():m.end() + 3] or " x"):
            add("A-colon", i, "prose colon")
            break

# ---------- B. vague phrasing ----------
VAGUE = [
    r"\bsignificantly (?:improv|reduc|outperform|enhanc)", r"\bcompetitive performance\b",
    r"\bvarious (?:aspects|factors)\b", r"\bplays? a (?:crucial|vital|key) role\b",
    r"\bit is worth noting\b", r"\bto some extent\b", r"\brich(?:er)? semantics?\b",
    r"\bdelve\b", r"\bseamless(?:ly)?\b", r"\bleverag(?:e|ing) the power\b",
    r"\bparadigm shift\b", r"\bnovel(?:ty)? approach\b", r"\bwe observe that\b",
    r"\bwe found that\b", r"\bmay potentially\b", r"\bquite\b",
]
for i, l in enumerate(lines, 1):
    if i not in PROSE or l.strip().startswith("%"):
        continue
    for p in VAGUE:
        if re.search(p, l, re.I):
            add("B-vague", i, re.search(p, l, re.I).group(0))

# ---------- C/D. float hygiene ----------
float_blocks = []
i = 0
while i < len(lines):
    m = re.match(r"\s*\\begin\{(table\*?|figure\*?)\}", lines[i])
    if m:
        kind = m.group(1)
        j = i
        while j < len(lines) and not re.match(r"\s*\\end\{" + re.escape(kind) + r"\}", lines[j]):
            j += 1
        float_blocks.append((kind, i + 1, j + 1, "\n".join(lines[i:j + 1])))
        i = j
    i += 1

for kind, a, b, body in float_blocks:
    cap = body.find("\\caption")
    gfx = max(body.find("\\begin{tabular}"), body.find("\\includegraphics"))
    if cap >= 0 and gfx >= 0:
        if kind.startswith("table") and cap > gfx:
            add("C-caption-order", a, "table: caption must be above the tabular")
        if kind.startswith("figure") and cap < gfx:
            add("C-caption-order", a, "figure: caption must be below the graphic")
    if kind.startswith("table"):
        if "\\small" not in body:
            add("C-tablesize", a, "table without \\small")
        for bad in ["\\scriptsize", "\\tiny", "\\footnotesize"]:
            if bad in body:
                add("C-tablesize", a, f"table uses {bad}")
        if re.search(r"\$\^\{?[\*†]\}?\$|\^\{\*\}|(?<!\\)\\\*", body):
            add("C-tablemark", a, "footnote marker in table")
    if "\\label" not in body:
        add("C-nolabel", a, f"{kind} without label")
    if cap >= 0:
        cbody = body[cap:cap + 400]
        if len(cbody) < 60:
            add("C-thincaption", a, f"{kind}: caption may be too short to be a take-away")

# ---------- E. numeric consistency ----------
# collect all numbers with 3+ significant digits and their lines, grouped by value family
NUM = re.compile(r"(?<![\w.])(\d+\.\d+)(?![\w])")
seen = defaultdict(list)
for i, l in enumerate(lines, 1):
    if l.strip().startswith("%"):
        continue
    for m in NUM.finditer(l):
        seen[m.group(1)].append(i)

# known canonical values: report any near-duplicate that differs only by rounding
canon = {
    "ssim": ["0.608", "0.636", "0.660", "0.601", "0.618", "0.632", "0.423",
             "0.178", "0.368", "0.553", "0.574", "0.578", "0.438"],
    "psnr": ["21.06", "21.74", "22.28", "21.88", "21.22", "21.59", "16.38",
             "10.14", "12.30", "20.74", "20.85", "21.09", "16.10"],
    "lpips": ["0.194", "0.163", "0.144", "0.184", "0.166", "0.504",
              "0.711", "0.844", "0.225", "0.210", "0.211", "0.386"],
    "fvd": ["42.6", "37.8", "33.3", "357.2", "44.5", "1118.7", "2361.1",
            "127.6", "121.6", "148.3", "177.0"],
}
allowed = {v for vs in canon.values() for v in vs}
variants = {
    "0.6084": "0.608", "0.6358": "0.636", "0.6603": "0.660", "0.6181": "0.618",
    "0.6315": "0.632", "0.4234": "0.423", "0.1937": "0.194", "0.1631": "0.163",
    "0.1440": "0.144", "0.1838": "0.184", "0.1661": "0.166", "0.5042": "0.504",
    "42.63": "42.6", "37.76": "37.8", "33.34": "33.3", "44.52": "44.5",
    "22.284": "22.28", "21.586": "21.59", "16.379": "16.38",
}
for v, canon_v in variants.items():
    if v in seen:
        add("E-precision", seen[v][0],
            f"{v} appears (use {canon_v} for one consistent precision); lines {seen[v]}")

# ---------- F. structure ----------
def section_body(name):
    m = re.search(r"\\section\{" + name + r"\}", src)
    if not m:
        return ""
    nxt = re.search(r"\\section\*?\{", src[m.end():])
    return src[m.end(): m.end() + (nxt.start() if nxt else len(src))]


intro = section_body("Introduction")
if intro:
    # count prose paragraphs, excluding floats and the itemize block
    tmp = re.sub(r"\\begin\{(figure\*?|table\*?|itemize|equation)\}.*?\\end\{\1\}", "", intro, flags=re.S)
    tmp = "\n".join(l for l in tmp.split("\n") if not l.strip().startswith("%"))
    paras = [p for p in re.split(r"\n\s*\n", tmp) if len(p.strip()) > 120]
    if len(paras) != 5:
        add("F-intro", 0, f"introduction has {len(paras)} prose paragraphs, expected 5")
    items = re.findall(r"\\item", intro)
    if len(items) != 3:
        add("F-contrib", 0, f"introduction has {len(items)} contribution items, expected 3")
    for it in re.findall(r"\\item\s*(.{0,30})", intro):
        if "\\textbf" not in it:
            add("F-contrib", 0, f"contribution item does not start with \\textbf: {it!r}")

# paragraph caps: every \textbf{...}\quad paragraph should begin with purpose
for i, l in enumerate(lines, 1):
    if re.match(r"\s*\\textbf\{[^}]+\.\}\\quad", l) and i in PROSE:
        tail = l.split("\\quad", 1)[1].strip()
        if tail and not re.match(r"(To |In order to |We |Given |Since |Building|Beyond|Unlike|As |Existing |A parallel )", tail):
            add("F-paracap", i, f"paragraph may lack a purpose-first cap: {tail[:60]!r}")

# ---------- report ----------
total = sum(len(v) for v in issues.values())
order = sorted(issues.keys())
for k in order:
    print(f"\n## {k}  ({len(issues[k])})")
    for ln, msg in issues[k][:40]:
        print(f"  L{ln}: {msg}")
    if len(issues[k]) > 40:
        print(f"  ... {len(issues[k]) - 40} more")
print(f"\nTOTAL ISSUES: {total}")
sys.exit(0)
