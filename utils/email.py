import logging
from flask import render_template
from app import mail
from flask_mail import Message

logger = logging.getLogger(__name__)

def send_email(subject, recipients, text_body, html_body=None, sender=None):
    """
    Send an email with the given parameters
    """
    try:
        msg = Message(subject, recipients=recipients, sender=sender)
        msg.body = text_body
        if html_body:
            msg.html = html_body
        mail.send(msg)
        logger.info(f"Email sent to {recipients} with subject '{subject}'")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False


def send_registration_email(user, role):
    """
    Send a registration confirmation email to a user
    """
    subject = f"MediConnect Pro - Registration Confirmation"
    recipients = [user.email]
    
    if role == 'doctor':
        msg_body = f"""
            Dear Dr. {user.doctor.last_name},
            
            Thank you for registering with MediConnect Pro as a doctor. Your account is pending approval from our administration team.
            You will be notified via email once your account has been approved.
            
            Your username: {user.username}
            
            Regards,
            MediConnect Pro Team
        """
    elif role == 'patient':
        msg_body = f"""
            Dear {user.patient.first_name} {user.patient.last_name},
            
            Thank you for registering with MediConnect Pro. Your patient account has been created successfully.
            You can now log in to access our services.
            
            Your username: {user.username}
            
            Regards,
            MediConnect Pro Team
        """
    elif role == 'staff':
        msg_body = f"""
            Dear {user.staff.first_name} {user.staff.last_name},
            
            Thank you for joining MediConnect Pro as a staff member. Your account has been created.
            
            Your username: {user.username}
            
            Regards,
            MediConnect Pro Team
        """
    else:
        msg_body = f"""
            Thank you for registering with MediConnect Pro.
            Your username: {user.username}
            
            Regards,
            MediConnect Pro Team
        """
    
    # For now, we'll use a simple text email
    # In a production environment, you would use HTML templates
    return send_email(subject, recipients, msg_body)


def send_appointment_notification(appointment, notification_type='confirmation', recipient=None):
    """
    Send appointment-related notifications
    Types: confirmation, reminder, cancellation, rescheduled
    """
    doctor_name = f"Dr. {appointment.doctor.last_name}"
    patient_name = f"{appointment.patient.first_name} {appointment.patient.last_name}"
    appt_date = appointment.start_time.strftime('%A, %B %d, %Y')
    appt_time = appointment.start_time.strftime('%I:%M %p')
    
    recipients = []
    
    # Determine recipient(s)
    if recipient == 'doctor':
        recipients = [appointment.doctor.user.email]
    elif recipient == 'patient':
        recipients = [appointment.patient.user.email]
    elif recipient == 'both' or recipient is None:
        recipients = [appointment.doctor.user.email, appointment.patient.user.email]
    
    if notification_type == 'confirmation':
        subject = f"Appointment Confirmation - {appt_date}"
        msg_body = f"""
            Appointment Confirmation
            
            Patient: {patient_name}
            Doctor: {doctor_name}
            Date: {appt_date}
            Time: {appt_time}
            Reason: {appointment.reason}
            
            Thank you for scheduling with MediConnect Pro.
            If you need to reschedule or cancel, please contact us at least 24 hours in advance.
        """
    elif notification_type == 'reminder':
        subject = f"Appointment Reminder - {appt_date}"
        msg_body = f"""
            Appointment Reminder
            
            This is a reminder about your upcoming appointment:
            
            Patient: {patient_name}
            Doctor: {doctor_name}
            Date: {appt_date}
            Time: {appt_time}
            
            Please arrive 15 minutes before your appointment time.
            If you need to reschedule or cancel, please contact us as soon as possible.
        """
    elif notification_type == 'cancellation':
        subject = f"Appointment Cancellation - {appt_date}"
        msg_body = f"""
            Appointment Cancellation
            
            The following appointment has been cancelled:
            
            Patient: {patient_name}
            Doctor: {doctor_name}
            Date: {appt_date}
            Time: {appt_time}
            
            If you did not request this cancellation or wish to reschedule,
            please contact our office.
        """
    elif notification_type == 'rescheduled':
        subject = f"Appointment Rescheduled - {appt_date}"
        msg_body = f"""
            Appointment Rescheduled
            
            Your appointment has been rescheduled to:
            
            Patient: {patient_name}
            Doctor: {doctor_name}
            Date: {appt_date}
            Time: {appt_time}
            
            If this new time does not work for you, please contact our office.
        """
    else:
        logger.error(f"Unknown notification type: {notification_type}")
        return False
    
    return send_email(subject, recipients, msg_body)


def send_password_reset_email(user, reset_token):
    """
    Send a password reset email with a token link
    """
    subject = "MediConnect Pro - Password Reset"
    recipients = [user.email]
    
    # This token URL would be generated in your password reset route
    reset_url = f"https://mediconnect.example.com/reset-password/{reset_token}"
    
    msg_body = f"""
        Password Reset Request
        
        You recently requested to reset your password for your MediConnect Pro account.
        Click the link below to reset it:
        
        {reset_url}
        
        If you did not request a password reset, please ignore this email or contact support
        if you have questions.
        
        This password reset link is only valid for 30 minutes.
        
        Regards,
        MediConnect Pro Team
    """
    
    return send_email(subject, recipients, msg_body)