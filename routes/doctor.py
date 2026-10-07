from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, Doctor, Patient, Staff, Appointment, Prescription, Medication, MedicalRecord, Invoice, InvoiceItem, Service
from forms import AppointmentForm, AppointmentStatusForm, PrescriptionForm, MedicationForm, MedicalRecordForm, StaffUpdateForm
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from utils.helpers import doctor_required, format_currency
import json

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/dashboard')
@login_required
@doctor_required
def dashboard():
    # Get the logged-in doctor
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get appointment statistics
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get today's appointments
    today_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.start_time >= today_start,
        Appointment.start_time <= today_end
    ).order_by(Appointment.start_time).all()
    
    # Get upcoming appointments (excluding today)
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.start_time > today_end,
        Appointment.status == 'scheduled'
    ).order_by(Appointment.start_time).limit(5).all()
    
    # Get recent patients
    recent_patients = Patient.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().order_by(Appointment.start_time.desc()).limit(5).all()
    
    # Get appointment counts by status
    appointment_stats = {
        'scheduled': Appointment.query.filter_by(doctor_id=doctor.id, status='scheduled').count(),
        'completed': Appointment.query.filter_by(doctor_id=doctor.id, status='completed').count(),
        'cancelled': Appointment.query.filter_by(doctor_id=doctor.id, status='cancelled').count(),
        'no_show': Appointment.query.filter_by(doctor_id=doctor.id, status='no-show').count()
    }
    
    # Get appointment data for last 7 days for chart
    last_7_days = []
    appointment_counts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        count = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.start_time >= day_start,
            Appointment.start_time <= day_end
        ).count()
        
        last_7_days.append(day.strftime('%a'))
        appointment_counts.append(count)
    
    # Get doctor's personal staff
    personal_staff = Staff.query.filter_by(assigned_doctor_id=doctor.id).all()
    
    return render_template('doctor/dashboard.html',
                          doctor=doctor,
                          today_appointments=today_appointments,
                          upcoming_appointments=upcoming_appointments,
                          recent_patients=recent_patients,
                          appointment_stats=appointment_stats,
                          chart_labels=last_7_days,
                          chart_data=appointment_counts,
                          personal_staff=personal_staff)

@doctor_bp.route('/appointments')
@login_required
@doctor_required
def appointments():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get filter parameters
    status = request.args.get('status', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build the query
    query = Appointment.query.filter_by(doctor_id=doctor.id)
    
    # Apply filters
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
    
    return render_template('doctor/appointments.html',
                          doctor=doctor,
                          appointments=appointments,
                          status_filter=status,
                          start_date=start_date,
                          end_date=end_date)

@doctor_bp.route('/appointments/new', methods=['GET', 'POST'])
@login_required
@doctor_required
def new_appointment():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    form = AppointmentForm()
    
    # Populate patient choices
    patients = Patient.query.all()
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients]
    
    # Pre-select the doctor
    form.doctor_id.choices = [(doctor.id, f"{doctor.first_name} {doctor.last_name}")]
    form.doctor_id.data = doctor.id
    
    if form.validate_on_submit():
        # Convert form data to datetime objects
        appointment_date = form.date.data
        start_time = form.start_time.data
        end_time = form.end_time.data
        
        start_datetime = datetime.combine(appointment_date, start_time)
        end_datetime = datetime.combine(appointment_date, end_time)
        
        # Check for time conflicts
        conflicting_appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.status != 'cancelled',
            Appointment.start_time < end_datetime,
            Appointment.end_time > start_datetime
        ).all()
        
        if conflicting_appointments:
            flash('There is a scheduling conflict with another appointment.', 'danger')
        else:
            # Create appointment
            appointment = Appointment(
                doctor_id=doctor.id,
                patient_id=form.patient_id.data,
                start_time=start_datetime,
                end_time=end_datetime,
                reason=form.reason.data,
                notes=form.notes.data,
                status='scheduled'
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            flash('Appointment scheduled successfully.', 'success')
            return redirect(url_for('doctor.appointments'))
    
    return render_template('doctor/appointment_form.html', 
                          form=form, 
                          doctor=doctor,
                          is_new=True)

@doctor_bp.route('/appointments/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@doctor_required
def edit_appointment(id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    appointment = Appointment.query.get_or_404(id)
    
    # Make sure the appointment belongs to this doctor
    if appointment.doctor_id != doctor.id:
        flash('You do not have permission to edit this appointment.', 'danger')
        return redirect(url_for('doctor.appointments'))
    
    form = AppointmentForm(obj=appointment)
    
    # Populate patient choices
    patients = Patient.query.all()
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients]
    
    # Pre-select the doctor
    form.doctor_id.choices = [(doctor.id, f"{doctor.first_name} {doctor.last_name}")]
    form.doctor_id.data = doctor.id
    
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
            Appointment.doctor_id == doctor.id,
            Appointment.id != appointment.id,
            Appointment.status != 'cancelled',
            Appointment.start_time < end_datetime,
            Appointment.end_time > start_datetime
        ).all()
        
        if conflicting_appointments:
            flash('There is a scheduling conflict with another appointment.', 'danger')
        else:
            # Update appointment
            appointment.patient_id = form.patient_id.data
            appointment.start_time = start_datetime
            appointment.end_time = end_datetime
            appointment.reason = form.reason.data
            appointment.notes = form.notes.data
            
            db.session.commit()
            
            flash('Appointment updated successfully.', 'success')
            return redirect(url_for('doctor.appointments'))
    
    return render_template('doctor/appointment_form.html', 
                          form=form, 
                          doctor=doctor,
                          appointment=appointment,
                          is_new=False)

@doctor_bp.route('/appointments/<int:id>/status', methods=['GET', 'POST'])
@login_required
@doctor_required
def appointment_status(id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    appointment = Appointment.query.get_or_404(id)
    
    # Make sure the appointment belongs to this doctor
    if appointment.doctor_id != doctor.id:
        flash('You do not have permission to update this appointment.', 'danger')
        return redirect(url_for('doctor.appointments'))
    
    form = AppointmentStatusForm(obj=appointment)
    
    if form.validate_on_submit():
        appointment.status = form.status.data
        appointment.notes = form.notes.data
        db.session.commit()
        
        flash('Appointment status updated successfully.', 'success')
        return redirect(url_for('doctor.appointments'))
    
    return render_template('doctor/appointment_status.html', 
                          form=form, 
                          doctor=doctor,
                          appointment=appointment)

@doctor_bp.route('/patients')
@login_required
@doctor_required
def patients():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get search parameter
    search = request.args.get('search', '')
    
    # Get patients who have had appointments with this doctor
    query = Patient.query.join(Appointment).filter(Appointment.doctor_id == doctor.id).distinct()
    
    if search:
        query = query.filter(
            or_(
                Patient.first_name.ilike(f'%{search}%'),
                Patient.last_name.ilike(f'%{search}%'),
                Patient.phone.ilike(f'%{search}%')
            )
        )
    
    patients = query.all()
    
    return render_template('doctor/patients.html',
                          doctor=doctor,
                          patients=patients,
                          search=search)

@doctor_bp.route('/patients/<int:id>')
@login_required
@doctor_required
def patient_detail(id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    patient = Patient.query.get_or_404(id)
    
    # Check if the doctor has seen this patient
    has_appointment = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.patient_id == patient.id
    ).first()
    
    if not has_appointment:
        flash('You do not have permission to view this patient.', 'danger')
        return redirect(url_for('doctor.patients'))
    
    # Get patient's appointments with this doctor
    appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.patient_id == patient.id
    ).order_by(Appointment.start_time.desc()).all()
    
    # Get patient's prescriptions from this doctor
    prescriptions = Prescription.query.filter(
        Prescription.doctor_id == doctor.id,
        Prescription.patient_id == patient.id
    ).order_by(Prescription.date_prescribed.desc()).all()
    
    # Get patient's medical records from this doctor
    medical_records = MedicalRecord.query.filter(
        MedicalRecord.doctor_id == doctor.id,
        MedicalRecord.patient_id == patient.id
    ).order_by(MedicalRecord.date.desc()).all()
    
    return render_template('doctor/patient_detail.html',
                          doctor=doctor,
                          patient=patient,
                          appointments=appointments,
                          prescriptions=prescriptions,
                          medical_records=medical_records)

@doctor_bp.route('/prescriptions')
@login_required
@doctor_required
def prescriptions():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get patient filter
    patient_id = request.args.get('patient_id')
    
    # Build the query
    query = Prescription.query.filter_by(doctor_id=doctor.id)
    
    # Apply patient filter
    if patient_id:
        query = query.filter_by(patient_id=int(patient_id))
    
    # Get prescriptions
    prescriptions = query.order_by(Prescription.date_prescribed.desc()).all()
    
    # Get all patients for filter dropdown
    patients = Patient.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().all()
    
    return render_template('doctor/prescriptions.html',
                          doctor=doctor,
                          prescriptions=prescriptions,
                          patients=patients,
                          selected_patient_id=patient_id)

@doctor_bp.route('/prescriptions/new', methods=['GET', 'POST'])
@login_required
@doctor_required
def new_prescription():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    form = PrescriptionForm()
    
    # Populate patient choices with patients who have had appointments
    patients = Patient.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().all()
    
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients]
    
    # Pre-populate patient if coming from appointment
    appointment_id = request.args.get('appointment_id')
    if appointment_id:
        appointment = Appointment.query.get(appointment_id)
        if appointment and appointment.doctor_id == doctor.id:
            form.patient_id.data = appointment.patient_id
    
    if form.validate_on_submit():
        prescription = Prescription(
            doctor_id=doctor.id,
            patient_id=form.patient_id.data,
            appointment_id=appointment_id if appointment_id else None,
            diagnosis=form.diagnosis.data,
            notes=form.notes.data
        )
        
        db.session.add(prescription)
        db.session.commit()
        
        flash('Prescription created successfully. Now add medications.', 'success')
        return redirect(url_for('doctor.edit_prescription', id=prescription.id))
    
    return render_template('doctor/prescription_form.html',
                          form=form,
                          doctor=doctor,
                          is_new=True)

@doctor_bp.route('/prescriptions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@doctor_required
def edit_prescription(id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    prescription = Prescription.query.get_or_404(id)
    
    # Make sure the prescription belongs to this doctor
    if prescription.doctor_id != doctor.id:
        flash('You do not have permission to edit this prescription.', 'danger')
        return redirect(url_for('doctor.prescriptions'))
    
    form = PrescriptionForm(obj=prescription)
    medication_form = MedicationForm()
    
    # Populate patient choices
    patients = Patient.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().all()
    
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients]
    
    if form.validate_on_submit():
        prescription.patient_id = form.patient_id.data
        prescription.diagnosis = form.diagnosis.data
        prescription.notes = form.notes.data
        
        db.session.commit()
        
        flash('Prescription updated successfully.', 'success')
        return redirect(url_for('doctor.edit_prescription', id=prescription.id))
    
    return render_template('doctor/prescription_form.html',
                          form=form,
                          medication_form=medication_form,
                          doctor=doctor,
                          prescription=prescription,
                          is_new=False)

@doctor_bp.route('/prescriptions/<int:id>/add-medication', methods=['POST'])
@login_required
@doctor_required
def add_medication(id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    prescription = Prescription.query.get_or_404(id)
    
    # Make sure the prescription belongs to this doctor
    if prescription.doctor_id != doctor.id:
        flash('You do not have permission to edit this prescription.', 'danger')
        return redirect(url_for('doctor.prescriptions'))
    
    form = MedicationForm()
    
    if form.validate_on_submit():
        medication = Medication(
            prescription_id=prescription.id,
            name=form.name.data,
            dosage=form.dosage.data,
            frequency=form.frequency.data,
            duration=form.duration.data,
            notes=form.notes.data
        )
        
        db.session.add(medication)
        db.session.commit()
        
        flash('Medication added successfully.', 'success')
    
    return redirect(url_for('doctor.edit_prescription', id=prescription.id))

@doctor_bp.route('/prescriptions/<int:prescription_id>/remove-medication/<int:medication_id>')
@login_required
@doctor_required
def remove_medication(prescription_id, medication_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    prescription = Prescription.query.get_or_404(prescription_id)
    
    # Make sure the prescription belongs to this doctor
    if prescription.doctor_id != doctor.id:
        flash('You do not have permission to edit this prescription.', 'danger')
        return redirect(url_for('doctor.prescriptions'))
    
    medication = Medication.query.get_or_404(medication_id)
    
    # Make sure the medication belongs to this prescription
    if medication.prescription_id != prescription.id:
        flash('Invalid medication.', 'danger')
        return redirect(url_for('doctor.edit_prescription', id=prescription.id))
    
    db.session.delete(medication)
    db.session.commit()
    
    flash('Medication removed successfully.', 'success')
    return redirect(url_for('doctor.edit_prescription', id=prescription.id))

@doctor_bp.route('/medical-records')
@login_required
@doctor_required
def medical_records():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get patient filter
    patient_id = request.args.get('patient_id')
    
    # Build the query
    query = MedicalRecord.query.filter_by(doctor_id=doctor.id)
    
    # Apply patient filter
    if patient_id:
        query = query.filter_by(patient_id=int(patient_id))
    
    # Get medical records
    medical_records = query.order_by(MedicalRecord.date.desc()).all()
    
    # Get all patients for filter dropdown
    patients = Patient.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().all()
    
    return render_template('doctor/medical_records.html',
                          doctor=doctor,
                          medical_records=medical_records,
                          patients=patients,
                          selected_patient_id=patient_id)

@doctor_bp.route('/medical-records/new', methods=['GET', 'POST'])
@login_required
@doctor_required
def new_medical_record():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    form = MedicalRecordForm()
    
    # Populate patient choices with patients who have had appointments
    patients = Patient.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().all()
    
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients]
    
    # Pre-populate patient if coming from appointment
    appointment_id = request.args.get('appointment_id')
    if appointment_id:
        appointment = Appointment.query.get(appointment_id)
        if appointment and appointment.doctor_id == doctor.id:
            form.patient_id.data = appointment.patient_id
    
    if form.validate_on_submit():
        medical_record = MedicalRecord(
            doctor_id=doctor.id,
            patient_id=form.patient_id.data,
            appointment_id=appointment_id if appointment_id else None,
            chief_complaint=form.chief_complaint.data,
            diagnosis=form.diagnosis.data,
            treatment_plan=form.treatment_plan.data,
            vital_signs=form.vital_signs.data,
            notes=form.notes.data
        )
        
        db.session.add(medical_record)
        db.session.commit()
        
        flash('Medical record created successfully.', 'success')
        return redirect(url_for('doctor.medical_records'))
    
    return render_template('doctor/medical_record_form.html',
                          form=form,
                          doctor=doctor,
                          is_new=True)

@doctor_bp.route('/medical-records/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@doctor_required
def edit_medical_record(id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    medical_record = MedicalRecord.query.get_or_404(id)
    
    # Make sure the medical record belongs to this doctor
    if medical_record.doctor_id != doctor.id:
        flash('You do not have permission to edit this medical record.', 'danger')
        return redirect(url_for('doctor.medical_records'))
    
    form = MedicalRecordForm(obj=medical_record)
    
    # Populate patient choices
    patients = Patient.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().all()
    
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients]
    
    if form.validate_on_submit():
        medical_record.patient_id = form.patient_id.data
        medical_record.chief_complaint = form.chief_complaint.data
        medical_record.diagnosis = form.diagnosis.data
        medical_record.treatment_plan = form.treatment_plan.data
        medical_record.vital_signs = form.vital_signs.data
        medical_record.notes = form.notes.data
        
        db.session.commit()
        
        flash('Medical record updated successfully.', 'success')
        return redirect(url_for('doctor.medical_records'))
    
    return render_template('doctor/medical_record_form.html',
                          form=form,
                          doctor=doctor,
                          medical_record=medical_record,
                          is_new=False)

@doctor_bp.route('/staff')
@login_required
@doctor_required
def staff_list():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    staff = Staff.query.filter_by(assigned_doctor_id=doctor.id).all()
    
    return render_template('doctor/staff.html',
                          doctor=doctor,
                          staff=staff)

@doctor_bp.route('/staff/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@doctor_required
def edit_staff(id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    staff = Staff.query.get_or_404(id)
    
    # Make sure the staff member is assigned to this doctor
    if staff.assigned_doctor_id != doctor.id:
        flash('You do not have permission to edit this staff member.', 'danger')
        return redirect(url_for('doctor.staff_list'))
    
    form = StaffUpdateForm(obj=staff)
    
    # Pre-select doctor
    form.assigned_doctor_id.choices = [(doctor.id, doctor.full_name)]
    form.assigned_doctor_id.data = doctor.id
    
    if form.validate_on_submit():
        staff.first_name = form.first_name.data
        staff.last_name = form.last_name.data
        staff.position = form.position.data
        staff.phone = form.phone.data
        staff.address = form.address.data
        
        db.session.commit()
        
        flash('Staff member updated successfully.', 'success')
        return redirect(url_for('doctor.staff_list'))
    
    return render_template('doctor/staff_form.html',
                          form=form,
                          doctor=doctor,
                          staff=staff)

@doctor_bp.route('/billing')
@login_required
@doctor_required
def billing():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get appointments that don't have invoices yet
    appointments_without_invoices = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == 'completed',
        ~Appointment.id.in_(db.session.query(Invoice.appointment_id).filter(Invoice.appointment_id != None))
    ).all()
    
    # Get existing invoices for appointments with this doctor
    invoices = Invoice.query.join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).order_by(Invoice.invoice_date.desc()).all()
    
    return render_template('doctor/billing.html',
                          doctor=doctor,
                          appointments_without_invoices=appointments_without_invoices,
                          invoices=invoices,
                          format_currency=format_currency)

@doctor_bp.route('/billing/create/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def create_invoice(appointment_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first_or_404()
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Make sure the appointment belongs to this doctor
    if appointment.doctor_id != doctor.id:
        flash('You do not have permission to create an invoice for this appointment.', 'danger')
        return redirect(url_for('doctor.billing'))
    
    # Check if invoice already exists
    existing_invoice = Invoice.query.filter_by(appointment_id=appointment.id).first()
    if existing_invoice:
        flash('An invoice already exists for this appointment.', 'warning')
        return redirect(url_for('doctor.billing'))
    
    # Get all services
    services = Service.query.all()
    
    if request.method == 'POST':
        # Create invoice
        invoice = Invoice(
            patient_id=appointment.patient_id,
            appointment_id=appointment.id,
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
        return redirect(url_for('doctor.billing'))
    
    return render_template('doctor/create_invoice.html',
                          doctor=doctor,
                          appointment=appointment,
                          services=services)
