import os
import logging
from datetime import datetime
from flask import Flask, redirect, url_for, flash, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, current_user
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set up base class for models
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-default-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Get database URL from environment or fallback
db_url = os.environ.get("DATABASE_URL", "sqlite:///local_dev.db")
if not db_url:
    logger.error("DATABASE_URL environment variable not set.")
else:
    logger.info(f"Using database URL: {db_url}")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure mail settings
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'mediconnect@example.com')

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
mail.init_app(app)

# Configure login settings
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Create database tables and register blueprints
with app.app_context():
    # Import models so tables are created
    from models import User, Doctor, Patient, Staff, Admin, Appointment, Prescription, MedicalRecord, Invoice, Department, Service
    db.create_all()

    # Register blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.doctor import doctor_bp
    from routes.staff import staff_bp
    from routes.patient import patient_bp
    from routes.appointments import appointments_bp
    from routes.billing import billing_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(appointments_bp, url_prefix='/appointments')
    app.register_blueprint(billing_bp, url_prefix='/billing')

    # Home route
    @app.route('/')
    def home():
        # Redirect users based on role
        if current_user.is_authenticated:
            if hasattr(current_user, 'role'):
                if current_user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif current_user.role == 'doctor':
                    return redirect(url_for('doctor.dashboard'))
                elif current_user.role == 'staff':
                    return redirect(url_for('staff.dashboard'))
                elif current_user.role == 'patient':
                    return redirect(url_for('patient.dashboard'))

        # Default home page for non-authenticated users
        return render_template('home.html')

    # Context processor for template variables
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))
