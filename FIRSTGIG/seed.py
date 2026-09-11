"""Populate demo data so the hackathon demo looks alive."""

from datetime import date, datetime, timedelta
from app import create_app
from extensions import db
from models import (
    User,
    StudentProfile,
    ClientProfile,
    Gig,
    Application,
    Project,
    Milestone,
    Payment,
    Review,
    Portfolio,
    Dispute,
    Notification,
)
from services.reliability_service import recalculate_student, recalculate_client
from services.escrow_service import MOCK_NOTE

PASSWORD = "password123"


def user(name, email, role):
    existing = User.query.filter_by(email=email).first()
    if existing:
        return existing
    u = User(name=name, email=email, role=role)
    u.set_password(PASSWORD)
    db.session.add(u)
    db.session.flush()
    return u


def add_completed_project(client, student, gig, days_ago=20, on_time=True, rating=5, comment="Great work."):
    start = date.today() - timedelta(days=days_ago + 6)
    deadline = start + timedelta(days=5)
    completed_at = datetime.combine(deadline if on_time else deadline + timedelta(days=2), datetime.min.time())
    gig.status = "CLOSED"
    p = Project(
        gig_id=gig.id,
        client_id=client.id,
        student_id=student.id,
        budget=gig.budget,
        start_date=start,
        deadline=deadline,
        status="COMPLETED",
        created_at=datetime.combine(start, datetime.min.time()),
        completed_at=completed_at,
        submission_message="Delivered as specified.",
        submission_link="https://example.com/demo",
        submitted_at=completed_at - timedelta(days=1),
    )
    db.session.add(p)
    db.session.flush()
    db.session.add(
        Payment(
            project_id=p.id,
            amount=gig.budget,
            status="Released",
            created_at=p.created_at,
            released_at=completed_at,
            note=MOCK_NOTE,
        )
    )
    db.session.add(
        Milestone(
            project_id=p.id,
            title="Delivery",
            description=gig.title,
            amount=gig.budget,
            deadline=deadline,
            status="Approved",
        )
    )
    db.session.add(
        Review(
            project_id=p.id,
            reviewer_id=client.id,
            reviewed_user_id=student.id,
            rating=rating,
            comment=comment,
            created_at=completed_at,
        )
    )
    db.session.add(
        Review(
            project_id=p.id,
            reviewer_id=student.id,
            reviewed_user_id=client.id,
            rating=5,
            comment="Clear brief and fair mock escrow release.",
            created_at=completed_at,
        )
    )
    return p


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        admin = user("FirstGig Admin", "admin@firstgig.test", "admin")

        aarthi = user("Aarthi Doulagar", "aarthi@college.edu", "student")
        begin = user("Rohan Mehta", "rohan@college.edu", "student")
        active = user("Priya Nair", "priya@college.edu", "student")
        rising = user("Kabir Shah", "kabir@college.edu", "student")
        trusted = user("Meera Iyer", "meera@college.edu", "student")

        db.session.add_all(
            [
                StudentProfile(
                    user_id=aarthi.id,
                    college="ABC College of Engineering",
                    branch="B.Tech — Computer Science",
                    academic_year="2nd Year",
                    bio="CS undergrad who ships clean Flask + frontend work. Looking for real client gigs to build a verified track record.",
                    skills="Python, Flask, HTML, CSS, JavaScript",
                    interests="Web Development, AI, Backend Development",
                    college_email="aarthi@college.edu",
                    verified=True,
                ),
                StudentProfile(
                    user_id=begin.id,
                    college="NIT Demo",
                    branch="B.Tech — Information Technology",
                    academic_year="1st Year",
                    bio="Just getting started. Strong on HTML/CSS and willing to take first small gigs.",
                    skills="HTML, CSS, Canva",
                    interests="UI/UX Design, Web Development",
                    college_email="rohan@college.edu",
                    verified=True,
                ),
                StudentProfile(
                    user_id=active.id,
                    college="VIT Demo",
                    branch="B.Tech — Computer Science",
                    academic_year="2nd Year",
                    bio="Two completed landing-page gigs. Fast turnaround.",
                    skills="HTML, CSS, JavaScript, Bootstrap",
                    interests="Web Development, Marketing",
                    college_email="priya@college.edu",
                    verified=True,
                ),
                StudentProfile(
                    user_id=rising.id,
                    college="BITS Demo",
                    branch="B.E. — Electronics",
                    academic_year="3rd Year",
                    bio="Comfortable with APIs and dashboards.",
                    skills="Python, Flask, SQL, JavaScript",
                    interests="Backend Development, Data Analysis",
                    college_email="kabir@college.edu",
                    verified=True,
                ),
                StudentProfile(
                    user_id=trusted.id,
                    college="IIIT Demo",
                    branch="B.Tech — Computer Science",
                    academic_year="4th Year",
                    bio="Trusted freelancer with a long streak of on-time deliveries.",
                    skills="Python, Flask, React-basics, SQL, REST APIs",
                    interests="Web Development, Backend Development, Mobile Apps",
                    college_email="meera@college.edu",
                    verified=True,
                ),
            ]
        )

        nova = user("Ananya Rao", "ananya@novalabs.test", "client")
        pixel = user("Vikram Joshi", "vikram@pixelcraft.test", "client")
        campus = user("Sana Qureshi", "sana@campushire.test", "client")
        db.session.add_all(
            [
                ClientProfile(user_id=nova.id, company_name="Nova Labs", description="Early-stage product studio hiring students for landing pages and MVPs."),
                ClientProfile(user_id=pixel.id, company_name="Pixelcraft", description="Design-led marketing boutique."),
                ClientProfile(user_id=campus.id, company_name="CampusHire", description="Ed-tech experiments and campus tools."),
            ]
        )
        db.session.flush()

        def gig(client, title, desc, cat, skills, budget, days, difficulty, status="OPEN", extra_days=0):
            g = Gig(
                client_id=client.id,
                title=title,
                description=desc,
                category=cat,
                required_skills=skills,
                budget=budget,
                deadline=date.today() + timedelta(days=days),
                difficulty=difficulty,
                status=status,
                requirements="Follow the brief, share a preview, and document what you shipped.",
                milestone_count=2 if budget >= 8000 else 1,
                created_at=datetime.utcnow() - timedelta(days=extra_days),
            )
            db.session.add(g)
            db.session.flush()
            return g

        # Historical closed gigs used to build levels (not shown as open).
        hist = []
        hist.append(gig(nova, "Fix CSS on a college fest site", "Small CSS cleanup.", "Web Development", "HTML, CSS", 800, -30, "Beginner", "CLOSED", 40))
        hist.append(gig(pixel, "Rewrite About page copy", "150 words, student-friendly.", "Content Writing", "Content Writing", 1500, -28, "Beginner", "CLOSED", 38))
        # Priya: 2 gigs
        p1 = gig(nova, "Responsive event landing page", "Single page for a campus event.", "Web Development", "HTML, CSS, JavaScript", 3000, -25, "Beginner", "CLOSED", 36)
        p2 = gig(pixel, "Bootstrap product teaser", "Hero + features + footer.", "Web Development", "HTML, CSS, Bootstrap", 2500, -22, "Beginner", "CLOSED", 32)
        add_completed_project(nova, active, p1, 30, True, 5, "Clean layout and on time.")
        add_completed_project(pixel, active, p2, 24, True, 4, "Good structure, a few spacing nits.")

        # Kabir: 4 gigs
        k_gigs = [
            gig(campus, "Simple Flask contact form", "Form + email mock.", "Backend Development", "Python, Flask", 4000, -40, "Beginner", "CLOSED", 50),
            gig(nova, "SQLite admin table view", "List/filter records.", "Backend Development", "Python, Flask, SQL", 5000, -35, "Intermediate", "CLOSED", 46),
            gig(pixel, "Chart.js dashboard widget", "One analytics card.", "Data Analysis", "JavaScript, HTML", 3500, -32, "Intermediate", "CLOSED", 42),
            gig(campus, "REST endpoint for events", "GET/POST mock.", "Backend Development", "Python, Flask", 6000, -28, "Intermediate", "CLOSED", 38),
        ]
        for i, g in enumerate(k_gigs):
            add_completed_project(User.query.get(g.client_id), rising, g, 45 - i * 4, True, 5 if i < 3 else 4, "Reliable student.")

        # Aarthi: 7 gigs → Verified Freelancer
        a_titles = [
            ("Portfolio site in Flask", "Multi-page Flask site.", "Web Development", "Python, Flask, HTML, CSS", 5000),
            ("Auth screens for campus app", "Login/register UI.", "Web Development", "HTML, CSS, JavaScript", 4500),
            ("Gig card component", "Responsive cards.", "UI/UX Design", "HTML, CSS", 3000),
            ("Seed script cleanup", "Python data script.", "Backend Development", "Python", 4000),
            ("Landing page for Nova Labs", "Marketing page.", "Web Development", "HTML, CSS, JavaScript", 8000),
            ("Review form validation", "Client-side + Flask.", "Web Development", "Python, Flask, JavaScript", 5500),
            ("Student dashboard widgets", "Stats cards.", "Web Development", "HTML, CSS, JavaScript", 7000),
        ]
        for i, (t, d, c, s, b) in enumerate(a_titles):
            g = gig(nova if i % 2 == 0 else campus, t, d, c, s, b, -20, "Intermediate", "CLOSED", 60 - i)
            add_completed_project(
                User.query.get(g.client_id),
                aarthi,
                g,
                70 - i * 5,
                True,
                5 if i % 3 else 4,
                "Aarthi communicates well and ships.",
            )
            if i < 4:
                db.session.add(
                    Portfolio(
                        student_id=aarthi.student_profile.id,
                        project_id=Project.query.filter_by(gig_id=g.id).first().id,
                        title=t,
                        description=d,
                        skills=s,
                        is_public=True,
                        project_link="https://example.com/demo",
                        contribution="Owned delivery end-to-end.",
                        completion_date=date.today() - timedelta(days=60 - i * 5),
                        client_review="Aarthi communicates well and ships.",
                    )
                )

        # Meera: 15 gigs → Trusted
        for i in range(15):
            g = gig(
                [nova, pixel, campus][i % 3],
                f"Trusted delivery #{i + 1}: campus tool module",
                "Scoped module with docs.",
                "Web Development" if i % 2 == 0 else "Backend Development",
                "Python, Flask, HTML, CSS, JavaScript",
                8000 + (i * 500),
                -10,
                "Advanced" if i > 8 else "Intermediate",
                "CLOSED",
                90 - i,
            )
            add_completed_project(User.query.get(g.client_id), trusted, g, 100 - i * 3, i != 4, 5 if i != 7 else 4, "Trusted quality.")

        # Open marketplace gigs across budgets
        open_specs = [
            (pixel, "Build a responsive landing page", "Hero, features, testimonials, footer. Mobile-first.", "Web Development", "HTML, CSS, JavaScript", 3000, 8, "Beginner"),
            (nova, "Design 3 mobile wireframes", "Low-fi screens for a campus app.", "UI/UX Design", "UI/UX Design, Figma", 1500, 6, "Beginner"),
            (campus, "Write 4 blog posts on internships", "SEO-light, 600 words each.", "Content Writing", "Content Writing", 800, 10, "Beginner"),
            (nova, "Flask portfolio website", "About, projects, contact form stored in SQLite.", "Web Development", "Python, Flask, HTML, CSS", 5000, 12, "Intermediate"),
            (pixel, "Product hunt style launch page", "Animated hero + waitlist form UI.", "Web Development", "HTML, CSS, JavaScript", 8000, 9, "Intermediate"),
            (campus, "Attendance CSV analyzer", "Python script + simple chart.", "Data Analysis", "Python, Data Analysis", 12000, 14, "Advanced"),
            (nova, "REST API for campus events", "CRUD + auth sessions.", "Backend Development", "Python, Flask, SQL", 18000, 16, "Advanced"),
            (pixel, "End-to-end marketing microsite", "Copy + design + frontend.", "Marketing", "HTML, CSS, JavaScript, Content Writing", 25000, 20, "Advanced"),
            (campus, "Bug bash a student dashboard", "Find and document UI bugs.", "Research", "HTML, CSS", 1500, 5, "Beginner"),
        ]
        open_gigs = []
        for spec in open_specs:
            open_gigs.append(gig(*spec, extra_days=2))

        # Pending application from Aarthi on Flask portfolio
        flask_gig = next(g for g in open_gigs if "portfolio website" in g.title.lower())
        db.session.add(
            Application(
                gig_id=flask_gig.id,
                student_id=aarthi.id,
                proposal="I have shipped several Flask sites and this matches my Web Development interest. I can deliver a clean, documented portfolio in 7 days.",
                expected_completion="7 days",
                status="Pending",
            )
        )
        flask_gig.status = "APPLIED"

        landing = next(g for g in open_gigs if "landing page" in g.title.lower())
        db.session.add(
            Application(
                gig_id=landing.id,
                student_id=begin.id,
                proposal="This would be my first paid gig. I can follow a Figma-less brief and keep the CSS tidy.",
                expected_completion="5 days",
                status="Pending",
            )
        )
        landing.status = "APPLIED"

        # Live in-progress project (Priya hired)
        live_gig = gig(
            campus,
            "Campus club microsite",
            "Four pages, events list, join form.",
            "Web Development",
            "HTML, CSS, JavaScript",
            4500,
            4,
            "Beginner",
            "ASSIGNED",
            1,
        )
        live = Project(
            gig_id=live_gig.id,
            client_id=campus.id,
            student_id=active.id,
            budget=4500,
            start_date=date.today() - timedelta(days=1),
            deadline=date.today() + timedelta(days=4),
            status="IN_PROGRESS",
        )
        db.session.add(live)
        db.session.flush()
        db.session.add(Payment(project_id=live.id, amount=4500, status="Held", note=MOCK_NOTE))
        db.session.add(Milestone(project_id=live.id, title="Design", description="Layout and tokens", amount=1500, deadline=date.today() + timedelta(days=2), status="In Progress"))
        db.session.add(Milestone(project_id=live.id, title="Build", description="Pages + form", amount=3000, deadline=date.today() + timedelta(days=4), status="Pending"))
        db.session.add(
            Application(
                gig_id=live_gig.id,
                student_id=active.id,
                proposal="I can reuse patterns from my last two landing pages.",
                expected_completion="4 days",
                status="Accepted",
            )
        )

        # Overdue project for dispute demo
        od_gig = gig(
            pixel,
            "Email header banner set",
            "Three banners, 600x200.",
            "UI/UX Design",
            "UI/UX Design, Canva",
            2000,
            -2,
            "Beginner",
            "ASSIGNED",
            10,
        )
        od = Project(
            gig_id=od_gig.id,
            client_id=pixel.id,
            student_id=begin.id,
            budget=2000,
            start_date=date.today() - timedelta(days=10),
            deadline=date.today() - timedelta(days=2),
            status="OVERDUE",
        )
        db.session.add(od)
        db.session.flush()
        db.session.add(Payment(project_id=od.id, amount=2000, status="Held", note=MOCK_NOTE))
        db.session.add(
            Dispute(
                project_id=od.id,
                raised_by=pixel.id,
                reason="Student missed deadline",
                description="Banners were not delivered by the deadline. Requesting admin review. Mock escrow still held.",
                evidence="Deadline was two days ago; no submission file.",
                status="Open",
            )
        )
        od.status = "DISPUTED"
        db.session.add(
            Application(
                gig_id=od_gig.id,
                student_id=begin.id,
                proposal="I can design simple banners in Canva.",
                expected_completion="5 days",
                status="Accepted",
            )
        )

        db.session.add(Notification(user_id=aarthi.id, message="Welcome back. New gigs match your Flask + Web Development profile.", link="/gigs"))
        db.session.add(Notification(user_id=nova.id, message="Aarthi applied to Flask portfolio website.", link=f"/gigs/{flask_gig.id}/applicants"))
        db.session.add(Notification(user_id=admin.id, message="Open dispute: Email header banner set.", link="/admin/disputes"))

        db.session.commit()
        for s in (aarthi, begin, active, rising, trusted):
            recalculate_student(s.id)
        for c in (nova, pixel, campus):
            recalculate_client(c.id)

        print("Seeded FirstGig demo data.")
        print("Login (password for all): password123")
        print("  Admin:   admin@firstgig.test")
        print("  Aarthi:  aarthi@college.edu   (Verified Freelancer ~7 gigs)")
        print("  Rohan:   rohan@college.edu    (Beginner)")
        print("  Priya:   priya@college.edu    (Active)")
        print("  Kabir:   kabir@college.edu    (Rising)")
        print("  Meera:   meera@college.edu    (Trusted)")
        print("  Client:  ananya@novalabs.test / vikram@pixelcraft.test / sana@campushire.test")


if __name__ == "__main__":
    seed()
