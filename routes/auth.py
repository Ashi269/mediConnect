from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash
from app import db
from models import User, Doctor, Patient, Staff, Admin
from forms import LoginForm, DoctorRegistrationForm, PatientRegistrationForm, StaffRegistrationForm
from utils.email import send_registration_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect based on user role
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif current_user.role == 'staff':
            return redirect(url_for('staff.dashboard'))
        elif current_user.role == 'patient':
            return redirect(url_for('patient.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Account is disabled. Please contact administration.', 'danger')
                return render_template('login.html', form=form)
            
            if not user.is_approved and user.role in ['doctor', 'staff']:
                flash('Your account is pending approval. Please contact administration.', 'warning')
                return render_template('login.html', form=form)
            
            login_user(user)
            next_page = request.args.get('next')
            
            # Redirect based on user role
            if next_page:
                return redirect(next_page)
            elif user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor.dashboard'))
            elif user.role == 'staff':
                return redirect(url_for('staff.dashboard'))
            elif user.role == 'patient':
                return redirect(url_for('patient.dashboard'))
        else:
            flash('Login failed. Please check email and password.', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@auth_bp.route('/register/doctor', methods=['GET', 'POST'])
def register_doctor():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = DoctorRegistrationForm()
    
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == form.email.data) | (User.username == form.username.data)
        ).first()
        
        if existing_user:
            flash('Email or username already in use.', 'danger')
        else:
            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                role='doctor',
                is_approved=False  # Doctors need approval
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()  # Get user ID without committing
            
            # Create doctor profile
            doctor = Doctor(
                user_id=user.id,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                specialty=form.specialty.data,
                phone=form.phone.data,
                license_number=form.license_number.data,
                bio=form.bio.data,
                address=form.address.data
            )
            db.session.add(doctor)
            db.session.commit()
            
            # Send notification email
            send_registration_email(user, 'doctor')
            
            flash('Registration successful! Your account requires admin approval. You will be notified when approved.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form, user_type='doctor')

@auth_bp.route('/register/patient', methods=['GET', 'POST'])
def register_patient():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = PatientRegistrationForm()
    
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == form.email.data) | (User.username == form.username.data)
        ).first()
        
        if existing_user:
            flash('Email or username already in use.', 'danger')
        else:
            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                role='patient',
                is_approved=True  # Patients don't need approval
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()  # Get user ID without committing
            
            # Create patient profile
            patient = Patient(
                user_id=user.id,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                date_of_birth=form.date_of_birth.data,
                gender=form.gender.data,
                phone=form.phone.data,
                address=form.address.data,
                blood_type=form.blood_type.data,
                allergies=form.allergies.data,
                emergency_contact_name=form.emergency_contact_name.data,
                emergency_contact_phone=form.emergency_contact_phone.data
            )
            db.session.add(patient)
            db.session.commit()
            
            # Send notification email
            send_registration_email(user, 'patient')
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form, user_type='patient')

@auth_bp.route('/register/staff', methods=['GET', 'POST'])
@login_required
def register_staff():
    # Only doctors or admins can register staff
    if current_user.role not in ['doctor', 'admin']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('home'))
    
    form = StaffRegistrationForm()
    
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == form.email.data) | (User.username == form.username.data)
        ).first()
        
        if existing_user:
            flash('Email or username already in use.', 'danger')
        else:
            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                role='staff',
                is_approved=True if current_user.role == 'admin' else False
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()  # Get user ID without committing
            
            # Create staff profile
            staff = Staff(
                user_id=user.id,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                position=form.position.data,
                phone=form.phone.data,
                address=form.address.data
            )
            
            # If created by doctor, auto-assign to that doctor
            if current_user.role == 'doctor':
                doctor = Doctor.query.filter_by(user_id=current_user.id).first()
                if doctor:
                    staff.assigned_doctor_id = doctor.id
            
            db.session.add(staff)
            db.session.commit()
            
            # Send notification email
            send_registration_email(user, 'staff')
            
            if current_user.role == 'admin':
                flash('Staff registration successful! The staff can now log in.', 'success')
                return redirect(url_for('admin.staff_list'))
            else:
                flash('Staff registration successful! Staff account requires admin approval.', 'success')
                return redirect(url_for('doctor.staff_list'))
    
    return render_template('register.html', form=form, user_type='staff')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))
