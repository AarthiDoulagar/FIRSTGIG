"""Freelancer progression. Level is derived from completed verified gigs only."""

LEVELS = [
    {"min": 0, "max": 0, "key": "beginner", "name": "FirstGig Beginner", "icon": "🟢", "budget": (500, 5000)},
    {"min": 1, "max": 2, "key": "active", "name": "Active Freelancer", "icon": "🔵", "budget": (500, 7500)},
    {"min": 3, "max": 4, "key": "rising", "name": "Rising Freelancer", "icon": "🟣", "budget": (1000, 10000)},
    {"min": 5, "max": 9, "key": "verified", "name": "Verified Freelancer", "icon": "⭐", "budget": (5000, 20000)},
    {"min": 10, "max": 19, "key": "trusted", "name": "Trusted Freelancer", "icon": "🏆", "budget": (5000, 30000)},
    {"min": 20, "max": 10_000, "key": "pro", "name": "Pro Student", "icon": "🚀", "budget": (10000, 100000)},
]


def level_for_completed(completed):
    completed = completed or 0
    for i, level in enumerate(LEVELS):
        if level["min"] <= completed <= level["max"]:
            nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
            toward = nxt["min"] if nxt else completed
            return {
                **level,
                "index": i,
                "completed": completed,
                "next_name": nxt["name"] if nxt else None,
                "next_icon": nxt["icon"] if nxt else None,
                "toward": toward,
                "progress_pct": 100 if not nxt else min(100, int((completed / toward) * 100) if toward else 100),
            }
    return {**LEVELS[-1], "index": len(LEVELS) - 1, "completed": completed, "next_name": None, "toward": completed, "progress_pct": 100}


def difficulty_for_level(level_key):
    mapping = {
        "beginner": "Beginner",
        "active": "Beginner",
        "rising": "Intermediate",
        "verified": "Intermediate",
        "trusted": "Advanced",
        "pro": "Advanced",
    }
    return mapping.get(level_key, "Beginner")
