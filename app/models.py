from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    resumes = db.relationship("Resume", backref="owner", cascade="all, delete-orphan")
    jobs = db.relationship("Job", backref="owner", cascade="all, delete-orphan")
    skills = db.relationship("UserSkill", backref="owner", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Resume(db.Model):
    __tablename__ = "resumes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False, default="")
    stored_filename = db.Column(db.String(255), nullable=False, default="")
    file_ext = db.Column(db.String(8), nullable=False, default="")
    is_archived = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # extraction results (stored as JSON text)
    raw_text = db.Column(db.Text, nullable=False, default="")
    sections_json = db.Column(db.Text, nullable=False, default="{}")
    skills_json = db.Column(db.Text, nullable=False, default="[]")
    contact_json = db.Column(db.Text, nullable=False, default="{}")
    education_json = db.Column(db.Text, nullable=False, default="[]")
    experience_json = db.Column(db.Text, nullable=False, default="[]")
    projects_json = db.Column(db.Text, nullable=False, default="[]")
    certifications_json = db.Column(db.Text, nullable=False, default="[]")

    word_count = db.Column(db.Integer, default=0)
    health_score = db.Column(db.Integer)  # last computed checklist score 0-100
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    @property
    def section_names(self):
        import json
        return sorted(json.loads(self.sections_json or "{}").keys())


SKILL_LEVELS = ["Not Started", "Learning", "Practicing", "Comfortable", "Expert"]

class UserSkill(db.Model):
    __tablename__ = "user_skills"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False, default="Not Started")

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_user_skill"),)


class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    company = db.Column(db.String(160), default="")
    role = db.Column(db.String(160), default="")
    location = db.Column(db.String(160), default="")
    remote = db.Column(db.Boolean, default=False)
    salary = db.Column(db.String(80), default="")
    experience = db.Column(db.String(80), default="")
    work_type = db.Column(db.String(40), default="")   # Full-time / Internship...
    source_text = db.Column(db.Text, nullable=False, default="")

    required_skills_json = db.Column(db.Text, default="[]")
    preferred_skills_json = db.Column(db.Text, default="[]")
    keywords_json = db.Column(db.Text, default="{}")

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    application = db.relationship("Application", backref="job", uselist=False, cascade="all, delete-orphan")
    interviews = db.relationship("Interview", backref="job", cascade="all, delete-orphan")

    @property
    def required_skills(self):
        import json
        return json.loads(self.required_skills_json or "[]")

    @property
    def preferred_skills(self):
        import json
        return json.loads(self.preferred_skills_json or "[]")


APPLICATION_STATUSES = [
    "Saved", "Applied", "Screening", "Assessment", "Interview",
    "Final Interview", "Offer", "Rejected", "Withdrawn",
]

STATUS_CLASS = {
    "Saved": "st-saved", "Applied": "st-applied", "Screening": "st-screening",
    "Assessment": "st-assessment", "Interview": "st-interview",
    "Final Interview": "st-final", "Offer": "st-offer",
    "Rejected": "st-rejected", "Withdrawn": "st-withdrawn",
}


class Application(db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"))
    status = db.Column(db.String(30), nullable=False, default="Saved", index=True)
    applied_on = db.Column(db.Date)
    notes = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    resume = db.relationship("Resume")
    interviews = db.relationship("Interview", backref="application", cascade="all, delete-orphan")
    history = db.relationship("StatusHistory", backref="application", cascade="all, delete-orphan",
                              order_by="StatusHistory.changed_at")

    @staticmethod
    def _aware(dt):
        """SQLite returns naive datetimes; treat them as UTC."""
        if dt is None:
            return utcnow()
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @property
    def is_stale(self):
        """No status movement for 14+ days while still open."""
        if self.status in ("Rejected", "Withdrawn", "Offer"):
            return False
        return (utcnow() - self._aware(self.updated_at)).days >= 14

    @property
    def days_in_status(self):
        return (utcnow() - self._aware(self.updated_at)).days


class StatusHistory(db.Model):
    __tablename__ = "status_history"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True)
    from_status = db.Column(db.String(30), default="")
    to_status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.Text, default="")
    changed_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Interview(db.Model):
    __tablename__ = "interviews"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), index=True)
    round_name = db.Column(db.String(120), default="Interview")
    scheduled_at = db.Column(db.DateTime, nullable=False)
    mode = db.Column(db.String(40), default="")       # Phone / Video / Onsite
    location = db.Column(db.String(160), default="")
    outcome = db.Column(db.String(40), default="")    # Pending / Passed / Failed
    notes = db.Column(db.Text, default="")

    @property
    def is_upcoming(self):
        return self.outcome == "Pending" and self.scheduled_at >= utcnow()


class LearningGoal(db.Model):
    """A skill the user wants to learn or strengthen, from a job-match gap."""
    __tablename__ = "learning_goals"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(60), default="Other / General")
    source_job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"))  # job that inspired it
    source_company = db.Column(db.String(160), default="")           # denormalized for display
    priority = db.Column(db.Integer, default=2)                       # 1 high, 2 med, 3 low
    progress = db.Column(db.Integer, default=0)                       # 0-100, user-set
    done = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_learning_goal"),
    )

    @property
    def is_open(self):
        return not self.done


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
