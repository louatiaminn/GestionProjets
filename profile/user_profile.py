from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db
from datetime import datetime
from models.models import User

profile = Blueprint('profile', __name__)

@profile.route('/profile')
@login_required
def view_profile():
    owned_projects_count = len(current_user.owned_projects)
    member_projects_count = len(current_user.projects.all())
    assigned_tasks_count = len(current_user.assigned_tasks)
    
    days_since_joined = (datetime.utcnow() - current_user.created_at).days
    
    recent_activities = []
    
    return render_template('profile.html',
                         owned_projects_count=owned_projects_count,
                         member_projects_count=member_projects_count,
                         assigned_tasks_count=assigned_tasks_count,
                         days_since_joined=days_since_joined,
                         recent_activities=recent_activities)

@profile.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    username = request.form.get('username')
    email = request.form.get('email')
    
    # Basic validation
    if not all([first_name, last_name, username, email]):
        flash('Tous les champs sont requis.', 'error')
        return redirect(url_for('profile.view_profile'))
    
    # Check if username or email already exists (excluding current user)
    existing_user = db.session.query(User).filter(
        (User.username == username) | (User.email == email),
        User.id != current_user.id
    ).first()
    
    if existing_user:
        if existing_user.username == username:
            flash('Ce nom d\'utilisateur est déjà utilisé.', 'error')
        else:
            flash('Cette adresse email est déjà utilisée.', 'error')
        return redirect(url_for('profile.view_profile'))
    
    # Update user information
    current_user.first_name = first_name
    current_user.last_name = last_name
    current_user.username = username
    current_user.email = email
    
    try:
        db.session.commit()
        flash('Profil mis à jour avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la mise à jour du profil.', 'error')
    
    return redirect(url_for('profile.view_profile'))

@profile.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Basic validation
    if not all([current_password, new_password, confirm_password]):
        flash('Tous les champs sont requis.', 'error')
        return redirect(url_for('profile.view_profile'))
    
    # Check current password
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Mot de passe actuel incorrect.', 'error')
        return redirect(url_for('profile.view_profile'))
    
    # Check if new passwords match
    if new_password != confirm_password:
        flash('Les nouveaux mots de passe ne correspondent pas.', 'error')
        return redirect(url_for('profile.view_profile'))
    
    # Check password length
    if len(new_password) < 8:
        flash('Le mot de passe doit contenir au moins 8 caractères.', 'error')
        return redirect(url_for('profile.view_profile'))
    
    # Update password
    current_user.password_hash = generate_password_hash(new_password)
    
    try:
        db.session.commit()
        flash('Mot de passe changé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors du changement de mot de passe.', 'error')
    
    return redirect(url_for('profile.view_profile'))