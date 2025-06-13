# Application de Gestion Collaborative de Projets
Cette application web permet à des équipes de planifier, suivre et piloter leurs projets en temps réel.  
Développée en Python avec Flask, elle offre :
- Gestion des utilisateurs et des permissions (Administrateur, Membre),
- Création, modification et suppression de projets et tâches,
- Système de commentaires et opérations en lot,
- Tableau de bord dynamique avec statistiques et graphiques (Chart.js).

## Installation rapide
1. Cloner le dépôt:
   git clone https://github.com/louatiaminn/GestionProjets.git 

2. Créer et activer un environnement virtuel:
python3 -m venv venv && source venv/bin/activate

3. Installer les dépendances: 
pip install -r requirements.txt

4. Lancer l’application:
   python app.py or flask run
