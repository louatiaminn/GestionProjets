from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from werkzeug.security import generate_password_hash
from models import db, User, Project, Task, Comment, UserRole, TaskStatus
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from dateutil.relativedelta import relativedelta  
from admin import admin
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()


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

@admin.route('/users', methods=['GET'])
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    
    query = User.query

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )    
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/users.html', users=users, search=search)

@admin.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            password = request.form.get('password', '').strip()
            role = request.form.get('role', 'member')
            is_active = request.form.get('is_active') == 'on'
            if not all([username, email, first_name, last_name, password]):
                flash('Tous les champs sont obligatoires.', 'error')
                return render_template('admin/create_user.html', 
                                     username=username, email=email, 
                                     first_name=first_name, last_name=last_name,
                                     role=role, is_active=is_active)
            if User.query.filter_by(username=username).first():
                flash('Ce nom d\'utilisateur existe déjà.', 'error')
                return render_template('admin/create_user.html', 
                                     username='', email=email, 
                                     first_name=first_name, last_name=last_name,
                                     role=role, is_active=is_active)
            if User.query.filter_by(email=email).first():
                flash('Cette adresse email existe déjà.', 'error')
                return render_template('admin/create_user.html', 
                                     username=username, email='', 
                                     first_name=first_name, last_name=last_name,
                                     role=role, is_active=is_active)
            try:
                user_role = UserRole(role)
            except ValueError:
                flash('Rôle invalide sélectionné.', 'error')
                return render_template('admin/create_user.html', 
                                     username=username, email=email, 
                                     first_name=first_name, last_name=last_name,
                                     role='member', is_active=is_active)
            new_user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash=generate_password_hash(password),
                role=user_role,
                is_active=is_active
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'Utilisateur {username} créé avec succès.', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création de l\'utilisateur: {str(e)}', 'error')
            return render_template('admin/create_user.html')
    return render_template('admin/create_user.html')

@admin.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Utilisateur non trouvé.'}), 404
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Vous ne pouvez pas modifier votre propre statut via cette action.'}), 400
    try:
        user.is_active = not user.is_active
        db.session.commit()
        action = "activé" if user.is_active else "désactivé"
        flash(f'L\'utilisateur {user.username} a été {action} avec succès.', 'success')
        return jsonify({'success': True, 'is_active': user.is_active})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin_role(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Utilisateur non trouvé.'}), 404    
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Vous ne pouvez pas modifier votre propre rôle via cette action.'}), 400

    try:
        if user.role == UserRole.ADMIN:
            user.role = UserRole.MEMBER 
            action = "retiré des administrateurs"
            is_admin = False
        else:
            user.role = UserRole.ADMIN
            action = "désigné comme administrateur"
            is_admin = True
        db.session.commit()
        flash(f'Le rôle de {user.username} a été {action} avec succès.', 'success')
        return jsonify({'success': True, 'is_admin': is_admin, 'new_role': user.role.value})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
@admin.route('/users/<int:user_id>/delete', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Utilisateur {user.username} supprimé.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Erreur: {str(e)}'}), 500
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
        return redirect(url_for('admin.manage_projects'))
    else:
        return redirect(url_for('project.project_list'))

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