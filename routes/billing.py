from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from app import db
from models import Invoice, InvoiceItem, Patient, Appointment, Service
from datetime import datetime, timedelta
from utils.helpers import admin_required, doctor_required, staff_required, format_currency
import json
from io import BytesIO
# Temporarily comment out pdfkit import
# import pdfkit

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/')
@login_required
def index():
    # Redirect based on user role
    if current_user.role == 'admin':
        return redirect(url_for('admin.reports'))
    elif current_user.role == 'doctor':
        return redirect(url_for('doctor.billing'))
    elif current_user.role == 'staff':
        return redirect(url_for('staff.invoices'))
    elif current_user.role == 'patient':
        return redirect(url_for('patient.invoices'))
    else:
        flash('You do not have permission to access billing.', 'danger')
        return redirect(url_for('home'))

@billing_bp.route('/invoice/<int:id>')
@login_required
def view_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    
    # Check if user has permission to view this invoice
    if current_user.role == 'admin':
        # Admin can view all invoices
        pass
    elif current_user.role == 'doctor':
        # Doctor can view invoices for their appointments
        doctor_id = current_user.doctor.id if hasattr(current_user, 'doctor') and current_user.doctor else None
        if not doctor_id or (invoice.appointment and invoice.appointment.doctor_id != doctor_id):
            flash('You do not have permission to view this invoice.', 'danger')
            return redirect(url_for('doctor.billing'))
    elif current_user.role == 'staff':
        # Staff can view all invoices
        pass
    elif current_user.role == 'patient':
        # Patient can only view their own invoices
        patient_id = current_user.patient.id if hasattr(current_user, 'patient') and current_user.patient else None
        if not patient_id or invoice.patient_id != patient_id:
            flash('You do not have permission to view this invoice.', 'danger')
            return redirect(url_for('patient.invoices'))
    
    return render_template('billing/invoice.html', 
                          invoice=invoice,
                          format_currency=format_currency)

@billing_bp.route('/invoice/<int:id>/download')
@login_required
def download_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    
    # Check if user has permission to download this invoice
    if current_user.role == 'admin':
        # Admin can download all invoices
        pass
    elif current_user.role == 'doctor':
        # Doctor can download invoices for their appointments
        doctor_id = current_user.doctor.id if hasattr(current_user, 'doctor') and current_user.doctor else None
        if not doctor_id or (invoice.appointment and invoice.appointment.doctor_id != doctor_id):
            flash('You do not have permission to download this invoice.', 'danger')
            return redirect(url_for('doctor.billing'))
    elif current_user.role == 'staff':
        # Staff can download all invoices
        pass
    elif current_user.role == 'patient':
        # Patient can only download their own invoices
        patient_id = current_user.patient.id if hasattr(current_user, 'patient') and current_user.patient else None
        if not patient_id or invoice.patient_id != patient_id:
            flash('You do not have permission to download this invoice.', 'danger')
            return redirect(url_for('patient.invoices'))
    
    # Generate PDF using HTML template
    html = render_template('billing/invoice_pdf.html', 
                          invoice=invoice,
                          format_currency=format_currency)
    
    # In a real production environment, you would use wkhtmltopdf
    # For this implementation, we'll just return the HTML content
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice.id}.html'
    
    return response

@billing_bp.route('/invoice/<int:id>/update-status', methods=['POST'])
@login_required
def update_invoice_status(id):
    invoice = Invoice.query.get_or_404(id)
    
    # Check if user has permission to update this invoice
    if current_user.role not in ['admin', 'staff']:
        flash('You do not have permission to update invoice status.', 'danger')
        return redirect(url_for('billing.view_invoice', id=id))
    
    new_status = request.form.get('status')
    if new_status in ['pending', 'paid', 'cancelled', 'overdue']:
        invoice.status = new_status
        db.session.commit()
        flash(f'Invoice status updated to {new_status}.', 'success')
    
    return redirect(url_for('billing.view_invoice', id=id))
