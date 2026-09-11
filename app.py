from datetime import datetime, timedelta
import os
import json
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g
)
from models import (
    db, User, StudentProfile, ClientProfile, Gig,
    Application, Project, Milestone, Submission,
    Review, PortfolioItem, Dispute, Notification
)
from recommendation import calculate_gig_match, get_recommended_gigs

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-this-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///firstgig.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()


# ==============================================================================
# CONTEXT PROCESSOR & AUTH HELPERS
# ==============================================================================
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)

@app.context_processor
def inject_global_context():
    unread_count = 0
    if g.user:
        unread_count = Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
    return {
        'current_user': g.user,
        'unread_notifs_count': unread_count,
        'now': datetime.utcnow()
    }

def login_required(view_func):
    def wrapper(*args, **kwargs):
        if not g.user:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

def role_required(required_role):
    def decorator(view_func):
        def wrapper(*args, **kwargs):
            if not g.user:
                flash('Please log in first.', 'warning')
                return redirect(url_for('login'))
            if g.user.role != required_role and g.user.role != 'admin':
                flash('Unauthorized access for your account role.', 'danger')
                return redirect(url_for('index'))
            return view_func(*args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return wrapper
    return decorator


# ==============================================================================
# DEMO ACCOUNT SWITCHER (FOR INSTANT EVALUATION)
# ==============================================================================
@app.route('/switch-demo/<role>')
def switch_demo(role):
    """
    1-Click demo test switcher so judges can test every feature instantly.
    """
    target_user = None
    if role == 'verified_student':
        target_user = User.query.filter_by(email='rahul@college.edu').first()
        dest = 'student_dashboard'
    elif role == 'beginner_student':
        target_user = User.query.filter_by(email='priya@college.edu').first()
        dest = 'student_dashboard'
    elif role == 'client':
        target_user = User.query.filter_by(email='vikram@studio.com').first()
        dest = 'client_dashboard'
    elif role == 'admin':
        target_user = User.query.filter_by(email='admin@firstgig.com').first()
        dest = 'admin_dashboard'
    else:
        flash('Invalid demo role.', 'danger')
        return redirect(url_for('index'))

    if target_user:
        session['user_id'] = target_user.id
        flash(f'Switched to Demo Account: {target_user.username} ({target_user.role.title()})', 'success')
        return redirect(url_for(dest))
    else:
        flash('Demo data not yet initialized. Please run seed script.', 'warning')
        return redirect(url_for('index'))


# ==============================================================================
# PUBLIC ROUTES
# ==============================================================================
@app.route('/')
def index():
    # 1. Recommended Gigs
    open_gigs = Gig.query.filter_by(status='open').order_by(Gig.created_at.desc()).all()
    student = g.user.student_profile if (g.user and g.user.role == 'student') else None

    # Fallback to demo verified student profile for rich guest preview if not logged in
    if not student:
        demo_student = StudentProfile.query.first()
        rec_gigs = get_recommended_gigs(demo_student, open_gigs, limit=3)
    else:
        rec_gigs = get_recommended_gigs(student, open_gigs, limit=3)

    featured_gigs = open_gigs[:6]
    featured_reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
    featured_portfolio = PortfolioItem.query.filter_by(is_public=True).order_by(PortfolioItem.created_at.desc()).limit(3).all()
    total_gigs_count = Gig.query.count()

    return render_template(
        'index.html',
        recommended_gigs=rec_gigs,
        featured_gigs=featured_gigs,
        featured_reviews=featured_reviews,
        featured_portfolio=featured_portfolio,
        total_gigs_count=total_gigs_count
    )

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/gigs')
def gigs():
    search_q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    difficulty = request.args.get('difficulty', '').strip()
    max_budget = request.args.get('max_budget', '').strip()
    skill_filter = request.args.get('skill', '').strip()

    query = Gig.query.filter_by(status='open')

    if search_q:
        query = query.filter((Gig.title.ilike(f'%{search_q}%')) | (Gig.description.ilike(f'%{search_q}%')))
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if max_budget:
        try:
            query = query.filter(Gig.budget <= int(max_budget))
        except ValueError:
            pass

    all_gigs = query.order_by(Gig.created_at.desc()).all()

    if skill_filter:
        filtered = []
        for g_item in all_gigs:
            if any(skill_filter.lower() in s.lower() for s in g_item.skills):
                filtered.append(g_item)
        all_gigs = filtered

    all_categories = [
        'Web Development', 'UI/UX Design', 'Python & Backend',
        'Mobile Development', 'Data & Analytics', 'Content & SEO'
    ]

    return render_template(
        'gigs.html',
        gigs=all_gigs,
        search_query=search_q,
        selected_category=category,
        selected_difficulty=difficulty,
        max_budget=max_budget,
        selected_skill=skill_filter,
        all_categories=all_categories
    )

@app.route('/gig/<int:gig_id>')
def gig_detail(gig_id):
    gig = Gig.query.get_or_404(gig_id)
    existing_app = None
    if g.user and g.user.role == 'student' and g.user.student_profile:
        existing_app = Application.query.filter_by(
            gig_id=gig.id,
            student_id=g.user.student_profile.id
        ).first()

    return render_template(
        'gig_detail.html',
        gig=gig,
        existing_application=existing_app
    )


# ==============================================================================
# AUTHENTICATION (LOGIN, REGISTER, LOGOUT)
# ==============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('dashboard_router'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard_router'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('dashboard_router'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'student')
        password = request.form.get('password', '')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or Email already in use. Please choose another or sign in.', 'danger')
            return redirect(url_for('register'))

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if role == 'student':
            college_name = request.form.get('college_name', 'University of Technology')
            college_email = request.form.get('college_email', email)
            branch = request.form.get('branch', 'Computer Science')
            academic_year = request.form.get('academic_year', '3rd Year')
            skills_str = request.form.get('skills', '')

            # Auto-verify if email ends with .edu or .ac.in
            auto_verify = any(college_email.endswith(ext) for ext in ['.edu', '.ac.in'])

            student_prof = StudentProfile(
                user_id=user.id,
                full_name=full_name,
                college_name=college_name,
                college_email=college_email,
                branch=branch,
                academic_year=academic_year,
                is_verified=auto_verify
            )
            student_prof.skills = skills_str
            student_prof.interests = "Web Development, Python, UI Design"
            db.session.add(student_prof)

        elif role == 'client':
            company_name = request.form.get('company_name', full_name)
            industry = request.form.get('industry', 'Technology')
            website = request.form.get('website', '')

            client_prof = ClientProfile(
                user_id=user.id,
                company_name=company_name,
                contact_name=full_name,
                industry=industry,
                website=website
            )
            db.session.add(client_prof)

        db.session.commit()
        session['user_id'] = user.id
        flash('Account successfully registered! Welcome to FirstGig.', 'success')
        return redirect(url_for('dashboard_router'))

    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard_router():
    if g.user.role == 'student':
        return redirect(url_for('student_dashboard'))
    elif g.user.role == 'client':
        return redirect(url_for('client_dashboard'))
    elif g.user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('index'))


# ==============================================================================
# STUDENT WORKFLOW ROUTES
# ==============================================================================
@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    profile = g.user.student_profile
    active_projects = Project.query.filter_by(student_id=profile.id).order_by(Project.updated_at.desc()).all()
    open_gigs = Gig.query.filter_by(status='open').all()
    rec_gigs = get_recommended_gigs(profile, open_gigs, limit=3)

    # Calculate simulated escrow held
    held_escrow = sum(p.budget for p in active_projects if p.escrow_status == 'Held')

    return render_template(
        'student/dashboard.html',
        profile=profile,
        tier_info=profile.career_level_info,
        active_projects=active_projects,
        recommended_gigs=rec_gigs,
        simulated_held_escrow=held_escrow
    )

@app.route('/student/profile')
@login_required
@role_required('student')
def student_profile():
    profile = g.user.student_profile
    reviews = Review.query.filter_by(reviewee_id=g.user.id).order_by(Review.created_at.desc()).all()
    portfolio = PortfolioItem.query.filter_by(student_id=profile.id).order_by(PortfolioItem.created_at.desc()).all()
    return render_template(
        'student/profile.html',
        profile=profile,
        reviews=reviews,
        portfolio_items=portfolio
    )

@app.route('/student/update-profile', methods=['POST'])
@login_required
@role_required('student')
def update_student_profile():
    profile = g.user.student_profile
    profile.full_name = request.form.get('full_name', profile.full_name)
    profile.bio = request.form.get('bio', profile.bio)
    profile.skills = request.form.get('skills', '')
    profile.interests = request.form.get('interests', '')
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('student_profile'))

@app.route('/gig/<int:gig_id>/apply', methods=['POST'])
@login_required
@role_required('student')
def apply_gig(gig_id):
    gig = Gig.query.get_or_404(gig_id)
    profile = g.user.student_profile

    # Check if already applied
    existing = Application.query.filter_by(gig_id=gig.id, student_id=profile.id).first()
    if existing:
        flash('You have already submitted a proposal for this gig.', 'info')
        return redirect(url_for('gig_detail', gig_id=gig.id))

    proposal = request.form.get('proposal', '')
    bid_amount = int(request.form.get('bid_amount', gig.budget))
    est_days = int(request.form.get('estimated_days', gig.deadline_days))

    application = Application(
        gig_id=gig.id,
        student_id=profile.id,
        proposal=proposal,
        bid_amount=bid_amount,
        estimated_days=est_days
    )
    db.session.add(application)

    # Notify client
    client_user = gig.client.user
    notif = Notification(
        user_id=client_user.id,
        title=f"New Applicant for {gig.title}",
        message=f"{profile.full_name} ({profile.career_level_info['badge']}) submitted a proposal of ₹{bid_amount:,}.",
        link=url_for('client_applications', gig_id=gig.id)
    )
    db.session.add(notif)
    db.session.commit()

    flash('Proposal successfully submitted to client!', 'success')
    return redirect(url_for('gig_detail', gig_id=gig.id))


# ==============================================================================
# CLIENT WORKFLOW ROUTES
# ==============================================================================
@app.route('/client/dashboard')
@login_required
@role_required('client')
def client_dashboard():
    profile = g.user.client_profile
    gigs = Gig.query.filter_by(client_id=profile.id).order_by(Gig.created_at.desc()).all()
    active_projects = Project.query.filter_by(client_id=profile.id).order_by(Project.updated_at.desc()).all()

    # Total pending applicants across client's gigs
    pending_count = Application.query.join(Gig).filter(
        Gig.client_id == profile.id,
        Application.status == 'pending'
    ).count()

    held_escrow = sum(p.budget for p in active_projects if p.escrow_status == 'Held')

    return render_template(
        'client/dashboard.html',
        profile=profile,
        gigs=gigs,
        active_projects=active_projects,
        total_gigs_count=len(gigs),
        pending_applicants_count=pending_count,
        simulated_held_escrow=held_escrow
    )

@app.route('/client/profile')
@login_required
@role_required('client')
def client_profile():
    return render_template('profile_view.html', client=g.user.client_profile)

@app.route('/client/post-gig', methods=['GET', 'POST'])
@login_required
@role_required('client')
def post_gig():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'Web Development')
        budget = int(request.form.get('budget', 3000))
        difficulty = request.form.get('difficulty', 'Beginner')
        deadline_days = int(request.form.get('deadline_days', 7))
        skills_str = request.form.get('skills', '')

        gig = Gig(
            client_id=g.user.client_profile.id,
            title=title,
            description=description,
            category=category,
            budget=budget,
            difficulty=difficulty,
            deadline_days=deadline_days
        )
        gig.skills = skills_str
        db.session.add(gig)
        db.session.commit()

        flash('Your gig has been posted to the marketplace!', 'success')
        return redirect(url_for('client_dashboard'))

    return render_template('client/post_gig.html')

@app.route('/client/applications')
@login_required
def client_applications():
    gig_id = request.args.get('gig_id')
    if g.user.role == 'client':
        query = Application.query.join(Gig).filter(Gig.client_id == g.user.client_profile.id)
        if gig_id:
            query = query.filter(Application.gig_id == gig_id)
        apps = query.order_by(Application.created_at.desc()).all()
    else:
        # Student view of their applications
        apps = Application.query.filter_by(student_id=g.user.student_profile.id).order_by(Application.created_at.desc()).all()

    return render_template('applications/list.html', applications=apps)

@app.route('/application/<int:app_id>/decide', methods=['POST'])
@login_required
@role_required('client')
def decide_application(app_id):
    decision = request.form.get('decision') # 'accept' or 'reject'
    app_record = Application.query.get_or_404(app_id)

    # Verify authorization
    if app_record.gig.client_id != g.user.client_profile.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('client_applications'))

    if decision == 'accept':
        app_record.status = 'accepted'
        gig = app_record.gig
        gig.status = 'in_progress'

        # Create Project in database
        deadline_date = datetime.utcnow() + timedelta(days=app_record.estimated_days)
        project = Project(
            gig_id=gig.id,
            client_id=gig.client_id,
            student_id=app_record.student_id,
            title=gig.title,
            description=gig.description,
            budget=app_record.bid_amount,
            deadline_date=deadline_date,
            status='ASSIGNED',
            escrow_status='Held'
        )
        db.session.add(project)
        db.session.flush()

        # Generate standard milestones
        half_budget = int(app_record.bid_amount * 0.5)
        m1 = Milestone(
            project_id=project.id,
            title="Design & Architecture Setup",
            description="Initial prototypes, setup, and structure",
            amount=half_budget,
            deadline_date=datetime.utcnow() + timedelta(days=max(1, app_record.estimated_days // 2)),
            status="In Progress"
        )
        m2 = Milestone(
            project_id=project.id,
            title="Core Implementation & Final Testing",
            description="Complete functional deliverable with documentation",
            amount=app_record.bid_amount - half_budget,
            deadline_date=deadline_date,
            status="Pending"
        )
        db.session.add_all([m1, m2])

        # Notify student
        student_user = app_record.student.user
        notif = Notification(
            user_id=student_user.id,
            title=f"Proposal Accepted: {gig.title}!",
            message=f"{gig.client.company_name} accepted your proposal! ₹{project.budget:,} is held in Mock Escrow.",
            link=url_for('project_detail', project_id=project.id)
        )
        db.session.add(notif)
        db.session.commit()

        flash(f'Proposal accepted! Project created and ₹{project.budget:,} deposited into Mock Escrow.', 'success')
        return redirect(url_for('project_detail', project_id=project.id))

    elif decision == 'reject':
        app_record.status = 'rejected'
        db.session.commit()
        flash('Proposal rejected.', 'info')
        return redirect(url_for('client_applications'))

    return redirect(url_for('client_applications'))


# ==============================================================================
# PROJECT WORKSPACE & DELIVERABLES (ESCROW & MILESTONES)
# ==============================================================================
@app.route('/projects')
@login_required
def projects_list():
    if g.user.role == 'student':
        projects = Project.query.filter_by(student_id=g.user.student_profile.id).order_by(Project.updated_at.desc()).all()
    elif g.user.role == 'client':
        projects = Project.query.filter_by(client_id=g.user.client_profile.id).order_by(Project.updated_at.desc()).all()
    else:
        projects = Project.query.order_by(Project.updated_at.desc()).all()

    return render_template('projects/list.html', projects=projects)

@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)

    # Check deadline status update
    if project.status != 'COMPLETED' and project.deadline_ui_status['days'] <= 0:
        project.status = 'OVERDUE'
        db.session.commit()

    return render_template('projects/detail.html', project=project)

@app.route('/project/<int:project_id>/submit', methods=['POST'])
@login_required
@role_required('student')
def submit_project_work(project_id):
    project = Project.query.get_or_404(project_id)
    if project.student_id != g.user.student_profile.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('projects_list'))

    message = request.form.get('message', '')
    description = request.form.get('description', '')
    project_link = request.form.get('project_link', '')
    action_type = request.form.get('action_type', 'submit')

    sub_status = 'submitted' if action_type == 'submit' else 'draft'
    submission = Submission(
        project_id=project.id,
        message=message,
        description=description,
        project_link=project_link,
        status=sub_status
    )
    db.session.add(submission)

    if action_type == 'submit':
        project.status = 'SUBMITTED'

        # Notify client
        client_user = project.client.user
        notif = Notification(
            user_id=client_user.id,
            title=f"Work Submitted for: {project.title}",
            message=f"{project.student.full_name} has submitted deliverables for your review.",
            link=url_for('project_detail', project_id=project.id)
        )
        db.session.add(notif)
        flash('Deliverable submitted successfully to client for review!', 'success')
    else:
        flash('Draft saved successfully.', 'info')

    db.session.commit()
    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/project/<int:project_id>/approve', methods=['POST'])
@login_required
@role_required('client')
def approve_project_work(project_id):
    project = Project.query.get_or_404(project_id)
    if project.client_id != g.user.client_profile.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('projects_list'))

    decision = request.form.get('decision')

    if decision == 'approve':
        project.status = 'COMPLETED'
        project.escrow_status = 'Released'

        # Update milestones
        for m in project.milestones:
            m.status = 'Approved'

        # Create verified review
        comment = request.form.get('comment', 'Excellent deliverable delivered on time!')
        rating = int(request.form.get('rating', 5))
        review = Review(
            project_id=project.id,
            reviewer_id=g.user.id,
            reviewee_id=project.student.user_id,
            rating=rating,
            comment=comment,
            is_verified_project=True
        )
        db.session.add(review)

        # Update student stats and advance career tier!
        student = project.student
        student.completed_gigs_count += 1
        # Recalculate average rating
        all_revs = Review.query.filter_by(reviewee_id=student.user_id).all()
        ratings = [r.rating for r in all_revs] + [rating]
        student.rating = round(sum(ratings) / len(ratings), 1)

        # Automatically create portfolio item
        skills_str = project.gig.skills_json if project.gig else "[]"
        try:
            skills_list = json.loads(skills_str)
            skills_text = ", ".join(skills_list)
        except Exception:
            skills_text = "Web Development"

        port_item = PortfolioItem(
            student_id=student.id,
            project_id=project.id,
            title=project.title,
            description=project.description[:240],
            skills_used=skills_text,
            completion_date=datetime.utcnow().strftime('%b %Y'),
            client_review_snippet=comment[:150],
            project_link=project.submissions[-1].project_link if project.submissions else "",
            is_verified_project=True,
            is_public=True
        )
        db.session.add(port_item)

        # Notify student
        student_user = student.user
        notif = Notification(
            user_id=student_user.id,
            title="🎉 Project Approved & Mock Escrow Released!",
            message=f"{project.client.company_name} approved your work! ₹{project.budget:,} mock escrow released. New tier: {student.career_level_info['badge']}!",
            link=url_for('project_detail', project_id=project.id)
        )
        db.session.add(notif)
        db.session.commit()

        flash(f'Project approved! Simulated escrow of ₹{project.budget:,} released and verified review recorded.', 'success')

    elif decision == 'request_changes':
        project.status = 'IN PROGRESS'
        # Notify student
        student_user = project.student.user
        notif = Notification(
            user_id=student_user.id,
            title=f"Modifications Requested for {project.title}",
            message=f"{project.client.company_name} reviewed your submission and requested adjustments.",
            link=url_for('project_detail', project_id=project.id)
        )
        db.session.add(notif)
        db.session.commit()
        flash('Changes requested. Student notified to update deliverable.', 'info')

    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/project/<int:project_id>/dispute', methods=['POST'])
@login_required
def file_dispute(project_id):
    project = Project.query.get_or_404(project_id)
    reason = request.form.get('reason', 'Scope disagreement')
    description = request.form.get('description', '')
    evidence = request.form.get('evidence', '')

    dispute = Dispute(
        project_id=project.id,
        raised_by_id=g.user.id,
        reason=reason,
        description=description,
        evidence=evidence,
        status='Open'
    )
    db.session.add(dispute)

    # Notify admin
    admin_user = User.query.filter_by(role='admin').first()
    if admin_user:
        notif = Notification(
            user_id=admin_user.id,
            title=f"⚠️ New Dispute: {project.title}",
            message=f"Dispute raised by {g.user.username}: {reason}",
            link=url_for('admin_dashboard')
        )
        db.session.add(notif)

    db.session.commit()
    flash('Dispute submitted to platform administrator for mediation.', 'warning')
    return redirect(url_for('project_detail', project_id=project.id))


# ==============================================================================
# PORTFOLIO & NOTIFICATIONS & PROFILES
# ==============================================================================
@app.route('/portfolio')
def portfolio():
    items = PortfolioItem.query.filter_by(is_public=True).order_by(PortfolioItem.created_at.desc()).all()
    return render_template('portfolio.html', portfolio_items=items)

@app.route('/portfolio/add', methods=['POST'])
@login_required
@role_required('student')
def add_portfolio_item():
    student = g.user.student_profile
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    skills_used = request.form.get('skills_used', '').strip()
    project_link = request.form.get('project_link', '').strip()

    item = PortfolioItem(
        student_id=student.id,
        title=title,
        description=description,
        skills_used=skills_used,
        completion_date=datetime.utcnow().strftime('%b %Y'),
        project_link=project_link,
        is_verified_project=True,
        is_public=True
    )
    db.session.add(item)
    db.session.commit()
    flash('Project showcase item added to your portfolio!', 'success')
    return redirect(url_for('portfolio'))

@app.route('/portfolio/toggle/<int:item_id>', methods=['POST'])
@login_required
@role_required('student')
def toggle_portfolio_visibility(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    if item.student_id != g.user.student_profile.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('portfolio'))

    item.is_public = not item.is_public
    db.session.commit()
    flash(f"Portfolio item visibility set to {'Public' if item.is_public else 'Hidden'}.", 'info')
    return redirect(url_for('portfolio'))

@app.route('/profile/<int:user_id>')
def view_profile(user_id):
    target_user = User.query.get_or_404(user_id)
    if target_user.role == 'student':
        reviews = Review.query.filter_by(reviewee_id=target_user.id).order_by(Review.created_at.desc()).all()
        return render_template('profile_view.html', student=target_user.student_profile, reviews=reviews)
    elif target_user.role == 'client':
        return render_template('profile_view.html', client=target_user.client_profile)
    else:
        return redirect(url_for('index'))

@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=g.user.id).order_by(Notification.created_at.desc()).all()
    # Mark as read
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)

@app.route('/notifications/clear', methods=['POST'])
@login_required
def clear_notifications():
    Notification.query.filter_by(user_id=g.user.id).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('notifications'))


# ==============================================================================
# ADMIN SAAS DASHBOARD & DISPUTE ARBITRATION
# ==============================================================================
@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    total_students = StudentProfile.query.count()
    verified_students = StudentProfile.query.filter_by(is_verified=True).count()
    total_clients = ClientProfile.query.count()
    total_gigs = Gig.query.count()
    open_gigs = Gig.query.filter_by(status='open').count()

    active_projects = Project.query.filter(Project.status.in_(['ASSIGNED', 'IN PROGRESS'])).count()
    submitted_projects = Project.query.filter_by(status='SUBMITTED').count()
    completed_projects = Project.query.filter_by(status='COMPLETED').count()
    overdue_projects = Project.query.filter_by(status='OVERDUE').count()
    disputed_projects = Dispute.query.filter_by(status='Open').count()

    # Escrow metrics
    all_projects = Project.query.all()
    escrow_held = sum(p.budget for p in all_projects if p.escrow_status == 'Held')
    escrow_released = sum(p.budget for p in all_projects if p.escrow_status == 'Released')
    escrow_refunded = sum(p.budget for p in all_projects if p.escrow_status == 'Refunded')

    stats = {
        'total_students': total_students,
        'verified_students': verified_students,
        'total_clients': total_clients,
        'total_gigs': total_gigs,
        'open_gigs': open_gigs,
        'active_projects': active_projects,
        'submitted_projects': submitted_projects,
        'completed_projects': completed_projects,
        'overdue_projects': overdue_projects,
        'disputed_projects': disputed_projects,
        'escrow_held': escrow_held,
        'escrow_released': escrow_released,
        'escrow_refunded': escrow_refunded
    }

    disputes = Dispute.query.order_by(Dispute.created_at.desc()).all()
    all_students = StudentProfile.query.all()

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        disputes=disputes,
        all_students=all_students
    )

@app.route('/admin/dispute/<int:dispute_id>/resolve', methods=['POST'])
@login_required
@role_required('admin')
def admin_resolve_dispute(dispute_id):
    dispute = Dispute.query.get_or_404(dispute_id)
    action_type = request.form.get('action_type') # refund_client, release_payment, extend_deadline, mark_completed
    project = dispute.project

    if action_type == 'refund_client':
        project.escrow_status = 'Refunded'
        project.status = 'CANCELLED'
        dispute.status = 'Resolved'
        dispute.admin_decision = 'Full mock escrow refunded to client after dispute inspection.'
        flash('Refund issued to client. Dispute marked as resolved.', 'success')

    elif action_type == 'release_payment':
        project.escrow_status = 'Released'
        project.status = 'COMPLETED'
        dispute.status = 'Resolved'
        dispute.admin_decision = 'Payment released to student based on verified deliverables.'
        # Increment student stats
        project.student.completed_gigs_count += 1
        flash('Payment released to student. Dispute marked as resolved.', 'success')

    elif action_type == 'extend_deadline':
        project.deadline_date = project.deadline_date + timedelta(days=7)
        if project.status == 'OVERDUE':
            project.status = 'IN PROGRESS'
        dispute.status = 'Under Review'
        dispute.admin_decision = 'Deadline extended by 7 days for mutual completion.'
        flash('Project deadline extended by 7 days.', 'info')

    elif action_type == 'mark_completed':
        project.status = 'COMPLETED'
        project.escrow_status = 'Released'
        dispute.status = 'Resolved'
        dispute.admin_decision = 'Project marked as completed by administrator.'
        project.student.completed_gigs_count += 1
        flash('Project marked completed.', 'success')

    db.session.commit()
    return redirect(url_for('admin_dashboard') + '#disputes-section')

@app.route('/admin/student/<int:student_id>/verify', methods=['POST'])
@login_required
@role_required('admin')
def admin_verify_student(student_id):
    student = StudentProfile.query.get_or_404(student_id)
    student.is_verified = True
    db.session.commit()

    # Notify student
    notif = Notification(
        user_id=student.user_id,
        title="🎓 College Verification Approved!",
        message="Your student email has been officially verified. Your 🎓 Verified Student badge is now active!",
        link=url_for('student_profile')
    )
    db.session.add(notif)
    db.session.commit()

    flash(f"College verification approved for {student.full_name}!", 'success')
    return redirect(url_for('admin_dashboard'))


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
