"""Smoke-test core FirstGig business rules with the Flask test client."""
from app import create_app
from models import User, Application, Project, Review, Gig, StudentProfile

app = create_app()
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False

PASS = "password123"


def login(client, email):
    return client.post("/login", data={"email": email, "password": PASS}, follow_redirects=True)


def main():
    with app.test_client() as c:
        r = c.get("/")
        assert r.status_code == 200, r.status_code
        assert b"Your First Gig" in r.data

        r = login(c, "aarthi@college.edu")
        assert r.status_code == 200
        assert b"Verified Freelancer" in r.data or b"Aarthi" in r.data

        r = c.get("/gigs")
        assert r.status_code == 200
        assert b"Recommended For You" in r.data

        # duplicate apply blocked
        with app.app_context():
            gig = Gig.query.filter(Gig.title.ilike("%portfolio website%")).first()
            gid = gig.id
        r = c.post(f"/gigs/{gid}/apply", data={"proposal": "x" * 25, "expected_completion": "7 days"}, follow_redirects=True)
        assert b"already applied" in r.data.lower() or b"Application sent" in r.data

        c.get("/logout")
        login(c, "ananya@novalabs.test")
        r = c.get(f"/gigs/{gid}/applicants")
        assert r.status_code == 200
        assert b"Aarthi" in r.data

        with app.app_context():
            appn = Application.query.filter_by(gig_id=gid, student_id=User.query.filter_by(email="aarthi@college.edu").first().id).first()
            aid = appn.id
        r = c.post(f"/gigs/{gid}/applications/{aid}/accept", follow_redirects=True)
        assert r.status_code == 200
        assert b"Held" in r.data or b"IN_PROGRESS" in r.data or b"Mock escrow" in r.data

        with app.app_context():
            proj = Project.query.filter_by(gig_id=gid).first()
            pid = proj.id
            assert proj.payment.status == "Held"

        # review should be locked
        r = c.get(f"/projects/{pid}/review", follow_redirects=True)
        assert b"only after" in r.data.lower() or b"unlock" in r.data.lower() or b"COMPLETED" in r.data

        c.get("/logout")
        login(c, "aarthi@college.edu")
        r = c.post(
            f"/projects/{pid}/submit",
            data={"submission_message": "Shipped the Flask portfolio as specified.", "submission_link": "https://example.com/p"},
            follow_redirects=True,
        )
        assert b"SUBMITTED" in r.data or b"submitted" in r.data.lower()

        c.get("/logout")
        login(c, "ananya@novalabs.test")
        r = c.post(f"/projects/{pid}/approve", follow_redirects=True)
        assert b"COMPLETED" in r.data or b"completed" in r.data.lower()

        r = c.post(f"/projects/{pid}/review", data={"rating": "5", "comment": "Excellent delivery and communication."}, follow_redirects=True)
        assert r.status_code == 200

        c.get("/logout")
        login(c, "aarthi@college.edu")
        r = c.post(f"/projects/{pid}/review", data={"rating": "5", "comment": "Clear brief and fair escrow release."}, follow_redirects=True)
        assert r.status_code == 200
        r = c.post(
            f"/projects/{pid}/portfolio",
            data={"is_public": "on", "contribution": "Full stack delivery", "project_link": "https://example.com/p"},
            follow_redirects=True,
        )
        assert b"portfolio" in r.data.lower()

        with app.app_context():
            aarthi = User.query.filter_by(email="aarthi@college.edu").first()
            assert aarthi.student_profile.completed_gigs >= 8
            assert Review.query.filter_by(project_id=pid).count() == 2

        c.get("/logout")
        login(c, "admin@firstgig.test")
        r = c.get("/admin/")
        assert r.status_code == 200
        assert b"Students" in r.data

        with app.app_context():
            disputed = Project.query.filter_by(status="DISPUTED").first()
            did = disputed.disputes[0].id
            dpid = disputed.id
        r = c.post(f"/admin/disputes/{did}/resolve", data={"decision": "Refund Client"}, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            from extensions import db
            p = db.session.get(Project, dpid)
            assert p.status == "REFUNDED"
            assert p.payment.status == "Refunded"

        print("SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
