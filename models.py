from datetime import datetime, timedelta
import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student') # 'student', 'client', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    client_profile = db.relationship('ClientProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    college_name = db.Column(db.String(150), nullable=False)
    college_email = db.Column(db.String(120), nullable=False)
    branch = db.Column(db.String(100), nullable=False, default='Computer Science')
    academic_year = db.Column(db.String(50), nullable=False, default='3rd Year')
    is_verified = db.Column(db.Boolean, default=False)
    bio = db.Column(db.Text, default='')
    skills_json = db.Column(db.Text, default='[]') # stored as JSON list
    interests_json = db.Column(db.Text, default='[]') # stored as JSON list
    rating = db.Column(db.Float, default=5.0)
    reliability_rate = db.Column(db.Integer, default=100) # percentage
    on_time_rate = db.Column(db.Integer, default=100) # percentage
    completed_gigs_count = db.Column(db.Integer, default=0)
    disputes_count = db.Column(db.Integer, default=0)
    avatar_url = db.Column(db.String(255), default='')

    # Relationships
    applications = db.relationship('Application', backref='student', lazy=True)
    projects = db.relationship('Project', backref='student', lazy=True)
    portfolio_items = db.relationship('PortfolioItem', backref='student', lazy=True)

    @property
    def skills(self):
        try:
            return json.loads(self.skills_json)
        except Exception:
            return []

    @skills.setter
    def skills(self, val):
        if isinstance(val, list):
            self.skills_json = json.dumps(val)
        else:
            self.skills_json = json.dumps([s.strip() for s in str(val).split(',') if s.strip()])

    @property
    def interests(self):
        try:
            return json.loads(self.interests_json)
        except Exception:
            return []

    @interests.setter
    def interests(self, val):
        if isinstance(val, list):
            self.interests_json = json.dumps(val)
        else:
            self.interests_json = json.dumps([s.strip() for s in str(val).split(',') if s.strip()])

    @property
    def career_level_info(self):
        """
        Calculates student career tier:
        0: 🟢 FirstGig Beginner
        1–2: 🔵 Active Freelancer
        3–4: 🟣 Rising Freelancer
        5–9: ⭐ Verified Freelancer
        10–19: 🏆 Trusted Freelancer
        20+: 🚀 Pro Student
        """
        count = self.completed_gigs_count
        if count == 0:
            return {
                'tier_num': 0,
                'name': 'FirstGig Beginner',
                'badge': '🟢 FirstGig Beginner',
                'badge_icon': '🟢',
                'current_gigs': count,
                'next_target': 1,
                'progress_pct': 0,
                'next_level_name': 'Active Freelancer',
                'status_message': 'Complete 1 gig to become an Active Freelancer',
                'color_class': 'tier-beginner'
            }
        elif count in [1, 2]:
            progress = int((count / 3) * 100)
            return {
                'tier_num': 1,
                'name': 'Active Freelancer',
                'badge': '🔵 Active Freelancer',
                'badge_icon': '🔵',
                'current_gigs': count,
                'next_target': 3,
                'progress_pct': progress,
                'next_level_name': 'Rising Freelancer',
                'status_message': f'{count} / 3 gigs toward Rising Freelancer',
                'color_class': 'tier-active'
            }
        elif count in [3, 4]:
            progress = int(((count - 2) / (5 - 2)) * 100)
            return {
                'tier_num': 2,
                'name': 'Rising Freelancer',
                'badge': '🟣 Rising Freelancer',
                'badge_icon': '🟣',
                'current_gigs': count,
                'next_target': 5,
                'progress_pct': progress,
                'next_level_name': 'Verified Freelancer',
                'status_message': f'{count} / 5 gigs toward Verified Freelancer',
                'color_class': 'tier-rising'
            }
        elif 5 <= count <= 9:
            progress = int(((count - 4) / (10 - 4)) * 100)
            return {
                'tier_num': 3,
                'name': 'Verified Freelancer',
                'badge': '⭐ Verified Freelancer',
                'badge_icon': '⭐',
                'current_gigs': count,
                'next_target': 10,
                'progress_pct': progress,
                'next_level_name': 'Trusted Freelancer',
                'status_message': f'{count} / 10 gigs toward Trusted Freelancer',
                'color_class': 'tier-verified'
            }
        elif 10 <= count <= 19:
            progress = int(((count - 9) / (20 - 9)) * 100)
            return {
                'tier_num': 4,
                'name': 'Trusted Freelancer',
                'badge': '🏆 Trusted Freelancer',
                'badge_icon': '🏆',
                'current_gigs': count,
                'next_target': 20,
                'progress_pct': progress,
                'next_level_name': 'Pro Student',
                'status_message': f'{count} / 20 gigs toward Pro Student',
                'color_class': 'tier-trusted'
            }
        else:
            return {
                'tier_num': 5,
                'name': 'Pro Student',
                'badge': '🚀 Pro Student',
                'badge_icon': '🚀',
                'current_gigs': count,
                'next_target': count,
                'progress_pct': 100,
                'next_level_name': 'Top Freelancer',
                'status_message': f'{count} completed gigs — Maximum Tier Achieved!',
                'color_class': 'tier-pro'
            }


class ClientProfile(db.Model):
    __tablename__ = 'client_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    company_name = db.Column(db.String(150), nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(100), default='Technology')
    website = db.Column(db.String(200), default='')
    description = db.Column(db.Text, default='')
    avatar_url = db.Column(db.String(255), default='')
    total_spent = db.Column(db.Integer, default=0) # in INR

    # Relationships
    gigs = db.relationship('Gig', backref='client', lazy=True)
    projects = db.relationship('Project', backref='client', lazy=True)


class Gig(db.Model):
    __tablename__ = 'gigs'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client_profiles.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.Integer, nullable=False) # In INR (₹)
    difficulty = db.Column(db.String(50), nullable=False, default='Beginner') # Beginner, Medium, Advanced
    deadline_days = db.Column(db.Integer, nullable=False, default=7)
    skills_json = db.Column(db.Text, default='[]')
    status = db.Column(db.String(30), default='open') # open, in_progress, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    applications = db.relationship('Application', backref='gig', lazy=True, cascade='all, delete-orphan')
    project = db.relationship('Project', backref='gig', uselist=False)

    @property
    def skills(self):
        try:
            return json.loads(self.skills_json)
        except Exception:
            return []

    @skills.setter
    def skills(self, val):
        if isinstance(val, list):
            self.skills_json = json.dumps(val)
        else:
            self.skills_json = json.dumps([s.strip() for s in str(val).split(',') if s.strip()])


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gigs.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    proposal = db.Column(db.Text, nullable=False)
    bid_amount = db.Column(db.Integer, nullable=False)
    estimated_days = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default='pending') # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gigs.id'), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client_profiles.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    budget = db.Column(db.Integer, nullable=False)
    deadline_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), default='ASSIGNED') # ASSIGNED, IN PROGRESS, SUBMITTED, COMPLETED, OVERDUE
    # Escrow Statuses: Pending, Held, Released, Refund Requested, Refunded
    escrow_status = db.Column(db.String(30), default='Held')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    milestones = db.relationship('Milestone', backref='project', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('Submission', backref='project', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='project', lazy=True, cascade='all, delete-orphan')
    disputes = db.relationship('Dispute', backref='project', lazy=True, cascade='all, delete-orphan')
    portfolio_item = db.relationship('PortfolioItem', backref='project', uselist=False)

    @property
    def days_remaining(self):
        delta = self.deadline_date - datetime.utcnow()
        return delta.days

    @property
    def deadline_ui_status(self):
        """
        Requirements:
        🟢 Plenty of time (> 3 days)
        🟡 Deadline approaching (1-3 days)
        🔴 Overdue (<= 0 days)
        """
        if self.status == 'COMPLETED':
            return {
                'badge': '✅ Completed',
                'css_class': 'deadline-completed',
                'days': 0,
                'icon': '✅',
                'label': 'Completed on time'
            }

        delta = self.deadline_date - datetime.utcnow()
        days = delta.days
        hours = int(delta.total_seconds() // 3600)

        if delta.total_seconds() < 0:
            overdue_days = abs(days)
            return {
                'badge': '🔴 Overdue',
                'css_class': 'deadline-overdue',
                'days': days,
                'icon': '🔴',
                'label': f'Overdue by {overdue_days if overdue_days > 0 else 1} day(s)'
            }
        elif days <= 3:
            return {
                'badge': '🟡 Deadline approaching',
                'css_class': 'deadline-approaching',
                'days': days,
                'icon': '🟡',
                'label': f'{days} day(s) ({hours}h) remaining'
            }
        else:
            return {
                'badge': '🟢 Plenty of time',
                'css_class': 'deadline-plenty',
                'days': days,
                'icon': '🟢',
                'label': f'{days} days remaining'
            }

    @property
    def escrow_stepper_info(self):
        """
        Visual stepper:
        1. Payment Created
        2. Payment Held
        3. Work Submitted
        4. Client Approved
        5. Payment Released
        """
        current_step = 1
        if self.escrow_status == 'Held':
            current_step = 2
            if self.status in ['SUBMITTED']:
                current_step = 3
        elif self.escrow_status == 'Released' or self.status == 'COMPLETED':
            current_step = 5
        elif self.escrow_status in ['Refund Requested', 'Refunded']:
            current_step = 4

        steps = [
            {'num': 1, 'name': 'Payment Created', 'done': current_step >= 1, 'active': current_step == 1},
            {'num': 2, 'name': 'Payment Held in Mock Escrow', 'done': current_step >= 2, 'active': current_step == 2},
            {'num': 3, 'name': 'Work Submitted', 'done': current_step >= 3, 'active': current_step == 3},
            {'num': 4, 'name': 'Client Approved', 'done': current_step >= 4, 'active': current_step == 4},
            {'num': 5, 'name': 'Payment Released to Student', 'done': current_step >= 5, 'active': current_step == 5}
        ]
        return {
            'steps': steps,
            'current_step': current_step,
            'status': self.escrow_status
        }


class Milestone(db.Model):
    __tablename__ = 'milestones'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default='')
    amount = db.Column(db.Integer, nullable=False) # In INR
    deadline_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), default='Pending') # Pending, In Progress, Submitted, Approved


class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, default='')
    project_link = db.Column(db.String(255), default='')
    file_attachment = db.Column(db.String(255), default='')
    status = db.Column(db.String(30), default='submitted') # draft, submitted, changes_requested, approved
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, default=5) # 1 to 5 stars
    comment = db.Column(db.Text, nullable=False)
    is_verified_project = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User', foreign_keys=[reviewer_id])
    reviewee = db.relationship('User', foreign_keys=[reviewee_id])


class PortfolioItem(db.Model):
    __tablename__ = 'portfolio_items'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), default='')
    skills_used = db.Column(db.String(200), default='')
    completion_date = db.Column(db.String(100), default='')
    client_review_snippet = db.Column(db.Text, default='')
    project_link = db.Column(db.String(255), default='')
    is_verified_project = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Dispute(db.Model):
    __tablename__ = 'disputes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    raised_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text, default='')
    status = db.Column(db.String(30), default='Open') # Open, Under Review, Resolved
    admin_decision = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    raised_by = db.relationship('User', foreign_keys=[raised_by_id])


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), default='')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
