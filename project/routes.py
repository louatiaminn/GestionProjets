from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from models import Project, Task, User, TaskStatus, UserRole, Comment, db
from sqlalchemy import desc, func
from .forms import AddTaskForm, DeleteTaskForm, EditTaskForm, EditProjectForm

from . import project

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            flash('Accès réservé aux administrateurs.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def project_owner_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        project_id = kwargs.get('project_id')
        if project_id:
            proj = Project.query.get_or_404(project_id)
            if not (current_user.role == UserRole.ADMIN or 
                   proj.owner_id == current_user.id):
                flash('Vous n\'avez pas les permissions pour cette action.', 'error')
                return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def calculate_days_left(deadline):
    """Calculate days left until deadline"""
    if not deadline:
        return None
    today = datetime.utcnow().date()
    deadline_date = deadline.date() if hasattr(deadline, 'date') else deadline
    return (deadline_date - today).days
@project.route('/')
@login_required
def project_list():
    """List projects based on user role"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    if current_user.role == UserRole.ADMIN:
        projects = Project.query.order_by(desc(Project.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
    else:
        owned_projects = Project.query.filter_by(owner_id=current_user.id)
        member_projects = current_user.projects
        all_project_ids = set([p.id for p in owned_projects] + [p.id for p in member_projects])
        projects = Project.query.filter(Project.id.in_(all_project_ids)).order_by(
            desc(Project.created_at)
        ).paginate(page=page, per_page=per_page, error_out=False)    
    return render_template('project/list.html', projects=projects)

@project.route('/create', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create new project - All authenticated users can create"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        
        if not name:
            flash('Le nom du projet est requis.', 'error')
            return render_template('project/create.html')
        
        # Parse deadline if provided
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError:
                flash('Format de date invalide.', 'error')
                return render_template('project/create.html')
        
        new_project = Project(
            name=name,
            description=description,
            owner_id=current_user.id,
            deadline=deadline
        )
        
        db.session.add(new_project)
        db.session.commit()
        
        new_project.members.append(current_user)
        db.session.commit()
        
        flash(f'Projet "{name}" créé avec succès!', 'success')
        return redirect(url_for('project.project_detail', project_id=new_project.id))
    return render_template('project/create.html')
@project.route('/<int:project_id>/add_comment', methods=['POST'])
@login_required
def add_task_comment_general(project_id):
    """Add a comment to a task from project detail page"""
    proj = Project.query.get_or_404(project_id)
    
    # Check if user has access to this project
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))
    
    task_id = request.form.get('task_id')
    content = request.form.get('content')
    
    if not task_id:
        flash('Veuillez sélectionner une tâche.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    if not content or not content.strip():
        flash('Le contenu du commentaire ne peut pas être vide.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    task = Task.query.filter_by(id=task_id, project_id=project_id).first()
    if not task:
        flash('Tâche non trouvée dans ce projet.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    comment = Comment(
        content=content.strip(),
        author_id=current_user.id,
        task_id=task_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    flash('Commentaire ajouté avec succès!', 'success')
    return redirect(url_for('project.project_detail', project_id=project_id))

@project.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@project_owner_or_admin_required
def edit_project(project_id):
    """Edit project - Only owner or admin"""
    proj = Project.query.get_or_404(project_id)
    from .forms import EditProjectForm
    form = EditProjectForm()

    if form.validate_on_submit():
        proj.name        = form.name.data
        proj.description = form.description.data
        proj.deadline    = form.deadline.data
        proj.updated_at  = datetime.utcnow()
        db.session.commit()
        flash('Projet mis à jour avec succès!', 'success')
        return redirect(url_for('project.project_detail', project_id=proj.id))

    if request.method == 'GET':
        form.name.data        = proj.name
        form.description.data = proj.description
        form.deadline.data    = proj.deadline.date() if proj.deadline else None

    template = 'admin/edit.html' if current_user.role == UserRole.ADMIN else 'project/edit.html'
    return render_template(template, project=proj, form=form)
@project.route('/<int:project_id>/tasks')
@login_required
def task_details(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Permission check
    if (current_user.role != UserRole.ADMIN and 
        project.owner_id != current_user.id and 
        current_user not in project.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))    
    
    tasks = Task.query.filter_by(project_id=project_id).order_by(Task.updated_at.desc()).all()
    
    task_stats = {
        'todo': sum(1 for task in tasks if task.status.value == 'todo'),
        'in_progress': sum(1 for task in tasks if task.status.value == 'in_progress'),
        'completed': sum(1 for task in tasks if task.status.value == 'completed'),
    }
    
    today = datetime.utcnow().date()
    
    template = 'admin/task_details.html' if current_user.role == UserRole.ADMIN else 'project/task_details.html'
    return render_template(template, 
                         project=project, 
                         tasks=tasks, 
                         task_stats=task_stats,
                         today=today)
@project.route('/<int:project_id>/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(project_id, task_id):
    proj = Project.query.get_or_404(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()

    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))
    
    form = EditTaskForm()
    
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        task.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Tâche modifiée avec succès!', 'success')
        return redirect(url_for('project.project_detail', project_id=project_id))
    if request.method == 'GET':
        form.title.data = task.title
        form.description.data = task.description
        form.due_date.data = task.due_date.date() if task.due_date else None
    if current_user.role == UserRole.ADMIN:
        template = 'admin/edit_task.html'
    else:
        template = 'project/edit_task.html'
    return render_template(template, project=proj, task=task, form=form)
@project.route('/<int:project_id>/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(project_id, task_id):
    proj = Project.query.get_or_404(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()    
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))    
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        task.assignee_id != current_user.id):
        flash('Vous ne pouvez supprimer que vos propres tâches.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    task_title = task.title    
    Comment.query.filter_by(task_id=task_id).delete()
    db.session.delete(task)
    db.session.commit()
    flash(f'Tâche "{task_title}" supprimée avec succès!', 'success')
    return redirect(url_for('project.project_detail', project_id=project_id))

@project.route('/<int:project_id>/bulk_delete_tasks', methods=['POST'])
@login_required
def bulk_delete_tasks(project_id):
    """Bulk delete multiple tasks"""
    proj = Project.query.get_or_404(project_id)
    
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))
    task_ids = request.form.getlist('task_ids')
    if not task_ids:
        flash('Veuillez sélectionner des tâches à supprimer.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    try:
        tasks = Task.query.filter(
            Task.id.in_(task_ids), 
            Task.project_id == project_id
        ).all()
        
        deleted_count = 0
        for task in tasks:
            if (current_user.role == UserRole.ADMIN or 
                proj.owner_id == current_user.id or 
                task.assignee_id == current_user.id):
                
                Comment.query.filter_by(task_id=task.id).delete()
                db.session.delete(task)
                deleted_count += 1
        
        db.session.commit()
        
        if deleted_count > 0:
            flash(f'{deleted_count} tâche(s) supprimée(s) avec succès!', 'success')
        else:
            flash('Aucune tâche n\'a pu être supprimée.', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la suppression des tâches.', 'error')
    
    return redirect(url_for('project.project_detail', project_id=project_id))

@project.route('/<int:project_id>/tasks/<int:task_id>/update_status', methods=['POST'])
@login_required
def update_task_status(project_id, task_id):
    task   = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    project = task.project
    new_status = request.form.get('status')
    if new_status not in ['todo','in_progress','completed']:
        return jsonify(success=False, message='Statut invalide'), 400
    old_status = task.status.value if task.status else None
    task.status     = TaskStatus(new_status)
    task.updated_at = datetime.utcnow()
    if new_status == 'completed':
        task.completed_at = datetime.utcnow()
    else:
        task.completed_at = None
    db.session.commit()
    db.session.refresh(project)
    counts = {
      'todo':       sum(1 for t in project.tasks if t.status.value == 'todo'),
      'in_progress': sum(1 for t in project.tasks if t.status.value == 'in_progress'),
      'completed':   sum(1 for t in project.tasks if t.status.value == 'completed'),
    }
    pct = (counts['completed'] / len(project.tasks) * 100) if project.tasks else 0
    return jsonify({
      'success': True,
      'message': f'Tâche mise à jour vers "{ {"todo":"À faire","in_progress":"En cours","completed":"Terminée"}[new_status]}"',
      'old_status': old_status,
      'new_status': new_status,
      'task_stats': counts,
      'progress_percentage': round(pct,1),
      'updated_at': task.updated_at.isoformat()
    })
@project.route('/<int:project_id>/bulk_update_tasks', methods=['POST'])
@login_required
def bulk_update_task_status(project_id):
    """Bulk update multiple task statuses"""
    try:
        proj = Project.query.get_or_404(project_id)        
        if (current_user.role != UserRole.ADMIN and 
            proj.owner_id != current_user.id and 
            current_user not in proj.members.all()):
            flash('Vous n\'avez pas accès à ce projet.', 'error')
            return redirect(url_for('project.project_detail', project_id=project_id))     
        task_ids = request.form.getlist('task_ids')
        new_status = request.form.get('bulk_status')
        if not task_ids or not new_status:
            flash('Veuillez sélectionner des tâches et un statut.', 'error')
            return redirect(url_for('project.project_detail', project_id=project_id))        
        try:
            status_enum = TaskStatus(new_status)
        except ValueError:
            flash('Statut invalide.', 'error')
            return redirect(url_for('project.project_detail', project_id=project_id))        
        tasks = Task.query.filter(Task.id.in_(task_ids), Task.project_id == project_id).all()
        updated_count = 0
        for task in tasks:
            task.status = status_enum
            task.updated_at = datetime.utcnow()
            if status_enum == TaskStatus.COMPLETED:
                task.completed_at = datetime.utcnow()
            elif task.completed_at and status_enum != TaskStatus.COMPLETED:
                task.completed_at = None
            updated_count += 1
        db.session.commit()        
        status_translations = {
            'todo': 'À faire',
            'in_progress': 'En cours', 
            'completed': 'Terminées'
        }
        
        flash(f'{updated_count} tâche(s) mise(s) à jour vers "{status_translations[new_status]}".', 'success')
        return redirect(url_for('project.project_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la mise à jour groupée.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
   
   
@project.route('/<int:project_id>/delete', methods=['POST'])
@login_required
@project_owner_or_admin_required
def delete_project(project_id):
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
        return redirect(url_for('admin.project_list'))
    else:
        return redirect(url_for('project.project_list'))
@project.route('/<int:project_id>/add_task', methods=['GET', 'POST'])
@login_required
def add_task(project_id):
    """Ajouter une tâche à un projet"""
    proj = Project.query.get_or_404(project_id)
    if (current_user.role != UserRole.ADMIN and
        proj.owner_id != current_user.id and
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas les droits pour ajouter une tâche à ce projet.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    form = AddTaskForm()
    if form.validate_on_submit():
        title       = form.title.data
        description = form.description.data
        due_date    = form.due_date.data
        task = Task(
            title=title,
            description=description,
            due_date=due_date,
            project=proj
        )
        db.session.add(task)
        db.session.commit()
        flash('Tâche ajoutée avec succès.', 'success')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    if current_user.role == UserRole.ADMIN:
        return render_template(
            'admin/add_task.html',
            project=proj,
            form=form
        )
    else:
        return render_template(
            'project/add_task.html',
            project=proj,
            form=form
        )
@project.route('/<int:project_id>/members')
@login_required
def project_members(project_id):
    """View project members"""
    proj = Project.query.get_or_404(project_id)
    
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))
    members = proj.members.all()
    available_users = User.query.filter(
        ~User.id.in_([m.id for m in members])
    ).filter(User.is_active == True).all()
    return render_template('project/members.html', 
                         project=proj, 
                         members=members,
                         available_users=available_users)
@project.route('/<int:project_id>/add_member', methods=['POST'])
@login_required
@project_owner_or_admin_required
def add_member(project_id):
    """Add member to project - Only owner or admin"""
    proj = Project.query.get_or_404(project_id)
    user_id = request.form.get('user_id')
    if not user_id:
        flash('Utilisateur non sélectionné.', 'error')
        return redirect(url_for('project.project_members', project_id=project_id))
    user = User.query.get_or_404(user_id)
    if user in proj.members.all():
        flash(f'{user.full_name} est déjà membre de ce projet.', 'warning')
        return redirect(url_for('project.project_members', project_id=project_id))
    proj.members.append(user)
    db.session.commit()
    flash(f'{user.full_name} ajouté au projet avec succès!', 'success')
    return redirect(url_for('project.project_members', project_id=project_id))
@project.route('/<int:project_id>/remove_member/<int:user_id>', methods=['POST'])
@login_required
@project_owner_or_admin_required
def remove_member(project_id, user_id):
    """Remove member from project - Only owner or admin"""
    proj = Project.query.get_or_404(project_id)
    user = User.query.get_or_404(user_id)
    if user.id == proj.owner_id:
        flash('Impossible de retirer le propriétaire du projet.', 'error')
        return redirect(url_for('project.project_members', project_id=project_id))
    if user in proj.members.all():
        assigned_tasks = Task.query.filter_by(project_id=project_id, assignee_id=user_id)\
                                 .filter(Task.status != TaskStatus.COMPLETED).count()
        if assigned_tasks > 0:
            flash(f'Impossible de retirer {user.full_name}. Il/Elle a {assigned_tasks} tâches actives.', 'error')
            return redirect(url_for('project.project_members', project_id=project_id))
        proj.members.remove(user)
        db.session.commit()
        flash(f'{user.full_name} retiré du projet.', 'success')
    else:
        flash('Utilisateur non trouvé dans ce projet.', 'error')
    return redirect(url_for('project.project_members', project_id=project_id))
@project.route('/<int:project_id>/stats')
@login_required
def project_stats_api(project_id):
    proj = Project.query.get_or_404(project_id)
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        return jsonify({'error': 'Access denied'}), 403
    task_stats = proj.task_counts
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    daily_completions = db.session.query(
        func.date(Task.completed_at),
        func.count(Task.id)
    ).filter(
        Task.project_id == project_id,
        Task.completed_at.between(start_date, end_date)
    ).group_by(func.date(Task.completed_at)).all()
    return jsonify({
        'task_stats': task_stats,
        'progress_percentage': proj.progress_percentage,
        'total_members': proj.members.count(),
        'daily_completions': [
            {'date': str(date), 'count': count} 
            for date, count in daily_completions
        ]
    })
@project.route('/<int:project_id>/tasks/<int:task_id>/comments/add', methods=['POST'])
@login_required
def add_task_comment(project_id, task_id):
    proj = Project.query.get_or_404(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))
    
    content = request.form.get('content')
    if not content or not content.strip():
        flash('Le contenu du commentaire ne peut pas être vide.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    comment = Comment(
        content=content.strip(),
        author_id=current_user.id,
        task_id=task_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    flash('Commentaire ajouté avec succès!', 'success')
    return redirect(url_for('project.project_detail', project_id=project_id))

@project.route('/<int:project_id>/tasks/<int:task_id>/comments/<int:comment_id>/edit', methods=['POST'])
@login_required
def edit_task_comment(project_id, task_id, comment_id):
    """Edit a task comment"""
    proj = Project.query.get_or_404(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    comment = Comment.query.filter_by(id=comment_id, task_id=task_id).first_or_404()
    
    # Check if user has access to this project
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))
    
    # Check if user can edit this comment (author or admin)
    if comment.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        flash('Vous ne pouvez modifier que vos propres commentaires.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    content = request.form.get('content')
    if not content or not content.strip():
        flash('Le contenu du commentaire ne peut pas être vide.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    comment.content = content.strip()
    comment.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash('Commentaire modifié avec succès!', 'success')
    return redirect(url_for('project.project_detail', project_id=project_id))

@project.route('/<int:project_id>/tasks/<int:task_id>/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_task_comment(project_id, task_id, comment_id):
    """Delete a task comment"""
    proj = Project.query.get_or_404(project_id)
    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()
    comment = Comment.query.filter_by(id=comment_id, task_id=task_id).first_or_404()
    
    # Check if user has access to this project
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))
    
    if comment.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        flash('Vous ne pouvez supprimer que vos propres commentaires.', 'error')
        return redirect(url_for('project.project_detail', project_id=project_id))
    
    db.session.delete(comment)
    db.session.commit()
    
    flash('Commentaire supprimé avec succès!', 'success')
    return redirect(url_for('project.project_detail', project_id=project_id))

@project.route('/<int:project_id>')
@login_required
def project_detail(project_id):
    """Display project details with tasks and comments"""
    proj = Project.query.get_or_404(project_id)
    if (current_user.role != UserRole.ADMIN and 
        proj.owner_id != current_user.id and 
        current_user not in proj.members.all()):
        flash('Vous n\'avez pas accès à ce projet.', 'error')
        return redirect(url_for('project.project_list'))
    tasks = Task.query.filter_by(project_id=project_id).order_by(desc(Task.created_at)).all()    
    recent_tasks = Task.query.filter_by(project_id=project_id).limit(10).all()    
    comments = Comment.query.join(Task).filter(
        Task.project_id == project_id
    ).order_by(desc(Comment.created_at)).all()

    task_stats = proj.task_counts    
    template = 'admin/details.html' if current_user.role == UserRole.ADMIN else 'project/details.html'
    
    return render_template(template, 
                         project=proj, 
                         tasks=tasks, 
                         recent_tasks=recent_tasks,
                         comments=comments,
                         task_stats=task_stats,
                         current_date=datetime.now().date(),  
                         now=datetime.now) 
    
@project.route('/bulk_actions', methods=['POST'])
@login_required
@admin_required
def bulk_project_actions():
    """Bulk operations on projects - Admin only"""
    action = request.form.get('action')
    project_ids = request.form.getlist('project_ids')
    
    if not project_ids:
        flash('Aucun projet sélectionné.', 'error')
        return redirect(url_for('project.project_list'))
    
    projects = Project.query.filter(Project.id.in_(project_ids)).all()
    
    if action == 'activate':
        for proj in projects:
            proj.is_active = True
        db.session.commit()
        flash(f'{len(projects)} projet(s) activé(s).', 'success')
        
    elif action == 'deactivate':
        for proj in projects:
            proj.is_active = False
        db.session.commit()
        flash(f'{len(projects)} projet(s) désactivé(s).', 'success')
        
    elif action == 'delete':
        for proj in projects:
            db.session.delete(proj)
        db.session.commit()
        flash(f'{len(projects)} projet(s) supprimé(s).', 'success')
    
    return redirect(url_for('admin.manage_projects'))