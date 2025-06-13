from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SubmitField, SelectField, DateTimeField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateTimeField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class TaskForm(FlaskForm):
    title = StringField('Titre de la tâche', 
                       validators=[DataRequired(), Length(min=1, max=200)])
    
    description = TextAreaField('Description', 
                               validators=[Optional(), Length(max=1000)])
    
    priority = SelectField('Priorité', 
                          choices=[
                              ('low', 'Basse'),
                              ('medium', 'Moyenne'), 
                              ('high', 'Haute'),
                              ('urgent', 'Urgente')
                          ],
                          default='medium')
    
    assignee_id = SelectField('Assigné à', 
                             coerce=int,
                             validators=[Optional()])
    
    due_date = DateTimeField('Date d\'échéance', 
                            validators=[Optional()],
                            format='%Y-%m-%d %H:%M')
    
    submit = SubmitField('Enregistrer')

class ProjectForm(FlaskForm):
    name = StringField('Nom du projet', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description du projet')
    deadline = DateField('Date limite (YYYY-MM-DD)', format='%Y-%m-%d')
    submit = SubmitField('Créer le projet')

class CommentForm(FlaskForm):
    content = TextAreaField('Contenu du commentaire', validators=[DataRequired()])
    submit = SubmitField('Ajouter le commentaire')

class EditTaskForm(FlaskForm):
    title = StringField('Titre de la tâche', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description de la tâche')
    due_date = DateField('Date limite (YYYY-MM-DD)', format='%Y-%m-%d')
    submit = SubmitField('Modifier la tâche')

class EditProjectForm(FlaskForm):
    name = StringField('Nom du projet', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description du projet')
    deadline = DateField('Date limite (YYYY-MM-DD)', format='%Y-%m-%d')
    submit = SubmitField('Modifier le projet')

class EditCommentForm(FlaskForm):
    content = TextAreaField('Contenu du commentaire', validators=[DataRequired()])
    submit = SubmitField('Modifier le commentaire')

class DeleteCommentForm(FlaskForm):
    submit = SubmitField('Supprimer le commentaire')

class DeleteTaskForm(FlaskForm):
    submit = SubmitField('Supprimer la tâche')

class DeleteProjectForm(FlaskForm):
    submit = SubmitField('Supprimer le projet')

# FIXED: Use IntegerField instead of StringField for user IDs
class AssignTaskForm(FlaskForm):
    user_id = IntegerField('ID de l\'utilisateur', 
                          validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Assigner la tâche')

class AssignProjectForm(FlaskForm):
    user_id = IntegerField('ID de l\'utilisateur', 
                          validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Assigner le projet')

class RemoveMemberForm(FlaskForm):
    user_id = IntegerField('ID de l\'utilisateur', 
                          validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Supprimer le membre')

class AddMemberForm(FlaskForm):
    user_id = IntegerField('ID de l\'utilisateur', 
                          validators=[DataRequired(), NumberRange(min=1)])
    role = StringField('Role', validators=[DataRequired()])
    submit = SubmitField('Ajouter le membre')

class EditMemberForm(FlaskForm):
    role = StringField('Role', validators=[DataRequired()])
    submit = SubmitField('Modifier le membre')

class DeleteMemberForm(FlaskForm):
    submit = SubmitField('Supprimer le membre')

class AddTaskForm(FlaskForm):
    title = StringField('Titre de la tâche', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description de la tâche')
    due_date = DateField('Date limite (YYYY-MM-DD)', format='%Y-%m-%d')
    submit = SubmitField('Ajouter la tâche')

class AddProjectForm(FlaskForm):
    name = StringField('Nom du projet', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description du projet')
    deadline = DateField('Date limite (YYYY-MM-DD)', format='%Y-%m-%d')
    submit = SubmitField('Créer le projet')

class AddCommentForm(FlaskForm):
    content = TextAreaField('Contenu du commentaire', validators=[DataRequired()])
    submit = SubmitField('Ajouter le commentaire')