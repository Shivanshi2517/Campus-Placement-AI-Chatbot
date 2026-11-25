"""The 3 extra features: Resume Analyzer, Eligibility Checker, Mock Quiz."""
import json, random, re
from pathlib import Path

DATA = Path(__file__).parent / "data"
ROLES = json.loads((DATA / "roles.json").read_text(encoding="utf-8"))
COMPANIES = json.loads((DATA / "companies.json").read_text(encoding="utf-8"))["companies"]
QUIZ = json.loads((DATA / "quiz.json").read_text(encoding="utf-8"))["questions"]


# ---------- Feature 1: Resume analyzer ----------
def _has(text, term):
    return re.search(r"(?<![a-z0-9+#])" + re.escape(term) + r"(?![a-z0-9+#])", text) is not None


def analyze_resume(text, role):
    text_l = text.lower()
    wanted = ROLES["roles"].get(role)
    if wanted is None:
        raise ValueError("Unknown role")

    found = [s for s in wanted if _has(text_l, s)]
    missing = [s for s in wanted if s not in found]
    skill_score = 55 * len(found) / len(wanted)

    sections = {name: any(_has(text_l, k) for k in keys) for name, keys in ROLES["sections"].items()}
    section_score = 20 * sum(sections.values()) / len(sections)

    numbers = re.findall(r"\d+\s?%|\b\d{2,}\+?\b", text)
    impact_score = min(len(numbers), 5) * 2            # up to 10
    verbs = ["developed", "built", "designed", "implemented", "created", "led", "improved", "optimized", "reduced", "deployed"]
    verb_score = min(sum(_has(text_l, v) for v in verbs), 5)  # up to 5
    words = len(text.split())
    length_score = 10 if 150 <= words <= 700 else 4 if words >= 80 else 0

    total = round(skill_score + section_score + impact_score + verb_score + length_score)
    tips = []
    if missing:
        tips.append("Add (only if you truly know them): " + ", ".join(missing[:6]) + ".")
    for name, ok in sections.items():
        if not ok:
            tips.append(f"Add a '{name}' section.")
    if impact_score < 6:
        tips.append("Quantify your work with numbers/percentages (e.g., 'improved accuracy by 12%').")
    if verb_score < 3:
        tips.append("Start bullet points with strong action verbs: built, designed, optimized, deployed.")
    if words < 150:
        tips.append("Your resume looks too short; add project details and your tech stack.")
    if words > 700:
        tips.append("Your resume is long; keep it to one page for fresher roles.")
    grade = "Excellent" if total >= 80 else "Good" if total >= 60 else "Needs work" if total >= 40 else "Weak"
    return {"score": min(total, 100), "grade": grade, "role": role, "found_skills": found,
            "missing_skills": missing, "sections": sections, "word_count": words, "tips": tips}


# ---------- Feature 2: Eligibility checker ----------
def check_eligibility(cgpa, tenth, twelfth, backlogs, branch):
    results = []
    for c in COMPANIES:
        reasons = []
        if cgpa < c["min_cgpa"]:
            reasons.append(f"CGPA {cgpa} is below required {c['min_cgpa']}")
        if tenth < c["min_10th"]:
            reasons.append(f"10th {tenth}% is below required {c['min_10th']}%")
        if twelfth < c["min_12th"]:
            reasons.append(f"12th {twelfth}% is below required {c['min_12th']}%")
        if backlogs > c["max_backlogs"]:
            reasons.append(f"{backlogs} backlog(s) exceed the allowed {c['max_backlogs']}")
        if branch not in c["branches"]:
            reasons.append(f"{branch} branch is not eligible")
        results.append({"company": c["name"], "eligible": not reasons, "reasons": reasons,
                        "package": c["package"], "rounds": c["rounds"]})
    results.sort(key=lambda r: (not r["eligible"], r["company"]))
    return results


# ---------- Feature 3: Mock aptitude quiz ----------
def get_quiz(category=None, n=5):
    pool = [q for q in QUIZ if category in (None, "", "All") or q["category"] == category]
    chosen = random.sample(pool, min(n, len(pool)))
    return [{k: q[k] for k in ("id", "category", "q", "options")} for q in chosen]


def grade_quiz(answers):
    by_id = {q["id"]: q for q in QUIZ}
    review, correct = [], 0
    for qid, picked in answers.items():
        q = by_id.get(int(qid))
        if not q:
            continue
        ok = int(picked) == q["answer"]
        correct += ok
        review.append({"id": q["id"], "q": q["q"], "your": q["options"][int(picked)] if 0 <= int(picked) < 4 else "-",
                       "correct": q["options"][q["answer"]], "is_correct": ok, "explain": q["explain"]})
    total = len(review)
    pct = round(100 * correct / total) if total else 0
    msg = "Great job!" if pct >= 80 else "Good, keep practising." if pct >= 50 else "Revise the basics and try again."
    return {"correct": correct, "total": total, "percent": pct, "message": msg, "review": review}
