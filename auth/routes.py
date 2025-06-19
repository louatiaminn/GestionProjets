from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from . import auth
from .forms import LoginForm
from models import db, User, UserRole

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == UserRole.ADMIN:
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash(f'Bienvenue, {user.first_name}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.role == UserRole.ADMIN:
                return redirect(url_for('admin.admin_dashboard'))
            return redirect(url_for('dashboard'))
        
        flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')
    
    return render_template('auth/login.html', form=form)



@auth.route('/logout')
def logout():
    logout_user()
    flash('Déconnexion réussie.', 'success')
    return redirect(url_for('auth.login'))

