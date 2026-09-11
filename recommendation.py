"""
Rule-based recommendation engine for FirstGig.
Matches student profiles to open gigs based on:
1. Skill overlap (exact & partial matching)
2. Domain / Category interest alignment
3. Student career tier vs. gig difficulty
4. Reliability, rating, and completion track record
"""

def calculate_gig_match(student, gig):
    """
    Calculates a match percentage (0-100%) and a friendly explanation for a student & gig.
    """
    if not student:
        # Generic recommendation for guests
        return {
            'score': 85,
            'match_pct': 85,
            'reason': f"Popular {gig.difficulty} project in {gig.category} for new freelancers",
            'matched_skills': gig.skills[:2]
        }

    student_skills = [s.lower().strip() for s in (student.skills or [])]
    student_interests = [i.lower().strip() for i in (student.interests or [])]
    gig_skills = [s.lower().strip() for s in (gig.skills or [])]
    gig_category = gig.category.lower().strip()
    tier_num = student.career_level_info['tier_num']

    # 1. Skill Overlap (up to 45 pts)
    matched_skills = []
    for g_skill in gig_skills:
        for s_skill in student_skills:
            if g_skill in s_skill or s_skill in g_skill:
                if g_skill not in [m.lower() for m in matched_skills]:
                    # Keep original casing
                    orig = next((orig_s for orig_s in gig.skills if orig_s.lower().strip() == g_skill), g_skill.title())
                    matched_skills.append(orig)

    if gig_skills:
        skill_ratio = len(matched_skills) / len(gig_skills)
        skill_score = min(45, int(skill_ratio * 45))
    else:
        skill_score = 30

    # 2. Interest / Category Alignment (up to 25 pts)
    interest_matched = False
    interest_score = 10 # baseline interest
    matched_interest_name = ""

    for interest in student_interests:
        if interest in gig_category or gig_category in interest:
            interest_score = 25
            interest_matched = True
            matched_interest_name = interest.title()
            break
        for g_skill in gig_skills:
            if interest in g_skill or g_skill in interest:
                interest_score = 22
                interest_matched = True
                matched_interest_name = interest.title()
                break

    # 3. Career Level vs Difficulty Fit (up to 20 pts)
    diff = gig.difficulty.lower()
    diff_score = 15
    if tier_num == 0: # Beginner
        if diff == 'beginner':
            diff_score = 20
        elif diff == 'medium':
            diff_score = 12
        else:
            diff_score = 5
    elif tier_num in [1, 2]: # Active
        if diff == 'beginner':
            diff_score = 18
        elif diff == 'medium':
            diff_score = 20
        else:
            diff_score = 10
    elif tier_num in [3, 4]: # Rising / Verified
        if diff in ['medium', 'advanced']:
            diff_score = 20
        else:
            diff_score = 15
    else: # Pro
        diff_score = 20

    # 4. Student Reliability & Rating Factor (up to 10 pts)
    rep_score = int(min(10, (student.rating / 5.0) * 6 + (student.reliability_rate / 100.0) * 4))

    total_score = skill_score + interest_score + diff_score + rep_score
    # Cap between 40 and 98%
    final_pct = max(40, min(98, total_score))

    # Generate personalized explanation
    reasons = []
    if matched_skills:
        skill_str = " + ".join(matched_skills[:2])
        reasons.append(f"Matches your {skill_str} skills")
    
    if interest_matched and matched_interest_name:
        reasons.append(f"aligns with your {matched_interest_name} interest")
    elif diff == 'beginner' and tier_num == 0:
        reasons.append("ideal starting gig for your level")
    elif tier_num >= 3 and diff in ['medium', 'advanced']:
        reasons.append("matches your verified freelancer track record")

    if not reasons:
        explanation = f"Recommended based on your academic background in {student.branch}"
    else:
        explanation = " and ".join(reasons).capitalize() + "."

    return {
        'score': total_score,
        'match_pct': final_pct,
        'reason': explanation,
        'matched_skills': matched_skills
    }

def get_recommended_gigs(student, open_gigs, limit=6):
    """
    Ranks open gigs for a student by rule-based match score.
    Attaches `recommendation` dict to each gig object.
    """
    scored = []
    for gig in open_gigs:
        rec = calculate_gig_match(student, gig)
        scored.append((rec['match_pct'], gig, rec))

    # Sort descending by match percentage
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for match_pct, gig, rec in scored[:limit]:
        # Temporary runtime attribute on gig
        gig.match_info = rec
        results.append(gig)

    return results
