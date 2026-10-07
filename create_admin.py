# create_admin.py

from app import app, db
from models import User, Admin
from werkzeug.security import generate_password_hash

# Default credentials
email = 'superadmin@example.com'
username = 'superadmin'
password = 'superadmin123'
first_name = 'Super'
last_name = 'Admin'
phone = '1212121212'

with app.app_context():
    # Check if admin already exists
    if User.query.filter_by(email=email).first():
        print("Admin user already exists.")
    else:
        # Create new user
        user = User(
            email=email,
            username=username,
            role='admin',
            is_active=True,
            is_approved=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Create admin profile
        admin = Admin(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        db.session.add(admin)
        db.session.commit()

        print(f"✅ Admin user created: {email} / {password}")
