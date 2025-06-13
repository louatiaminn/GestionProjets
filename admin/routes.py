from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Project, Task, Comment, UserRole, TaskStatus
from datetime import datetime, timedelta
from sqlalchemy import func
from dateutil.relativedelta import relativedelta  # precise date handling
from admin import admin  # imported after __init__.py setup

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash('Accès refusé. Privilèges administrateur requis.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(role=UserRole.ADMIN).count()

    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(is_active=True).count()

    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status=TaskStatus.COMPLETED).count()
    pending_tasks = Task.query.filter(Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])).count()

    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
    recent_tasks = Task.query.order_by(Task.updated_at.desc()).limit(10).all()

    monthly_stats = []
    today = datetime.utcnow().replace(day=1)
    for i in range(12):
        month_start = today - relativedelta(months=i)
        next_month = month_start + relativedelta(months=1)
        users_count = User.query.filter(User.created_at >= month_start, User.created_at < next_month).count()
        projects_count = Project.query.filter(Project.created_at >= month_start, Project.created_at < next_month).count()
        monthly_stats.append({
            'month': month_start.strftime('%b %Y'),
            'users': users_count,
            'projects': projects_count
        })
    monthly_stats.reverse()

    top_users = db.session.query(
    User.id,
    User.username,
    (User.first_name + ' ' + User.last_name).label('full_name'),
    func.count(Project.id).label('project_count')
).outerjoin(Project, User.id == Project.owner_id)\
 .group_by(User.id, User.username, User.first_name, User.last_name)\
 .order_by(func.count(Project.id).desc())\
 .limit(5).all()



    return render_template('admin/admin_dashboard.html',
                           total_users=total_users,
                           active_users=active_users,
                           admin_users=admin_users,
                           total_projects=total_projects,
                           active_projects=active_projects,
                           total_tasks=total_tasks,
                           completed_tasks=completed_tasks,
                           pending_tasks=pending_tasks,
                           recent_users=recent_users,
                           recent_projects=recent_projects,
                           recent_tasks=recent_tasks,
                           monthly_stats=monthly_stats,
                           top_users=top_users)

@admin.route('/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)

    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=users, search=search)

@admin.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activé' if user.is_active else 'désactivé'
    flash(f'Utilisateur {user.username} {status} avec succès.', 'success')
    return jsonify({'success': True, 'is_active': user.is_active})

@admin.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot modify your own admin status'}), 400
    user.role = UserRole.MEMBER if user.role == UserRole.ADMIN else UserRole.ADMIN
    db.session.commit()
    role_name = 'administrateur' if user.role == UserRole.ADMIN else 'membre'
    flash(f'Utilisateur {user.username} défini comme {role_name}.', 'success')
    return jsonify({'success': True, 'is_admin': user.role == UserRole.ADMIN})

@admin.route('/projects')
@login_required
@admin_required
def manage_projects():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)

    query = Project.query
    if search:
        query = query.filter(
            db.or_(
                Project.name.contains(search),
                Project.description.contains(search)
            )
        )
    projects = query.order_by(Project.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/projects.html', projects=projects, search=search)

@admin.route('/projects/<int:project_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_project_status(project_id):
    project = Project.query.get_or_404(project_id)
    project.is_active = not project.is_active
    db.session.commit()
    status = 'activé' if project.is_active else 'désactivé'
    flash(f'Projet {project.name} {status} avec succès.', 'success')
    return jsonify({'success': True, 'is_active': project.is_active})

@admin.route('/<int:project_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_project(project_id):
    """Delete project - Owner or Admin; redirect based on role"""
    proj = Project.query.get_or_404(project_id)
    project_name = proj.name

    active_tasks = Task.query.filter_by(project_id=project_id) \
                             .filter(Task.status != TaskStatus.COMPLETED) \
                             .count()

    if active_tasks > 0 and current_user.role != UserRole.ADMIN:
        flash(f'Impossible de supprimer le projet. Il contient {active_tasks} tâches actives.', 'error')
        return redirect(url_for('project.project_list'))

    db.session.delete(proj)
    db.session.commit()
    flash(f'Projet "{project_name}" supprimé avec succès.', 'success')

    if current_user.role == UserRole.ADMIN:
        # Redirect to your admin projects list
        return redirect(url_for('admin.manage_projects'))
    else:
        # Redirect to the normal user project list
        return redirect(url_for('project.project_list'))


@admin.route('/users/<int:user_id>/delete', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Vous ne pouvez pas supprimer votre propre compte.'}), 400

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin.route('/system-stats')
@login_required
@admin_required
def system_stats():
    db_stats = {
        'users': User.query.count(),
        'projects': Project.query.count(),
        'tasks': Task.query.count(),
        'comments': Comment.query.count()
    }

    task_stats = {
        'todo': Task.query.filter_by(status=TaskStatus.TODO).count(),
        'in_progress': Task.query.filter_by(status=TaskStatus.IN_PROGRESS).count(),
        'completed': Task.query.filter_by(status=TaskStatus.COMPLETED).count()
    }

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = User.query.join(Task).filter(Task.updated_at >= thirty_days_ago).distinct().count()

    return jsonify({
        'database': db_stats,
        'tasks': task_stats,
        'active_users_30d': active_users
    })
