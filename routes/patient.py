from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, Doctor, Patient, Appointment, Prescription, Medication, MedicalRecord, Invoice
from forms import PatientUpdateForm, AppointmentForm
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from utils.helpers import patient_required, format_currency

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    # Get the logged-in patient
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get upcoming appointments
    today = datetime.now()
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.start_time > today,
        Appointment.status == 'scheduled'
    ).order_by(Appointment.start_time).limit(5).all()
    
    # Get recent prescriptions
    recent_prescriptions = Prescription.query.filter_by(
        patient_id=patient.id
    ).order_by(Prescription.date_prescribed.desc()).limit(3).all()
    
    # Get pending invoices
    pending_invoices = Invoice.query.filter_by(
        patient_id=patient.id,
        status='pending'
    ).order_by(Invoice.due_date).all()
    
    # Get medication reminders
    medications = Medication.query.join(Prescription).filter(
        Prescription.patient_id == patient.id
    ).all()
    
    return render_template('patient/dashboard.html',
                          patient=patient,
                          upcoming_appointments=upcoming_appointments,
                          recent_prescriptions=recent_prescriptions,
                          pending_invoices=pending_invoices,
                          medications=medications,
                          format_currency=format_currency)

@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@patient_required
def profile():
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    form = PatientUpdateForm(obj=patient)
    
    if form.validate_on_submit():
        patient.first_name = form.first_name.data
        patient.last_name = form.last_name.data
        patient.date_of_birth = form.date_of_birth.data
        patient.gender = form.gender.data
        patient.phone = form.phone.data
        patient.address = form.address.data
        patient.blood_type = form.blood_type.data
        patient.allergies = form.allergies.data
        patient.emergency_contact_name = form.emergency_contact_name.data
        patient.emergency_contact_phone = form.emergency_contact_phone.data
        
        user = User.query.get(patient.user_id)
        user.email = form.email.data
        
        db.session.commit()
        
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('patient.profile'))
    
    # Pre-populate email from user model
    if patient.user:
        form.email.data = patient.user.email
    
    return render_template('patient/profile.html', 
                          form=form, 
                          patient=patient)

@patient_bp.route('/appointments')
@login_required
@patient_required
def appointments():
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get filter parameters
    status = request.args.get('status', 'all')
    
    # Build the query
    query = Appointment.query.filter_by(patient_id=patient.id)
    
    # Apply status filter
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Get appointments ordered by start time
    appointments = query.order_by(Appointment.start_time.desc()).all()
    
    return render_template('patient/appointments.html',
                          patient=patient,
                          appointments=appointments,
                          status_filter=status)

@patient_bp.route('/appointments/new', methods=['GET', 'POST'])
@login_required
@patient_required
def new_appointment():
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    form = AppointmentForm()
    
    # Pre-select the patient
    form.patient_id.choices = [(patient.id, f"{patient.first_name} {patient.last_name}")]
    form.patient_id.data = patient.id
    
    # Populate doctor choices
    doctors = Doctor.query.all()
    form.doctor_id.choices = [(d.id, f"Dr. {d.first_name} {d.last_name} - {d.specialty}") for d in doctors]
    
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
            flash('There is a scheduling conflict with another appointment. Please choose a different time.', 'danger')
        else:
            # Create appointment
            appointment = Appointment(
                doctor_id=form.doctor_id.data,
                patient_id=patient.id,
                start_time=start_datetime,
                end_time=end_datetime,
                reason=form.reason.data,
                notes=form.notes.data,
                status='scheduled'
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            flash('Appointment scheduled successfully. You will be notified when the appointment is confirmed.', 'success')
            return redirect(url_for('patient.appointments'))
    
    return render_template('patient/appointment_form.html', 
                          form=form, 
                          patient=patient)

@patient_bp.route('/prescriptions')
@login_required
@patient_required
def prescriptions():
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all prescriptions for this patient
    prescriptions = Prescription.query.filter_by(
        patient_id=patient.id
    ).order_by(Prescription.date_prescribed.desc()).all()
    
    return render_template('patient/prescriptions.html',
                          patient=patient,
                          prescriptions=prescriptions)

@patient_bp.route('/prescriptions/<int:id>')
@login_required
@patient_required
def prescription_detail(id):
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    prescription = Prescription.query.get_or_404(id)
    
    # Make sure the prescription belongs to this patient
    if prescription.patient_id != patient.id:
        flash('You do not have permission to view this prescription.', 'danger')
        return redirect(url_for('patient.prescriptions'))
    
    return render_template('patient/prescription_detail.html',
                          patient=patient,
                          prescription=prescription)

@patient_bp.route('/medical-records')
@login_required
@patient_required
def medical_records():
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all medical records for this patient
    medical_records = MedicalRecord.query.filter_by(
        patient_id=patient.id
    ).order_by(MedicalRecord.date.desc()).all()
    
    return render_template('patient/medical_records.html',
                          patient=patient,
                          medical_records=medical_records)

@patient_bp.route('/medical-records/<int:id>')
@login_required
@patient_required
def medical_record_detail(id):
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    medical_record = MedicalRecord.query.get_or_404(id)
    
    # Make sure the medical record belongs to this patient
    if medical_record.patient_id != patient.id:
        flash('You do not have permission to view this medical record.', 'danger')
        return redirect(url_for('patient.medical_records'))
    
    return render_template('patient/medical_record_detail.html',
                          patient=patient,
                          medical_record=medical_record)

@patient_bp.route('/invoices')
@login_required
@patient_required
def invoices():
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get filter parameters
    status = request.args.get('status', 'all')
    
    # Build the query
    query = Invoice.query.filter_by(patient_id=patient.id)
    
    # Apply status filter
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Get invoices ordered by date
    invoices = query.order_by(Invoice.invoice_date.desc()).all()
    
    return render_template('patient/invoices.html',
                          patient=patient,
                          invoices=invoices,
                          status_filter=status,
                          format_currency=format_currency)

@patient_bp.route('/invoices/<int:id>')
@login_required
@patient_required
def invoice_detail(id):
    patient = Patient.query.filter_by(user_id=current_user.id).first_or_404()
    invoice = Invoice.query.get_or_404(id)
    
    # Make sure the invoice belongs to this patient
    if invoice.patient_id != patient.id:
        flash('You do not have permission to view this invoice.', 'danger')
        return redirect(url_for('patient.invoices'))
    
    return render_template('patient/invoice_detail.html',
                          patient=patient,
                          invoice=invoice,
                          format_currency=format_currency)
