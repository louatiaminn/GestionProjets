from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from enum import Enum
from . import db 

db = SQLAlchemy()

class UserRole(Enum):
    ADMIN = "admin"
    MEMBER = "member"
    PROJECT_MANAGER = "project_manager" 

class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"  
    COMPLETED = "completed"
    
class CommentSentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


project_members = db.Table('project_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('role', db.String(20), default='member'),
    db.Column('joined_at', db.DateTime, default=datetime.utcnow)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.MEMBER)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    owned_projects = db.relationship('Project', backref='owner', lazy=True, 
                                   foreign_keys='Project.owner_id',
                                   cascade='all, delete-orphan')
    assigned_tasks = db.relationship('Task', backref='assignee', lazy=True,
                                   cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy=True,
                             cascade='all, delete-orphan')
    
    projects = db.relationship('Project', secondary=project_members, 
                              back_populates='members', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    # Updated foreign key with CASCADE DELETE
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    @classmethod
    def create_project(cls, name, owner, description=None, start_date=None, deadline=None):
        project = cls(
            name=name, 
            owner=owner, 
            description=description, 
            start_date=start_date or datetime.utcnow(),
            deadline=deadline
        )
        db.session.add(project)
        db.session.commit()
        return project
        
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')
    members = db.relationship('User', secondary=project_members, 
                             back_populates='projects', lazy='dynamic')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    @property
    def progress_percentage(self):
        """Calculate project completion percentage"""
        if not self.tasks:
            return 0
        completed_tasks = sum(1 for task in self.tasks if task.status == TaskStatus.COMPLETED)
        return round((completed_tasks / len(self.tasks)) * 100, 1)
    
    @property
    def task_counts(self):
        """Get count of tasks by status"""
        counts = {'todo': 0, 'in_progress': 0, 'completed': 0}
        for task in self.tasks:
            counts[task.status.value] += 1
        return counts
    
    @property
    def days_left(self):
        """Calculate days left until deadline"""
        if not self.deadline:
            return None
        today = datetime.utcnow().date()
        deadline_date = self.deadline.date() if hasattr(self.deadline, 'date') else self.deadline
        return (deadline_date - today).days
    
    @property
    def duration_days(self):
        """Calculate total project duration in days"""
        if not self.start_date or not self.deadline:
            return None
        start = self.start_date.date() if hasattr(self.start_date, 'date') else self.start_date
        end = self.deadline.date() if hasattr(self.deadline, 'date') else self.deadline
        return (end - start).days
    
    @property
    def days_elapsed(self):
        """Calculate days elapsed since project start"""
        if not self.start_date:
            return None
        today = datetime.utcnow().date()
        start = self.start_date.date() if hasattr(self.start_date, 'date') else self.start_date
        elapsed = (today - start).days
        return max(0, elapsed)  # Don't return negative values for future start dates
    
    @property
    def is_started(self):
        """Check if project has started"""
        if not self.start_date:
            return True  # If no start date, assume started
        today = datetime.utcnow().date()
        start = self.start_date.date() if hasattr(self.start_date, 'date') else self.start_date
        return today >= start

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    # Updated foreign key with CASCADE DELETE for assignee
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.TODO)
    priority = db.Column(db.String(10), default='medium')  # low, medium, high
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    comments = db.relationship('Comment', backref='task', lazy=True, cascade='all, delete-orphan')
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if not self.due_date or self.status == TaskStatus.COMPLETED:
            return False
        return self.due_date.date() < datetime.utcnow().date()

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sentiment = db.Column(db.Enum(CommentSentiment), default=CommentSentiment.NEUTRAL)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)    
    
    def __repr__(self):
        return f'<Comment {self.id}>'