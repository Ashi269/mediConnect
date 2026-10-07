from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, Doctor, Patient, Staff, Appointment, Invoice, InvoiceItem, Service
from forms import AppointmentForm, PatientRegistrationForm, PatientSearchForm
from datetime import datetime, timedelta
from sqlalchemy import or_
from utils.helpers import staff_required, format_currency
from utils.email import send_appointment_notification
import json

staff_bp = Blueprint('staff', __name__)

@staff_bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    # Get the logged-in staff member
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get today's date
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get today's appointments
    today_appointments = Appointment.query.filter(
        Appointment.start_time >= today_start,
        Appointment.start_time <= today_end
    ).order_by(Appointment.start_time).all()
    
    if staff.assigned_doctor_id:
        # If assigned to a doctor, only show that doctor's appointments
        today_appointments = [a for a in today_appointments if a.doctor_id == staff.assigned_doctor_id]
    
    # Get appointment counts by status
    appointment_stats = {
        'scheduled': Appointment.query.filter_by(status='scheduled').count(),
        'completed': Appointment.query.filter_by(status='completed').count(),
        'cancelled': Appointment.query.filter_by(status='cancelled').count(),
        'no_show': Appointment.query.filter_by(status='no-show').count()
    }
    
    # Get all doctors
    doctors = Doctor.query.all()
    
    # If assigned to a doctor, only show that doctor
    assigned_doctor = None
    if staff.assigned_doctor_id:
        doctors = [d for d in doctors if d.id == staff.assigned_doctor_id]
        assigned_doctor = doctors[0] if doctors else None
    
    # Get recent patients
    recent_patients = Patient.query.order_by(Patient.user_id.desc()).limit(5).all()
    
    # Get pending invoices
    pending_invoices = Invoice.query.filter_by(status='pending').count()
    
    return render_template('staff/dashboard.html',
                          staff=staff,
                          today_appointments=today_appointments,
                          appointment_stats=appointment_stats,
                          doctors=doctors,
                          assigned_doctor=assigned_doctor,
                          recent_patients=recent_patients,
                          pending_invoices=pending_invoices)

@staff_bp.route('/appointments')
@login_required
@staff_required
def appointments():
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get filter parameters
    doctor_id = request.args.get('doctor_id')
    status = request.args.get('status', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build the query
    query = Appointment.query
    
    # Apply filters
    if doctor_id:
        query = query.filter_by(doctor_id=int(doctor_id))
    elif staff.assigned_doctor_id:
        # If assigned to a doctor and no doctor filter applied, show only that doctor's appointments
        query = query.filter_by(doctor_id=staff.assigned_doctor_id)
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Appointment.start_time >= start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            end_date = datetime.combine(end_date, datetime.max.time())
            query = query.filter(Appointment.start_time <= end_date)
        except ValueError:
            pass
    
    # Get appointments ordered by start time (newest first)
    appointments = query.order_by(Appointment.start_time.desc()).all()
    
    # Get all doctors for filter dropdown
    doctors = Doctor.query.all()
    if staff.assigned_doctor_id:
        # If assigned to a doctor, only show that doctor in dropdown
        doctors = [d for d in doctors if d.id == staff.assigned_doctor_id]
    
    return render_template('staff/appointments.html',
                          staff=staff,
                          appointments=appointments,
                          doctors=doctors,
                          selected_doctor_id=doctor_id,
                          status_filter=status,
                          start_date=start_date,
                          end_date=end_date)

@staff_bp.route('/appointments/new', methods=['GET', 'POST'])
@login_required
@staff_required
def new_appointment():
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    form = AppointmentForm()
    
    # Populate patient choices
    patients = Patient.query.all()
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients]
    
    # Populate doctor choices
    doctors = Doctor.query.all()
    
    # If staff is assigned to a doctor, only show that doctor
    if staff.assigned_doctor_id:
        doctors = [d for d in doctors if d.id == staff.assigned_doctor_id]
        if doctors:
            form.doctor_id.choices = [(d.id, f"{d.first_name} {d.last_name}") for d in doctors]
            form.doctor_id.data = doctors[0].id
    else:
        form.doctor_id.choices = [(d.id, f"{d.first_name} {d.last_name}") for d in doctors]
    
    if form.validate_on_submit():
        # Convert form data to datetime objects
        appointment_date = form.date.data
        start_time = form.start_time.data
        end_time = form.end_time.data
        
        start_datetime = datetime.combine(appointment_date, start_time)
        end_datetime = datetime.combine(appointment_date, end_time)
        
        # Check for time conflicts
        conflicting_appointments = Appointment.query.filter(
            Appointment.doctor_id == form.doctor_id.data,
            Appointment.status != 'cancelled',
            Appointment.start_time < end_datetime,
            Appointment.end_time > start_datetime
        ).all()
        
        if conflicting_appointments:
            flash('There is a scheduling conflict with another appointment.', 'danger')
        else:
            # Create appointment
            appointment = Appointment(
                doctor_id=form.doctor_id.data,
                patient_id=form.patient_id.data,
                start_time=start_datetime,
                end_time=end_datetime,
                reason=form.reason.data,
                notes=form.notes.data,
                status='scheduled',
                created_by_id=staff.id
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            # Send notification to patient
            patient = Patient.query.get(form.patient_id.data)
            doctor = Doctor.query.get(form.doctor_id.data)
            if patient and doctor:
                send_appointment_notification(patient, doctor, appointment)
            
            flash('Appointment scheduled successfully.', 'success')
            return redirect(url_for('staff.appointments'))
    
    return render_template('staff/appointment_form.html', 
                          form=form, 
                          staff=staff,
                          is_new=True)

@staff_bp.route('/appointments/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_appointment(id):
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    appointment = Appointment.query.get_or_404(id)
    
    # If staff is assigned to a doctor, make sure they can only edit that doctor's appointments
    if staff.assigned_doctor_id and appointment.doctor_id != staff.assigned_doctor_id:
        flash('You do not have permission to edit this appointment.', 'danger')
        return redirect(url_for('staff.appointments'))
    
    form = AppointmentForm(obj=appointment)
    
    # Populate patient choices
    patients = Patient.query.all()
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients]
    
    # Populate doctor choices
    doctors = Doctor.query.all()
    
    # If staff is assigned to a doctor, only show that doctor
    if staff.assigned_doctor_id:
        doctors = [d for d in doctors if d.id == staff.assigned_doctor_id]
    
    form.doctor_id.choices = [(d.id, f"{d.first_name} {d.last_name}") for d in doctors]
    
    # Set defaults for date and time
    if request.method == 'GET':
        form.date.data = appointment.start_time.date()
        form.start_time.data = appointment.start_time.time()
        form.end_time.data = appointment.end_time.time()
    
    if form.validate_on_submit():
        # Convert form data to datetime objects
        appointment_date = form.date.data
        start_time = form.start_time.data
        end_time = form.end_time.data
        
        start_datetime = datetime.combine(appointment_date, start_time)
        end_datetime = datetime.combine(appointment_date, end_time)
        
        # Check for time conflicts with other appointments
        conflicting_appointments = Appointment.query.filter(
            Appointment.doctor_id == form.doctor_id.data,
            Appointment.id != appointment.id,
            Appointment.status != 'cancelled',
            Appointment.start_time < end_datetime,
            Appointment.end_time > start_datetime
        ).all()
        
        if conflicting_appointments:
            flash('There is a scheduling conflict with another appointment.', 'danger')
        else:
            # Update appointment
            appointment.doctor_id = form.doctor_id.data
            appointment.patient_id = form.patient_id.data
            appointment.start_time = start_datetime
            appointment.end_time = end_datetime
            appointment.reason = form.reason.data
            appointment.notes = form.notes.data
            
            db.session.commit()
            
            # Send notification to patient about update
            patient = Patient.query.get(form.patient_id.data)
            doctor = Doctor.query.get(form.doctor_id.data)
            if patient and doctor:
                send_appointment_notification(patient, doctor, appointment, is_update=True)
            
            flash('Appointment updated successfully.', 'success')
            return redirect(url_for('staff.appointments'))
    
    return render_template('staff/appointment_form.html', 
                          form=form, 
                          staff=staff,
                          appointment=appointment,
                          is_new=False)

@staff_bp.route('/patients')
@login_required
@staff_required
def patients():
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Create search form
    form = PatientSearchForm()
    
    # Get search parameter
    search = request.args.get('search', '')
    
    # Build the query
    query = Patient.query
    
    if search:
        query = query.filter(
            or_(
                Patient.first_name.ilike(f'%{search}%'),
                Patient.last_name.ilike(f'%{search}%'),
                Patient.phone.ilike(f'%{search}%')
            )
        )
    
    # Get patients
    patients = query.all()
    
    return render_template('staff/patients.html',
                          staff=staff,
                          patients=patients,
                          form=form,
                          search=search)

@staff_bp.route('/patients/new', methods=['GET', 'POST'])
@login_required
@staff_required
def new_patient():
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    form = PatientRegistrationForm()
    
    # Remove username and password fields for staff-created patients
    delattr(form, 'username')
    delattr(form, 'password')
    delattr(form, 'confirm_password')
    
    if form.validate_on_submit():
        # Generate a unique username based on first and last name
        base_username = f"{form.first_name.data.lower()}.{form.last_name.data.lower()}"
        username = base_username
        count = 1
        
        # Check if username exists and increment until unique
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{count}"
            count += 1
        
        # Create temporary random password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        
        # Create new user
        user = User(
            username=username,
            email=form.email.data,
            role='patient',
            is_approved=True
        )
        user.set_password(temp_password)
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
        
        flash(f'Patient registered successfully. Temporary login: {username} / {temp_password}', 'success')
        return redirect(url_for('staff.patients'))
    
    return render_template('staff/patient_form.html', form=form, staff=staff)

@staff_bp.route('/patients/<int:id>')
@login_required
@staff_required
def patient_detail(id):
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    patient = Patient.query.get_or_404(id)
    
    # Get patient's appointments
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.start_time.desc()).all()
    
    # If staff is assigned to a doctor, only show appointments with that doctor
    if staff.assigned_doctor_id:
        appointments = [a for a in appointments if a.doctor_id == staff.assigned_doctor_id]
    
    # Get patient's invoices
    invoices = Invoice.query.filter_by(patient_id=patient.id).order_by(Invoice.invoice_date.desc()).all()
    
    return render_template('staff/patient_detail.html',
                          staff=staff,
                          patient=patient,
                          appointments=appointments,
                          invoices=invoices,
                          format_currency=format_currency)

@staff_bp.route('/invoices')
@login_required
@staff_required
def invoices():
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get filter parameters
    status = request.args.get('status', 'all')
    patient_id = request.args.get('patient_id')
    
    # Build the query
    query = Invoice.query
    
    # Apply filters
    if status != 'all':
        query = query.filter_by(status=status)
    
    if patient_id:
        query = query.filter_by(patient_id=int(patient_id))
    
    # Get invoices ordered by date (newest first)
    invoices = query.order_by(Invoice.invoice_date.desc()).all()
    
    # Get all patients for filter dropdown
    patients = Patient.query.all()
    
    return render_template('staff/invoices.html',
                          staff=staff,
                          invoices=invoices,
                          patients=patients,
                          status_filter=status,
                          selected_patient_id=patient_id,
                          format_currency=format_currency)

@staff_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_invoice():
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get patient ID from query parameter
    patient_id = request.args.get('patient_id')
    appointment_id = request.args.get('appointment_id')
    
    patient = None
    appointment = None
    
    if patient_id:
        patient = Patient.query.get(patient_id)
    
    if appointment_id:
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            patient = appointment.patient
            
            # Check if invoice already exists for this appointment
            existing_invoice = Invoice.query.filter_by(appointment_id=appointment.id).first()
            if existing_invoice:
                flash('An invoice already exists for this appointment.', 'warning')
                return redirect(url_for('staff.invoices'))
    
    # Get all services
    services = Service.query.all()
    
    # Get all patients (for dropdown)
    patients = Patient.query.all()
    
    if request.method == 'POST':
        selected_patient_id = request.form.get('patient_id')
        selected_appointment_id = request.form.get('appointment_id', None)
        
        if not selected_patient_id:
            flash('Please select a patient.', 'danger')
            return redirect(url_for('staff.create_invoice'))
        
        # Create invoice
        invoice = Invoice(
            patient_id=selected_patient_id,
            created_by_id=staff.id,
            appointment_id=selected_appointment_id if selected_appointment_id else None,
            due_date=datetime.now() + timedelta(days=30),
            status='pending',
            notes=request.form.get('notes', '')
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get invoice ID
        
        # Add items from form
        total_amount = 0
        items_json = request.form.get('items_json', '[]')
        items = json.loads(items_json)
        
        for item in items:
            service_id = item.get('service_id')
            service = None
            
            # If service is selected, get its details
            if service_id and service_id != 'custom':
                service = Service.query.get(service_id)
            
            # Create invoice item
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                service_id=service.id if service else None,
                description=item.get('description', 'Custom service') if not service else service.name,
                quantity=int(item.get('quantity', 1)),
                unit_price=float(item.get('price', 0)) if not service else service.cost,
                total_price=float(item.get('total', 0)) if not service else (service.cost * int(item.get('quantity', 1)))
            )
            
            db.session.add(invoice_item)
            total_amount += invoice_item.total_price
        
        # Update invoice total
        invoice.total_amount = total_amount
        db.session.commit()
        
        flash('Invoice created successfully.', 'success')
        return redirect(url_for('staff.invoices'))
    
    return render_template('staff/create_invoice.html',
                          staff=staff,
                          patient=patient,
                          appointment=appointment,
                          patients=patients,
                          services=services)

@staff_bp.route('/invoices/<int:id>/update-status', methods=['POST'])
@login_required
@staff_required
def update_invoice_status(id):
    staff = Staff.query.filter_by(user_id=current_user.id).first_or_404()
    invoice = Invoice.query.get_or_404(id)
    
    new_status = request.form.get('status')
    if new_status in ['pending', 'paid', 'cancelled', 'overdue']:
        invoice.status = new_status
        db.session.commit()
        flash(f'Invoice status updated to {new_status}.', 'success')
    
    return redirect(url_for('staff.invoices'))
