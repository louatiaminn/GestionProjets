from app import create_app
from models import db, User, Project, Task, UserRole, TaskStatus  
from werkzeug.security import generate_password_hash

app = create_app('development')

with app.app_context():
    db.create_all()
    
    test_user = User(
        username='admin',
        email='admin@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='Admin',
        last_name='User',
        role=UserRole.ADMIN
    )
    
    db.session.add(test_user)
    db.session.commit()
    
    print("Database created successfully!")
    print(f"Created user: {test_user.full_name}")