from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Doctor, Appointment
from datetime import datetime, timedelta
from utils.helpers import is_authorized

appointments_bp = Blueprint('appointments', __name__)

@appointments_bp.route('/get-slots', methods=['GET'])
@login_required
def get_available_slots():
    doctor_id = request.args.get('doctor_id')
    date_str = request.args.get('date')
    
    if not doctor_id or not date_str:
        return jsonify({'error': 'Missing parameters'}), 400
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Get all appointments for the doctor on this date
    doctor = Doctor.query.get_or_404(doctor_id)
    
    # Start and end time of the working day (e.g., 8 AM to 5 PM)
    start_hour = 8
    end_hour = 17
    
    # Duration of each slot in minutes
    slot_duration = 30
    
    # Generate all possible time slots for the day
    all_slots = []
    current_time = datetime.combine(date, datetime.min.time().replace(hour=start_hour))
    end_time = datetime.combine(date, datetime.min.time().replace(hour=end_hour))
    
    while current_time < end_time:
        slot_end = current_time + timedelta(minutes=slot_duration)
        all_slots.append({
            'start': current_time.strftime('%H:%M'),
            'end': slot_end.strftime('%H:%M'),
            'formatted': f"{current_time.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}"
        })
        current_time = slot_end
    
    # Get booked appointments for the day
    start_of_day = datetime.combine(date, datetime.min.time())
    end_of_day = datetime.combine(date, datetime.max.time())
    
    booked_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.start_time >= start_of_day,
        Appointment.start_time <= end_of_day,
        Appointment.status != 'cancelled'
    ).all()
    
    # Mark booked slots
    available_slots = []
    for slot in all_slots:
        slot_start = datetime.strptime(f"{date_str} {slot['start']}", '%Y-%m-%d %H:%M')
        slot_end = datetime.strptime(f"{date_str} {slot['end']}", '%Y-%m-%d %H:%M')
        
        is_booked = False
        for appt in booked_appointments:
            if (slot_start < appt.end_time and slot_end > appt.start_time):
                is_booked = True
                break
        
        if not is_booked:
            available_slots.append(slot)
    
    return jsonify({
        'doctor_name': doctor.full_name,
        'date': date_str,
        'available_slots': available_slots
    })

@appointments_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    
    # Check if user has permission to cancel this appointment
    if not is_authorized(current_user, appointment, 'cancel'):
        flash('You do not have permission to cancel this appointment.', 'danger')
        return redirect(url_for('home'))
    
    # Check if appointment can be cancelled (not already completed or cancelled)
    if appointment.status in ['completed', 'cancelled']:
        flash('This appointment cannot be cancelled.', 'danger')
    else:
        appointment.status = 'cancelled'
        appointment.notes = appointment.notes + '\n\nCancelled by ' + current_user.username + ' at ' + datetime.now().strftime('%Y-%m-%d %H:%M')
        db.session.commit()
        flash('Appointment cancelled successfully.', 'success')
    
    # Redirect based on user role
    if current_user.role == 'patient':
        return redirect(url_for('patient.appointments'))
    elif current_user.role == 'doctor':
        return redirect(url_for('doctor.appointments'))
    elif current_user.role == 'staff':
        return redirect(url_for('staff.appointments'))
    else:
        return redirect(url_for('home'))
