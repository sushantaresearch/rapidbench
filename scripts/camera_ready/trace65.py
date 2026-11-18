r"""Trace every number in the revised (\rev{}) text of the Paper 65 camera-ready.

Usage: python3 -I trace65.py <review_tex> <orig_tex> <analysis65.json> <rdm_l1_check.json> <grid_synthetic.csv> <grid_ctgan.csv> <grid_date.csv>
Each check recomputes the expected literal from the JSON or the frozen grid CSVs and
asserts that the literal appears in the revised text. Numbers carried over from the
submitted paper are listed as such (they were verified against results/ before
submission). Exits non-zero if a check fails or a number is untraced.
"""
import json, re, sys
import pandas as pd

TEX, ORIG, AJ, LJ, GA, GC, GB = sys.argv[1:8]
tex = open(TEX, encoding="utf-8").read()
orig = open(ORIG, encoding="utf-8").read()
A = json.load(open(AJ)); L = json.load(open(LJ))
gA = pd.read_csv(GA); gC = pd.read_csv(GC); gB = pd.read_csv(GB)
for g in (gA, gB, gC):
    g["cls"] = g.injector.str[:3]

def revs(s):
    out, i = [], 0
    while True:
        j = s.find("\\rev{", i)
        if j < 0:
            return out
        if s[j - 1:j] == "{" and s[j - 13:j] == "\\newcommand{\\":  # the macro definition itself
            i = j + 5; continue
        k, d = j + 5, 1
        while d:
            d += {"{": 1, "}": -1}.get(s[k], 0); k += 1
        out.append(s[j + 5:k - 1]); i = k

R = "\n".join(revs(tex))
T1 = A["t=0.01"]; f1 = lambda x: f"{x:.1f}"

pairs = {t: sorted((s, c) for s in ("S-A", "S-B", "S-C") for c in A[t][s]["silent_net_by_class"]) for t in ("t=0.005", "t=0.01", "t=0.02")}
same_pairs = pairs["t=0.005"] == pairs["t=0.01"] == pairs["t=0.02"] and len(pairs["t=0.01"]) == 6
f01_mean = gA[gA.cls == "F01"].rdm_S2_duty_by_chapter.mean()
f06_p20 = gA[(gA.cls == "F06") & (gA.severity == 0.2)].max_rdm.mean()
f09_p20 = gA[(gA.cls == "F09") & (gA.severity == 0.2)].max_rdm.mean()

checks = [  # (literal in revised text, expected literal, source)
 (f"{T1['S-A']['rate_net_pct']}\\%, {T1['S-B']['rate_net_pct']}\\%, and {T1['S-C']['rate_net_pct']}\\% per substrate", "10.6\\%, 17.3\\%, and 7.5\\% per substrate", "per-substrate net silent rates"),
 (f"10.6\\% (S-A), 17.3\\% (S-B; 95\\% CI $[{T1['S-B']['ci_net'][0]}, {T1['S-B']['ci_net'][1]}]$)", "10.6\\% (S-A), 17.3\\% (S-B; 95\\% CI $[11.6, 24.4]$)", "S-B rate and exact CI"),
 (f"7.5\\% (S-C; $[{T1['S-C']['ci_net'][0]}, {T1['S-C']['ci_net'][1]}]$)", "7.5\\% (S-C; $[3.5, 13.8]$)", "S-C rate and exact CI"),
 (f"all {T1['S-B']['cells']} S-B cells", "all 150 S-B cells", "S-B cells (R4 fires in all: S-B_cells_R4_fired=%d)" % A["S-B_cells_R4_fired"]),
 (f"S-B gives {T1['S-B']['silent_raw']} silent cells raw but {T1['S-B']['silent_net']} net", "S-B gives 0 silent cells raw but 26 net", "S-B raw vs net"),
 ("(F04 %d, F09 %d, F10 %d)" % tuple(T1["S-B"]["silent_net_by_class"][c] for c in ("F04", "F09", "F10")), "(F04 7, F09 4, F10 15)", "S-B net silent by class"),
 ("$54 = %d + %d + %d$" % (T1["S-A"]["silent_net"], T1["S-B"]["silent_net"], T1["S-C"]["silent_net"]), "$54 = 19 + 26 + 9$", "net decomposition"),
 ("$28 = %d + %d + %d$" % (T1["S-A"]["silent_raw"], T1["S-B"]["silent_raw"], T1["S-C"]["silent_raw"]), "$28 = 19 + 0 + 9$", "raw decomposition"),
 ("eight classes" if len(A["common_classes"]) == 8 else "??", "eight classes", "common classes: " + ",".join(A["common_classes"])),
 ("(120 cells each)" if all(T1[s]["common_cells"] == 120 for s in ("S-A", "S-B", "S-C")) else "??", "(120 cells each)", "common cells per substrate"),
 ("only F09 is silent (%d, %d, and %d\ncells; %s\\%% of %d)" % (T1["S-A"]["common_silent_by_class"]["F09"], T1["S-B"]["common_silent_by_class"]["F09"], T1["S-C"]["common_silent_by_class"]["F09"], T1["pooled"]["common_rate_pct"], T1["pooled"]["common_cells"])
     if all(list(T1[s]["common_silent_by_class"]) == ["F09"] for s in ("S-A", "S-B", "S-C")) else "??",
  "only F09 is silent (9, 4, and 9\ncells; 6.1\\% of 360)", "common-class silent cells"),
 ("The same six class-substrate pairs" if same_pairs else "??", "The same six class-substrate pairs", "silent pairs identical at 0.5%, 1%, 2%: " + str(pairs["t=0.01"])),
 (f"RDM {100 * L['rdm_S2']:.1f}\\%, so {100 * L['reallocated_share_mass']:.1f}\\% of duty", "RDM 53.9\\%, so 27.0\\% of duty", "F01 seed 42 (rdm_l1_check.json); ratio %.3f" % L["ratio_rdm_over_moved"]),
 (f"puts {100 * f01_mean / 2:.0f}\\% of duty in the\nwrong chapter (RDM {100 * f01_mean:.0f}\\%)", "puts 27\\% of duty in the\nwrong chapter (RDM 54\\%)", "F01 mean over seeds on S-A"),
 (f"(up to {A['max_rdm_pct']['S-C']['F09']}\\% distortion)" if A["max_rdm_pct"]["S-C"]["F09"] == max(A["max_rdm_pct"][s]["F09"] for s in ("S-A", "S-B", "S-C")) else "??", "(up to 8.4\\% distortion)", "F09 max RDM over substrates"),
 (f"(mean\nmax-RDM {100 * f06_p20:.1f}\\% at $p{{=}}0.20$)", "(mean\nmax-RDM 6.7\\% at $p{=}0.20$)", "F06 mean max-RDM at p=0.20 on S-A (F09 at p=0.20: %.1f%%)" % (100 * f09_p20)),
 (f"(up to {A['max_rdm_pct']['S-B']['F10']}\\%)", "(up to 20.2\\%)", "F10 max RDM on S-B"),
]
bad = 0
ws = lambda x: " ".join(x.split())
RW = ws(R)
for lit, exp, src in checks:
    ok = (ws(lit) == ws(exp)) and (ws(exp) in RW)
    print(("OK  " if ok else "FAIL") + f" {ws(exp)!r:62s} [{src}]" + ("" if ws(exp) in RW else "  (literal not in revised text)"))
    bad += not ok

# every number in revised text must be covered by a check, the original paper, or a stated source
sourced = {"320": "ISA 320 (IAASB PDF)", "7": "para. A7 / F04 7", "2013": "IAASB handbook year",
           "42": "seed 42 (rdm_l1_check.json)", "5": "S_3--S_5 (executor.py CONTRACT_KEYS: five statistics)",
           "3": "S_3 (statistic index)", "1": "S_1 / 1% gate (original)", "0.5": "threshold (original)", "2": "threshold (original)"}
covered = set()
for lit, exp, src in checks:
    covered.update(re.findall(r"\d+(?:\.\d+)?", exp))
strip = lambda s: re.sub(r"\\(?:ref|eqref|cite|label|path)(?:\[[^\]]*\])?\{[^}]*\}|F\d\d|R\d|S-[ABC]|V1b?|V[23]|E[1-4]|S_\d|S_[1-6]--S_[1-6]", "", s)
orig_nums = set(re.findall(r"\d+(?:\.\d+)?", orig))
untraced, carried = [], []
for n in sorted(set(re.findall(r"\d+(?:\.\d+)?", strip(R))), key=float):
    if n in covered:
        continue
    if n in sourced:
        print(f"SRC  {n:8s} {sourced[n]}"); continue
    if n in orig_nums:
        carried.append(n); continue
    untraced.append(n)
print("carried over from the submitted paper:", ", ".join(carried))
print("UNTRACED:", untraced if untraced else "none")
sys.exit(1 if (bad or untraced) else 0)
