from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, Doctor, Patient, Staff, Admin, Department, Service, Appointment, Invoice
from forms import DepartmentForm, ServiceForm, UserApprovalForm
from datetime import datetime, timedelta
from sqlalchemy import func
from utils.helpers import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get basic stats for dashboard
    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_staff = Staff.query.count()
    total_appointments = Appointment.query.count()
    
    # Get pending approval requests
    pending_doctors = Doctor.query.join(User).filter(User.is_approved == False).all()
    pending_staff = Staff.query.join(User).filter(User.is_approved == False).all()
    
    # Get recent appointments
    recent_appointments = Appointment.query.order_by(Appointment.start_time.desc()).limit(5).all()
    
    # Get appointment statistics
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_appointments = Appointment.query.filter(
        Appointment.start_time >= today_start,
        Appointment.start_time <= today_end
    ).count()
    
    # Get appointment data for last 7 days for chart
    last_7_days = []
    appointment_counts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        count = Appointment.query.filter(
            Appointment.start_time >= day_start,
            Appointment.start_time <= day_end
        ).count()
        
        last_7_days.append(day.strftime('%a'))
        appointment_counts.append(count)
    
    # Get revenue data (total amount from invoices)
    total_revenue = db.session.query(func.sum(Invoice.total_amount)).scalar() or 0
    
    # Get pending invoices
    pending_invoices = Invoice.query.filter(Invoice.status == 'pending').count()
    
    return render_template('admin/dashboard.html',
                          total_doctors=total_doctors,
                          total_patients=total_patients,
                          total_staff=total_staff,
                          total_appointments=total_appointments,
                          today_appointments=today_appointments,
                          pending_doctors=pending_doctors,
                          pending_staff=pending_staff,
                          recent_appointments=recent_appointments,
                          chart_labels=last_7_days,
                          chart_data=appointment_counts,
                          total_revenue=total_revenue,
                          pending_invoices=pending_invoices)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    doctors = Doctor.query.join(User).all()
    staff = Staff.query.join(User).all()
    patients = Patient.query.join(User).all()
    
    return render_template('admin/users.html', 
                          doctors=doctors,
                          staff=staff,
                          patients=patients)

@admin_bp.route('/approve-users', methods=['GET', 'POST'])
@login_required
@admin_required
def approve_users():
    pending_doctors = Doctor.query.join(User).filter(User.is_approved == False).all()
    pending_staff = Staff.query.join(User).filter(User.is_approved == False).all()
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')
        
        if user_id and action:
            user = User.query.get(user_id)
            
            if user:
                if action == 'approve':
                    user.is_approved = True
                    flash(f'User {user.username} has been approved.', 'success')
                elif action == 'reject':
                    # For reject, we could either delete the user or just keep them not approved
                    # Here we're keeping them but marking as inactive
                    user.is_active = False
                    flash(f'User {user.username} has been rejected.', 'warning')
                
                db.session.commit()
                return redirect(url_for('admin.approve_users'))
    
    return render_template('admin/approve_users.html', 
                          pending_doctors=pending_doctors,
                          pending_staff=pending_staff)

@admin_bp.route('/departments', methods=['GET', 'POST'])
@login_required
@admin_required
def departments():
    form = DepartmentForm()
    
    if form.validate_on_submit():
        department = Department(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(department)
        db.session.commit()
        flash('Department added successfully.', 'success')
        return redirect(url_for('admin.departments'))
    
    departments = Department.query.all()
    return render_template('admin/settings.html', 
                          form=form, 
                          departments=departments,
                          active_tab='departments')

@admin_bp.route('/services', methods=['GET', 'POST'])
@login_required
@admin_required
def services():
    form = ServiceForm()
    
    # Populate department choices
    departments = Department.query.all()
    form.department_id.choices = [(d.id, d.name) for d in departments]
    
    if form.validate_on_submit():
        service = Service(
            name=form.name.data,
            description=form.description.data,
            cost=form.cost.data,
            duration_minutes=form.duration_minutes.data,
            department_id=form.department_id.data
        )
        db.session.add(service)
        db.session.commit()
        flash('Service added successfully.', 'success')
        return redirect(url_for('admin.services'))
    
    services = Service.query.all()
    return render_template('admin/settings.html', 
                          form=form, 
                          services=services,
                          departments=departments,
                          active_tab='services')

@admin_bp.route('/edit-department/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_department(id):
    department = Department.query.get_or_404(id)
    form = DepartmentForm(obj=department)
    
    if form.validate_on_submit():
        department.name = form.name.data
        department.description = form.description.data
        db.session.commit()
        flash('Department updated successfully.', 'success')
        return redirect(url_for('admin.departments'))
    
    return render_template('admin/edit_department.html', form=form, department=department)

@admin_bp.route('/edit-service/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_service(id):
    service = Service.query.get_or_404(id)
    form = ServiceForm(obj=service)
    
    # Populate department choices
    departments = Department.query.all()
    form.department_id.choices = [(d.id, d.name) for d in departments]
    
    if form.validate_on_submit():
        service.name = form.name.data
        service.description = form.description.data
        service.cost = form.cost.data
        service.duration_minutes = form.duration_minutes.data
        service.department_id = form.department_id.data
        db.session.commit()
        flash('Service updated successfully.', 'success')
        return redirect(url_for('admin.services'))
    
    return render_template('admin/edit_service.html', form=form, service=service)

@admin_bp.route('/delete-department/<int:id>')
@login_required
@admin_required
def delete_department(id):
    department = Department.query.get_or_404(id)
    
    # Check if department has associated doctors or services
    if department.doctors.count() > 0 or department.services.count() > 0:
        flash('Cannot delete department as it has associated doctors or services.', 'danger')
    else:
        db.session.delete(department)
        db.session.commit()
        flash('Department deleted successfully.', 'success')
    
    return redirect(url_for('admin.departments'))

@admin_bp.route('/delete-service/<int:id>')
@login_required
@admin_required
def delete_service(id):
    service = Service.query.get_or_404(id)
    
    # Check if service has associated invoice items
    if service.invoice_items.count() > 0:
        flash('Cannot delete service as it has associated invoice items.', 'danger')
    else:
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted successfully.', 'success')
    
    return redirect(url_for('admin.services'))

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    # Get appointment statistics by doctor
    doctors = Doctor.query.all()
    doctor_stats = []
    
    for doctor in doctors:
        total_appointments = Appointment.query.filter_by(doctor_id=doctor.id).count()
        completed_appointments = Appointment.query.filter_by(doctor_id=doctor.id, status='completed').count()
        
        if total_appointments > 0:
            completion_rate = (completed_appointments / total_appointments) * 100
        else:
            completion_rate = 0
        
        doctor_stats.append({
            'name': doctor.full_name,
            'total': total_appointments,
            'completed': completed_appointments,
            'completion_rate': completion_rate
        })
    
    # Get revenue statistics
    total_revenue = db.session.query(func.sum(Invoice.total_amount)).scalar() or 0
    paid_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(Invoice.status == 'paid').scalar() or 0
    pending_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(Invoice.status == 'pending').scalar() or 0
    
    # Get revenue by month for current year
    current_year = datetime.now().year
    monthly_revenue = []
    
    for month in range(1, 13):
        start_date = datetime(current_year, month, 1)
        if month == 12:
            end_date = datetime(current_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(current_year, month + 1, 1) - timedelta(days=1)
        
        month_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
            Invoice.status == 'paid'
        ).scalar() or 0
        
        monthly_revenue.append({
            'month': start_date.strftime('%b'),
            'revenue': month_revenue
        })
    
    return render_template('admin/reports.html', 
                          doctor_stats=doctor_stats,
                          total_revenue=total_revenue,
                          paid_revenue=paid_revenue,
                          pending_revenue=pending_revenue,
                          monthly_revenue=monthly_revenue)

@admin_bp.route('/user/<int:id>/toggle-status')
@login_required
@admin_required
def toggle_user_status(id):
    user = User.query.get_or_404(id)
    
    # Toggle user status
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    
    return redirect(url_for('admin.users'))
