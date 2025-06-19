from secrets import token_urlsafe
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from config import config
from models import db, User, TaskStatus
from datetime import datetime, timedelta

login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @app.context_processor
    def inject_datetime():
        return {
            'datetime': datetime,
            'now': datetime.utcnow()
        }
    
    @app.template_filter('is_overdue')
    def is_overdue(due_date, task_status=None):
        if not due_date:
            return False
        if task_status and task_status == 'completed':
            return False
        return due_date.date() < datetime.utcnow().date()
    
    # Fixed import - now imports from the profile directory
    from profile.user_profile import profile as profile_blueprint
    app.register_blueprint(profile_blueprint)

    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from project import project
    app.register_blueprint(project, url_prefix='/projects')
    
    from admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        owned_projects = current_user.owned_projects
        member_projects = current_user.projects.all() 
        all_user_projects = list(owned_projects) + [p for p in member_projects if p not in owned_projects]
        user_tasks = current_user.assigned_tasks
        todo_tasks = [task for task in user_tasks if task.status == TaskStatus.TODO]
        in_progress_tasks = [task for task in user_tasks if task.status == TaskStatus.IN_PROGRESS]
        completed_tasks = [task for task in user_tasks if task.status == TaskStatus.COMPLETED]
        total_todo = 0
        total_in_progress = 0
        total_completed = 0
        for project in all_user_projects:
            if hasattr(project, 'task_counts'):
                project_stats = project.task_counts
                total_todo += project_stats.get('todo', 0)
                total_in_progress += project_stats.get('in_progress', 0)
                total_completed += project_stats.get('completed', 0)
        task_stats = {
            'todo': total_todo,
            'in_progress': total_in_progress,
            'completed': total_completed
        }
        if task_stats['todo'] == 0 and task_stats['in_progress'] == 0 and task_stats['completed'] == 0:
            task_stats = {
                'todo': len(todo_tasks),
                'in_progress': len(in_progress_tasks),
                'completed': len(completed_tasks)
            }
        total_tasks = len(user_tasks)
        completion_rate = (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0
        upcoming_deadline = datetime.utcnow() + timedelta(days=7)
        upcoming_tasks = [task for task in user_tasks 
                        if task.due_date and task.due_date <= upcoming_deadline 
                        and task.status != TaskStatus.COMPLETED]
        project_stats = []
        for project in all_user_projects:
            project_stats.append({
                'name': project.name,
                'progress': project.progress_percentage,
                'total_tasks': len(project.tasks),
                'completed_tasks': len([t for t in project.tasks if t.status == TaskStatus.COMPLETED])
            })
        recent_tasks = sorted(user_tasks, key=lambda x: x.updated_at, reverse=True)[:10]
        return render_template('dashboard.html',
                            owned_projects=owned_projects,
                            member_projects=member_projects,
                            all_projects=all_user_projects,
                            todo_tasks=todo_tasks,
                            in_progress_tasks=in_progress_tasks,
                            completed_tasks=completed_tasks,
                            upcoming_tasks=upcoming_tasks,
                            task_stats=task_stats,
                            completion_rate=completion_rate,
                            project_stats=project_stats,
                            recent_tasks=recent_tasks)
    return app

if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        db.create_all()
    app.run(debug=True)