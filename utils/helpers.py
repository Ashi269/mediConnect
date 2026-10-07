import logging
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user

logger = logging.getLogger(__name__)

def is_authorized(user, resource, action='view'):
    """
    Check if a user is authorized to perform an action on a resource
    
    Parameters:
    - user: The user object
    - resource: The resource object (e.g., Appointment, Patient, etc.)
    - action: The action to perform (view, edit, delete)
    
    Returns:
    - Boolean indicating if user is authorized
    """
    if not user or not user.is_authenticated:
        logger.warning(f"Unauthenticated user attempted to {action} a {type(resource).__name__}")
        return False
        
    # Admin users can do anything
    if user.role == 'admin':
        return True
        
    # Check specific role permissions
    if user.role == 'doctor':
        # Doctors can access their own resources
        if hasattr(resource, 'doctor_id') and hasattr(user, 'doctor') and user.doctor and resource.doctor_id == user.doctor.id:
            return True
            
        # Doctors can access their patients' resources
        if hasattr(resource, 'patient_id') and hasattr(user, 'doctor') and user.doctor:
            from models import Appointment
            # Check if the patient has an appointment with this doctor
            appointments = Appointment.query.filter_by(
                doctor_id=user.doctor.id,
                patient_id=resource.patient_id
            ).first()
            if appointments:
                return True
                
    elif user.role == 'staff':
        # Staff can access their assigned doctor's resources
        if hasattr(resource, 'doctor_id') and hasattr(user, 'staff') and user.staff and user.staff.assigned_doctor_id:
            if resource.doctor_id == user.staff.assigned_doctor_id:
                return True
                
        # Staff can access resources they created
        if hasattr(resource, 'created_by_id') and hasattr(user, 'staff') and user.staff and resource.created_by_id == user.staff.id:
            return True
            
    elif user.role == 'patient':
        # Patients can access their own resources
        if hasattr(resource, 'patient_id') and hasattr(user, 'patient') and user.patient and resource.patient_id == user.patient.id:
            return True
            
    logger.warning(f"User {user.username} (role: {user.role}) attempted unauthorized {action} on {type(resource).__name__} {resource.id}")
    return False

def role_required(role):
    """
    Decorator for views that require a specific user role
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role != role:
                logger.warning(f"User {current_user.username} (role: {current_user.role}) attempted to access {role}-only view")
                flash('You do not have permission to access this page.', 'danger')
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator for views that require admin access
    """
    return role_required('admin')(f)

def doctor_required(f):
    """
    Decorator for views that require doctor access
    """
    return role_required('doctor')(f)

def staff_required(f):
    """
    Decorator for views that require staff access
    """
    return role_required('staff')(f)

def patient_required(f):
    """
    Decorator for views that require patient access
    """
    return role_required('patient')(f)

def format_date(date_obj, format_str='%B %d, %Y'):
    """
    Format a date object as a string
    """
    if date_obj:
        return date_obj.strftime(format_str)
    return ''

def format_datetime(dt_obj, format_str='%B %d, %Y %I:%M %p'):
    """
    Format a datetime object as a string
    """
    if dt_obj:
        return dt_obj.strftime(format_str)
    return ''

def format_currency(amount):
    """
    Format a number as currency
    """
    if amount is not None:
        return f"${amount:.2f}"
    return '$0.00'

def get_appointment_status_badge(status):
    """
    Return Bootstrap badge HTML for appointment status
    """
    badges = {
        'scheduled': '<span class="badge bg-warning text-dark">Scheduled</span>',
        'completed': '<span class="badge bg-success">Completed</span>',
        'cancelled': '<span class="badge bg-danger">Cancelled</span>',
        'no-show': '<span class="badge bg-secondary">No Show</span>'
    }
    return badges.get(status, '<span class="badge bg-info">Unknown</span>')

def get_invoice_status_badge(status):
    """
    Return Bootstrap badge HTML for invoice status
    """
    badges = {
        'pending': '<span class="badge bg-warning text-dark">Pending</span>',
        'paid': '<span class="badge bg-success">Paid</span>',
        'cancelled': '<span class="badge bg-danger">Cancelled</span>',
        'overdue': '<span class="badge bg-danger">Overdue</span>'
    }
    return badges.get(status, '<span class="badge bg-info">Unknown</span>')

def calculate_age(birth_date):
    """
    Calculate age from birth date
    """
    if not birth_date:
        return None
    
    from datetime import datetime
    today = datetime.now().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def generate_random_password(length=10):
    """
    Generate a random password
    """
    import string
    import random
    
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(length))

def sanitize_html(html_content):
    """
    Sanitize HTML content to prevent XSS attacks
    """
    # This is a very simple implementation
    # In a production environment, use a library like bleach
    import re
    
    # Remove script tags and their contents
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
    
    # Remove on* attributes
    html_content = re.sub(r' on\w+=".*?"', '', html_content)
    
    return html_content