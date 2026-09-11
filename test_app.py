import unittest
from datetime import datetime, timedelta
from app import app
from models import db, User, StudentProfile, ClientProfile, Gig, Project, Review, Dispute

class FirstGigTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_public_pages(self):
        """Test that all public pages return HTTP 200"""
        routes = ['/', '/gigs', '/how-it-works', '/login', '/register', '/portfolio']
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed with {response.status_code}")
            self.assertIn(b'FirstGig', response.data)

    def test_02_gig_marketplace_filtering(self):
        """Test search and filter parameters on /gigs"""
        # Filter by category
        res_cat = self.client.get('/gigs?category=Web+Development')
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn(b'Web Development', res_cat.data)

        # Filter by difficulty
        res_diff = self.client.get('/gigs?difficulty=Beginner')
        self.assertEqual(res_diff.status_code, 200)

        # Filter by max budget
        res_bud = self.client.get('/gigs?max_budget=4000')
        self.assertEqual(res_bud.status_code, 200)

        # Keyword search
        res_search = self.client.get('/gigs?q=Landing+Page')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b'Landing Page', res_search.data)

    def test_03_demo_switcher_and_student_dashboard(self):
        """Test 1-click switcher to verified student and inspect dashboard"""
        switch_res = self.client.get('/switch-demo/verified_student', follow_redirects=True)
        self.assertEqual(switch_res.status_code, 200)
        # Rahul is Level 4: ⭐ Verified Freelancer
        self.assertIn(b'Verified Freelancer', switch_res.data)
        self.assertIn(b'Rahul Sharma', switch_res.data)
        # Check rule-based recommendation section
        self.assertIn(b'Recommended For Your Level', switch_res.data)

    def test_04_career_progression_calculation(self):
        """Test that career tier calculation is accurate across levels"""
        with app.app_context():
            rahul = StudentProfile.query.filter_by(full_name='Rahul Sharma').first()
            self.assertEqual(rahul.completed_gigs_count, 7)
            info = rahul.career_level_info
            self.assertEqual(info['tier_num'], 3)
            self.assertIn('Verified Freelancer', info['name'])

            priya = StudentProfile.query.filter_by(full_name='Priya Patel').first()
            self.assertEqual(priya.completed_gigs_count, 0)
            p_info = priya.career_level_info
            self.assertEqual(p_info['tier_num'], 0)
            self.assertIn('Beginner', p_info['name'])

    def test_05_client_dashboard_and_applicant_view(self):
        """Test client login, posted gigs, and applicant viewing"""
        client_res = self.client.get('/switch-demo/client', follow_redirects=True)
        self.assertEqual(client_res.status_code, 200)
        self.assertIn(b'Apex Digital Studio', client_res.data)
        self.assertIn(b'Total Gigs Posted', client_res.data)

        # View applicants
        apps_res = self.client.get('/client/applications')
        self.assertEqual(apps_res.status_code, 200)
        self.assertIn(b'Candidate Applicant Review', apps_res.data)

    def test_06_project_workspace_and_escrow_stepper(self):
        """Test project detail workspace: deadline UI, mock escrow stepper, milestones"""
        # Login as student to access project workspace
        self.client.get('/switch-demo/verified_student')
        with app.app_context():
            proj = Project.query.filter_by(status='IN PROGRESS').first()
            proj_id = proj.id

        proj_res = self.client.get(f'/project/{proj_id}')
        self.assertEqual(proj_res.status_code, 200)
        self.assertIn(b'HELD IN MOCK ESCROW', proj_res.data)
        self.assertIn(b'Demo Mode \xe2\x80\x94 Payments are simulated', proj_res.data)
        self.assertIn(b'Project Milestones', proj_res.data)

    def test_07_deadline_ui_badges(self):
        """Verify deadline status logic (Plenty of time, Approaching, Overdue)"""
        with app.app_context():
            now = datetime.utcnow()
            p_plenty = Project(
                client_id=1, student_id=1, title="Test Plenty", description="Test",
                budget=1000, deadline_date=now + timedelta(days=6), status="IN PROGRESS"
            )
            p_approach = Project(
                client_id=1, student_id=1, title="Test Approach", description="Test",
                budget=1000, deadline_date=now + timedelta(days=2), status="IN PROGRESS"
            )
            p_overdue = Project(
                client_id=1, student_id=1, title="Test Overdue", description="Test",
                budget=1000, deadline_date=now - timedelta(days=2), status="IN PROGRESS"
            )
            self.assertIn('Plenty', p_plenty.deadline_ui_status['badge'])
            self.assertIn('approaching', p_approach.deadline_ui_status['badge'])
            self.assertIn('Overdue', p_overdue.deadline_ui_status['badge'])

    def test_08_admin_dashboard_and_dispute_resolution(self):
        """Test SaaS admin dashboard, stats cards, and dispute resolution action"""
        admin_res = self.client.get('/switch-demo/admin', follow_redirects=True)
        self.assertEqual(admin_res.status_code, 200)
        self.assertIn(b'Platform Administration', admin_res.data)
        self.assertIn(b'Dispute Resolution Center', admin_res.data)
        self.assertIn(b'Student College Email Verification Queue', admin_res.data)

        with app.app_context():
            disp = Dispute.query.first()
            self.assertIsNotNone(disp)
            disp_id = disp.id

        resolve_res = self.client.post(
            f'/admin/dispute/{disp_id}/resolve',
            data={'action_type': 'extend_deadline'},
            follow_redirects=True
        )
        self.assertEqual(resolve_res.status_code, 200)
        with app.app_context():
            updated_disp = Dispute.query.get(disp_id)
            self.assertEqual(updated_disp.status, 'Under Review')

if __name__ == '__main__':
    unittest.main()
