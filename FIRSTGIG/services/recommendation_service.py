from datetime import date
from models import Gig, Project
from services.level_service import level_for_completed, difficulty_for_level


def recommend_gigs(student_user, limit=6):
    profile = student_user.student_profile
    if not profile:
        return []

    skills = {s.lower() for s in profile.skill_list()}
    interests = {s.lower() for s in profile.interest_list()}
    level = level_for_completed(profile.completed_gigs)
    budget_lo, budget_hi = level["budget"]
    preferred_diff = difficulty_for_level(level["key"])

    completed_cats = set()
    for p in Project.query.filter_by(student_id=student_user.id, status="COMPLETED").all():
        if p.gig:
            completed_cats.add((p.gig.category or "").lower())

    open_gigs = Gig.query.filter(Gig.status.in_(["OPEN", "APPLIED"])).order_by(Gig.created_at.desc()).all()
    scored = []
    for gig in open_gigs:
        reasons = []
        score = 0
        gig_skills = {s.lower() for s in gig.skill_list()}
        overlap = skills & gig_skills
        if gig_skills:
            skill_pct = len(overlap) / len(gig_skills)
            score += int(skill_pct * 40)
            if overlap:
                reasons.append("Matches your " + " + ".join(sorted(s.title() for s in overlap)) + " skills")
        else:
            score += 10

        if budget_lo <= gig.budget <= budget_hi:
            score += 25
            reasons.append("budget fits your " + level["name"] + " range")
        elif gig.budget < budget_lo:
            score += 12
        else:
            score += 6  # still visible, but not prioritized

        cat = (gig.category or "").lower()
        if cat in interests or any(cat in i or i in cat for i in interests):
            score += 20
            reasons.append("your " + gig.category + " interest")
        if cat in completed_cats:
            score += 8
            reasons.append("similar completed work")

        if gig.difficulty == preferred_diff:
            score += 10
        elif (preferred_diff == "Advanced" and gig.difficulty == "Intermediate") or (
            preferred_diff == "Intermediate" and gig.difficulty == "Beginner"
        ):
            score += 6

        if gig.deadline and (gig.deadline - date.today()).days < 0:
            continue

        score = min(99, max(12, score))
        explanation = f"{score}% Match"
        if reasons:
            explanation += " — " + " and ".join(reasons[:2]) + "."
        scored.append((score, gig, explanation))

    scored.sort(key=lambda x: (-x[0], x[1].created_at))
    return scored[:limit]
