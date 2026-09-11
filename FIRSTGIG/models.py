from datetime import datetime, date, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # student | client | admin
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student_profile = db.relationship("StudentProfile", backref="user", uselist=False, cascade="all, delete-orphan")
    client_profile = db.relationship("ClientProfile", backref="user", uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_student(self):
        return self.role == "student"

    def is_client(self):
        return self.role == "client"

    def is_admin(self):
        return self.role == "admin"

    @property
    def is_active(self):
        return bool(self.is_active_account)


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    college = db.Column(db.String(180), nullable=False)
    branch = db.Column(db.String(120), nullable=False)
    academic_year = db.Column(db.String(40), nullable=False)
    bio = db.Column(db.Text, default="")
    skills = db.Column(db.Text, default="")  # comma-separated
    interests = db.Column(db.Text, default="")
    college_email = db.Column(db.String(180))
    verification_code = db.Column(db.String(12))
    verified = db.Column(db.Boolean, default=False)
    avatar = db.Column(db.String(255))
    completed_gigs = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    reliability_score = db.Column(db.Float, default=70.0)
    on_time_percentage = db.Column(db.Float, default=100.0)
    dispute_count = db.Column(db.Integer, default=0)
    cancellation_count = db.Column(db.Integer, default=0)

    portfolio_items = db.relationship("Portfolio", backref="student", lazy="dynamic", cascade="all, delete-orphan")

    def skill_list(self):
        return [s.strip() for s in (self.skills or "").split(",") if s.strip()]

    def interest_list(self):
        return [s.strip() for s in (self.interests or "").split(",") if s.strip()]


class ClientProfile(db.Model):
    __tablename__ = "client_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    company_name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    rating = db.Column(db.Float, default=0.0)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String(400), nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Gig(db.Model):
    __tablename__ = "gigs"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    required_skills = db.Column(db.Text, default="")
    budget = db.Column(db.Integer, nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    difficulty = db.Column(db.String(20), default="Beginner")  # Beginner | Intermediate | Advanced
    status = db.Column(db.String(30), default="OPEN")  # OPEN | APPLIED | ASSIGNED | CLOSED | REMOVED
    requirements = db.Column(db.Text, default="")
    milestone_count = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship("User", foreign_keys=[client_id])
    applications = db.relationship("Application", backref="gig", lazy="dynamic", cascade="all, delete-orphan")
    project = db.relationship("Project", backref="gig", uselist=False)

    def skill_list(self):
        return [s.strip() for s in (self.required_skills or "").split(",") if s.strip()]


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey("gigs.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    proposal = db.Column(db.Text, nullable=False)
    expected_completion = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Pending | Accepted | Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("User", foreign_keys=[student_id])

    __table_args__ = (db.UniqueConstraint("gig_id", "student_id", name="uq_gig_student"),)


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey("gigs.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    budget = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, default=date.today)
    deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default="IN_PROGRESS")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    submission_message = db.Column(db.Text)
    submission_link = db.Column(db.String(400))
    submission_file = db.Column(db.String(255))
    submitted_at = db.Column(db.DateTime)
    change_request = db.Column(db.Text)
    student_explanation = db.Column(db.Text)

    client = db.relationship("User", foreign_keys=[client_id])
    student = db.relationship("User", foreign_keys=[student_id])
    milestones = db.relationship("Milestone", backref="project", cascade="all, delete-orphan", order_by="Milestone.id")
    payment = db.relationship("Payment", backref="project", uselist=False, cascade="all, delete-orphan")
    reviews = db.relationship("Review", backref="project", cascade="all, delete-orphan")
    disputes = db.relationship("Dispute", backref="project", cascade="all, delete-orphan")

    def days_remaining(self):
        if not self.deadline:
            return 0
        return (self.deadline - date.today()).days

    def deadline_tone(self):
        days = self.days_remaining()
        if self.status in ("COMPLETED", "REFUNDED", "CANCELLED"):
            return "done"
        if days < 0:
            return "overdue"
        if days <= 2:
            return "soon"
        return "ok"

    def is_participant(self, user_id):
        return user_id in (self.client_id, self.student_id)


class Milestone(db.Model):
    __tablename__ = "milestones"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    amount = db.Column(db.Integer, nullable=False)
    deadline = db.Column(db.Date)
    status = db.Column(db.String(20), default="Pending")  # Pending | In Progress | Submitted | Approved


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="Held")  # Pending | Held | Released | Refund Requested | Refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    released_at = db.Column(db.DateTime)
    refunded_at = db.Column(db.DateTime)
    note = db.Column(db.String(255), default="Simulated mock escrow — not real money")


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reviewed_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship("User", foreign_keys=[reviewer_id])
    reviewed_user = db.relationship("User", foreign_keys=[reviewed_user_id])

    __table_args__ = (db.UniqueConstraint("project_id", "reviewer_id", name="uq_review_once"),)


class Portfolio(db.Model):
    __tablename__ = "portfolio"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    skills = db.Column(db.Text, default="")
    is_public = db.Column(db.Boolean, default=True)
    project_link = db.Column(db.String(400))
    contribution = db.Column(db.Text, default="")
    completion_date = db.Column(db.Date)
    client_review = db.Column(db.Text)

    project = db.relationship("Project")


class Dispute(db.Model):
    __tablename__ = "disputes"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    raised_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="Open")  # Open | Under Review | Resolved
    admin_decision = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    raiser = db.relationship("User", foreign_keys=[raised_by])
