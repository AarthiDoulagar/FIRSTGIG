"""
Seed script for FirstGig database.
Populates realistic demo accounts, open gigs, active deliverables,
milestones, submissions, genuine verified reviews, disputes, and portfolio items.
"""

from datetime import datetime, timedelta
import json
from app import app
from models import (
    db, User, StudentProfile, ClientProfile, Gig,
    Application, Project, Milestone, Submission,
    Review, PortfolioItem, Dispute, Notification
)

def seed():
    with app.app_context():
        print("Re-creating database tables...")
        db.drop_all()
        db.create_all()

        print("Seeding Users...")
        # 1. Verified Student - Rahul Sharma (Level 4: ⭐ Verified Freelancer, 7 gigs done)
        u_student_verified = User(
            username="rahul_sharma",
            email="rahul@college.edu",
            role="student"
        )
        u_student_verified.set_password("student123")
        db.session.add(u_student_verified)

        # 2. Beginner Student - Priya Patel (Level 0: 🟢 FirstGig Beginner, 0 gigs done)
        u_student_beginner = User(
            username="priya_patel",
            email="priya@college.edu",
            role="student"
        )
        u_student_beginner.set_password("student123")
        db.session.add(u_student_beginner)

        # 3. Client - Vikram Verma (Apex Digital Studio)
        u_client1 = User(
            username="vikram_apex",
            email="vikram@studio.com",
            role="client"
        )
        u_client1.set_password("client123")
        db.session.add(u_client1)

        # 4. Client - Neha Kapoor (Velocity Fintech)
        u_client2 = User(
            username="neha_velocity",
            email="neha@startup.io",
            role="client"
        )
        u_client2.set_password("client123")
        db.session.add(u_client2)

        # 5. Platform Admin
        u_admin = User(
            username="admin_lead",
            email="admin@firstgig.com",
            role="admin"
        )
        u_admin.set_password("admin123")
        db.session.add(u_admin)

        db.session.flush()

        print("Seeding Profiles...")
        # Student 1 Profile: Rahul
        sp_rahul = StudentProfile(
            user_id=u_student_verified.id,
            full_name="Rahul Sharma",
            college_name="IIT Bombay",
            college_email="rahul@college.edu",
            branch="Computer Science & Engineering",
            academic_year="3rd Year",
            is_verified=True,
            bio="Pre-final year CSE student passionate about full-stack Python & Flask development, responsive UI engineering, and robust REST APIs. Looking to deliver high-quality code and grow reputation.",
            rating=4.9,
            reliability_rate=96,
            on_time_rate=95,
            completed_gigs_count=7,
            disputes_count=0
        )
        sp_rahul.skills = ["Python", "Flask", "HTML", "CSS", "JavaScript", "SQL", "Git"]
        sp_rahul.interests = ["Web Development", "Python & Backend", "API Architecture"]
        db.session.add(sp_rahul)

        # Student 2 Profile: Priya
        sp_priya = StudentProfile(
            user_id=u_student_beginner.id,
            full_name="Priya Patel",
            college_name="Delhi Technological University",
            college_email="priya@college.edu",
            branch="Information Technology",
            academic_year="2nd Year",
            is_verified=True,
            bio="Second-year IT student eager to complete my first real-world gig! Strong fundamentals in HTML, CSS, Figma design, and basic JavaScript.",
            rating=5.0,
            reliability_rate=100,
            on_time_rate=100,
            completed_gigs_count=0,
            disputes_count=0
        )
        sp_priya.skills = ["HTML", "CSS", "Figma", "UI/UX Design", "JavaScript"]
        sp_priya.interests = ["UI/UX Design", "Web Development", "Frontend"]
        db.session.add(sp_priya)

        # Client 1 Profile: Apex Digital Studio
        cp_vikram = ClientProfile(
            user_id=u_client1.id,
            company_name="Apex Digital Studio",
            contact_name="Vikram Verma",
            industry="Software & Digital Agency",
            website="https://apexdigital.example.com",
            description="Leading boutique creative agency building web applications, marketing landing pages, and prototypes for enterprise clients.",
            total_spent=42000
        )
        db.session.add(cp_vikram)

        # Client 2 Profile: Velocity Fintech
        cp_neha = ClientProfile(
            user_id=u_client2.id,
            company_name="Velocity Fintech",
            contact_name="Neha Kapoor",
            industry="Fintech & Payments",
            website="https://velocityfintech.example.com",
            description="Fast-growing fintech startup modernizing merchant checkout experiences.",
            total_spent=28000
        )
        db.session.add(cp_neha)

        db.session.flush()

        print("Seeding Gigs...")
        # Gigs posted by Vikram
        g1 = Gig(
            client_id=cp_vikram.id,
            title="Build a Responsive Landing Page in HTML/CSS",
            description="We need a clean, highly modern and responsive product landing page for a SaaS startup. Design assets will be provided in Figma. Must look pixel-perfect on mobile, tablet, and desktop viewports without horizontal scrolling.",
            category="Web Development",
            budget=3000,
            difficulty="Medium",
            deadline_days=5,
            status="open"
        )
        g1.skills = ["HTML", "CSS", "JavaScript", "Responsive Design"]

        g2 = Gig(
            client_id=cp_vikram.id,
            title="Flask REST API with JWT Authentication",
            description="Create modular Flask blueprint endpoints for user registration, login, role permissions, and token refresh. Store data in SQLite using SQLAlchemy.",
            category="Python & Backend",
            budget=6500,
            difficulty="Medium",
            deadline_days=8,
            status="open"
        )
        g2.skills = ["Python", "Flask", "SQLite", "REST APIs", "JWT"]

        g3 = Gig(
            client_id=cp_vikram.id,
            title="Figma UI/UX Prototype for Student Career App",
            description="Design an intuitive, vertical mobile design system and 5 high-fidelity screens for an ed-tech startup. Includes typography guidelines and color system.",
            category="UI/UX Design",
            budget=4500,
            difficulty="Beginner",
            deadline_days=6,
            status="open"
        )
        g3.skills = ["Figma", "UI/UX Design", "Wireframing", "Mobile Design"]

        # Gigs posted by Neha
        g4 = Gig(
            client_id=cp_neha.id,
            title="Python Automated Web Scraper for Market Pricing",
            description="Develop a python script with BeautifulSoup and requests to scrape public catalog pricing data daily and export formatted CSV summaries.",
            category="Python & Backend",
            budget=3500,
            difficulty="Beginner",
            deadline_days=4,
            status="open"
        )
        g4.skills = ["Python", "BeautifulSoup", "Data Extraction", "Automation"]

        g5 = Gig(
            client_id=cp_neha.id,
            title="Full-Stack Admin Analytics Dashboard",
            description="Develop an interactive admin interface with Chart.js, metric stat cards, and clean data tables with search filters for transactions.",
            category="Web Development",
            budget=11000,
            difficulty="Advanced",
            deadline_days=12,
            status="open"
        )
        g5.skills = ["Flask", "JavaScript", "Chart.js", "SQLAlchemy", "CSS"]

        g6 = Gig(
            client_id=cp_neha.id,
            title="Technical SEO Blog Articles on Cloud Computing",
            description="Write 3 comprehensive, original technical articles (1,200 words each) covering containerization, microservices, and serverless architectures.",
            category="Content & SEO",
            budget=2500,
            difficulty="Beginner",
            deadline_days=4,
            status="open"
        )
        g6.skills = ["Content Writing", "Technical Writing", "SEO", "Cloud Computing"]

        g7 = Gig(
            client_id=cp_vikram.id,
            title="CSS Layout Debugging & Cross-Browser Fixes",
            description="Resolve flexbox alignment quirks and mobile menu overflow across iOS Safari and Chrome Android on our client's web app.",
            category="Web Development",
            budget=2000,
            difficulty="Beginner",
            deadline_days=3,
            status="open"
        )
        g7.skills = ["CSS", "Responsive Design", "Debugging", "HTML"]

        db.session.add_all([g1, g2, g3, g4, g5, g6, g7])
        db.session.flush()

        print("Seeding Applications...")
        # Priya applies for g3 (UI/UX)
        app_priya = Application(
            gig_id=g3.id,
            student_id=sp_priya.id,
            proposal="Hi Vikram! I am a 2nd year IT student specializing in Figma UI/UX. I have crafted student-centric mobile interfaces and would love to deliver pixel-perfect wireframes for this app within 5 days.",
            bid_amount=4500,
            estimated_days=5,
            status="pending"
        )
        # Rahul applies for g2 (Flask API)
        app_rahul = Application(
            gig_id=g2.id,
            student_id=sp_rahul.id,
            proposal="Hello! I have completed 7 verified projects on FirstGig with a 4.9 rating. I'm proficient in Flask, SQLAlchemy, and JWT authentication. I can deliver a clean, documented API with unit test coverage.",
            bid_amount=6000,
            estimated_days=6,
            status="pending"
        )
        db.session.add_all([app_priya, app_rahul])
        db.session.flush()

        print("Seeding Projects & Milestones...")
        # Project 1: Ongoing active project for Rahul (Plenty of time)
        now = datetime.utcnow()
        p1 = Project(
            gig_id=g1.id,
            client_id=cp_vikram.id,
            student_id=sp_rahul.id,
            title="Apex SaaS Landing Page & Responsive Layout",
            description="Build modern, vertical SaaS landing page adhering to strict responsive design and typography guidelines.",
            budget=3000,
            deadline_date=now + timedelta(days=5),
            status="IN PROGRESS",
            escrow_status="Held"
        )
        db.session.add(p1)
        db.session.flush()

        m1_p1 = Milestone(
            project_id=p1.id,
            title="Hero & Feature Wireframe",
            description="Desktop and mobile responsive layout prototypes",
            amount=1500,
            deadline_date=now + timedelta(days=2),
            status="In Progress"
        )
        m2_p1 = Milestone(
            project_id=p1.id,
            title="Complete Responsive Page & Testing",
            description="Final code, accessibility checks, and cross-browser testing",
            amount=1500,
            deadline_date=now + timedelta(days=5),
            status="Pending"
        )
        db.session.add_all([m1_p1, m2_p1])

        # Project 2: Submitted project for Rahul waiting client review (Deadline approaching)
        p2 = Project(
            gig_id=g4.id,
            client_id=cp_neha.id,
            student_id=sp_rahul.id,
            title="E-Commerce Pricing Automation Script",
            description="Automated Python BeautifulSoup crawler for daily catalog price monitoring.",
            budget=3500,
            deadline_date=now + timedelta(days=2),
            status="SUBMITTED",
            escrow_status="Held"
        )
        db.session.add(p2)
        db.session.flush()

        sub_p2 = Submission(
            project_id=p2.id,
            message="Completed scraper script with exception handling, rate limiting, and automated CSV generation.",
            description="Includes README with virtualenv setup, tests, and sample outputs.",
            project_link="https://github.com/rahul-sharma/ecommerce-price-scraper",
            status="submitted",
            submitted_at=now - timedelta(hours=4)
        )
        db.session.add(sub_p2)

        # Project 3: Overdue project (to test 🔴 Overdue UI)
        p3 = Project(
            client_id=cp_vikram.id,
            student_id=sp_rahul.id,
            title="Legacy CSS Refactoring & Grid Optimization",
            description="Resolve legacy stylesheet conflicts on client portal.",
            budget=2500,
            deadline_date=now - timedelta(days=2), # past deadline
            status="OVERDUE",
            escrow_status="Held"
        )
        db.session.add(p3)

        # Project 4: Disputed Project (for Admin arbitration test)
        p4 = Project(
            client_id=cp_neha.id,
            student_id=sp_rahul.id,
            title="Custom WordPress Integration Prototype",
            description="Integration of webhook listeners into WordPress blog.",
            budget=4000,
            deadline_date=now - timedelta(days=1),
            status="IN PROGRESS",
            escrow_status="Held"
        )
        db.session.add(p4)
        db.session.flush()

        disp = Dispute(
            project_id=p4.id,
            raised_by_id=u_client2.id,
            reason="Deliverables Do Not Match Specifications",
            description="The webhook listener dropped payload formatting on test transactions and the student has been delayed in pushing fixes.",
            evidence="https://github.com/velocity-fintech/dispute-log-942",
            status="Open"
        )
        db.session.add(disp)

        print("Seeding Completed Projects, Reviews, and Portfolios...")
        # 5 completed historical projects for Rahul (demonstrating Verified Freelancer tier)
        completed_data = [
            ("Fintech Checkout Landing Page", 3500, 5, "Rahul delivered exceptional work ahead of schedule! Pixel perfect and clean CSS.", cp_vikram),
            ("Flask CRUD Backend for Inventory", 4500, 5, "Remarkable Python proficiency for a college student. Code was well-documented.", cp_neha),
            ("Portfolio Website for Design Consultant", 3000, 5, "Very responsive, implemented all revisions smoothly. Highly recommended student.", cp_vikram),
            ("Data Cleaning Script in Pandas", 2500, 4, "Solid script that processed over 50,000 records accurately.", cp_neha),
            ("Interactive Modal System in JavaScript", 2000, 5, "Quick turnaround and flawless vanilla JS implementation.", cp_vikram),
            ("Customer Feedback Form with Validation", 2500, 5, "Great communication and very polite. Exactly what our company needed.", cp_vikram),
            ("Mobile Navigation Drawer Refactor", 1500, 5, "Fixed our tricky Safari scrolling bug on mobile. Outstanding student talent!", cp_neha)
        ]

        for title, budget, rating, review_text, client in completed_data:
            past_proj = Project(
                client_id=client.id,
                student_id=sp_rahul.id,
                title=title,
                description=f"Successfully completed client deliverable for {title}.",
                budget=budget,
                deadline_date=now - timedelta(days=30),
                status="COMPLETED",
                escrow_status="Released"
            )
            db.session.add(past_proj)
            db.session.flush()

            rev = Review(
                project_id=past_proj.id,
                reviewer_id=client.user_id,
                reviewee_id=u_student_verified.id,
                rating=rating,
                comment=review_text,
                is_verified_project=True,
                created_at=now - timedelta(days=25)
            )
            db.session.add(rev)

            # Portfolio items
            port = PortfolioItem(
                student_id=sp_rahul.id,
                project_id=past_proj.id,
                title=title,
                description=f"Delivered production-ready solution featuring modern responsive design and clean architecture.",
                skills_used="HTML, CSS, JavaScript, Python",
                completion_date="Jan 2026",
                client_review_snippet=review_text,
                project_link="https://github.com/rahul-sharma/showcase-project",
                is_verified_project=True,
                is_public=True
            )
            db.session.add(port)

        # Seed Notifications
        n1 = Notification(
            user_id=u_student_verified.id,
            title="⭐ Milestone Unlocked: Verified Freelancer",
            message="Congratulations Rahul! Having completed 7 projects, your profile has earned the ⭐ Verified Freelancer badge.",
            link="/student/profile"
        )
        n2 = Notification(
            user_id=u_client1.id,
            title="New Proposal from Rahul Sharma",
            message="⭐ Verified Freelancer Rahul Sharma submitted a bid for 'Flask REST API with JWT Authentication'.",
            link="/client/applications"
        )
        db.session.add_all([n1, n2])

        db.session.commit()
        print("Database seeded successfully with all roles, gigs, escrow states, reviews, and portfolio items!")

if __name__ == '__main__':
    seed()
