from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, DateField, TimeField, FloatField, IntegerField, BooleanField, HiddenField, RadioField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from datetime import datetime

# Authentication and Registration Forms
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('doctor', 'Doctor'), ('patient', 'Patient')])
    submit = SubmitField('Register')

class DoctorRegistrationForm(RegistrationForm):
    specialty = StringField('Specialty', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired()])
    license_number = StringField('License Number', validators=[DataRequired()])
    bio = TextAreaField('Bio', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(DoctorRegistrationForm, self).__init__(*args, **kwargs)
        self.role.data = 'doctor'

class PatientRegistrationForm(RegistrationForm):
    date_of_birth = DateField('Date of Birth', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    phone = StringField('Phone', validators=[DataRequired()])
    address = TextAreaField('Address', validators=[Optional()])
    blood_type = SelectField('Blood Type', choices=[
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')
    ], validators=[Optional()])
    allergies = TextAreaField('Allergies', validators=[Optional()])
    emergency_contact_name = StringField('Emergency Contact Name', validators=[Optional()])
    emergency_contact_phone = StringField('Emergency Contact Phone', validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(PatientRegistrationForm, self).__init__(*args, **kwargs)
        self.role.data = 'patient'

class StaffRegistrationForm(RegistrationForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    position = SelectField('Position', choices=[
        ('receptionist', 'Receptionist'),
        ('nurse', 'Nurse'),
        ('assistant', 'Medical Assistant')
    ])
    phone = StringField('Phone', validators=[DataRequired()])
    address = TextAreaField('Address', validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(StaffRegistrationForm, self).__init__(*args, **kwargs)
        self.role.data = 'staff'

# Profile Update Forms
class UserUpdateForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired()])
    submit = SubmitField('Update Profile')

class DoctorUpdateForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    specialty = StringField('Specialty', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired()])
    address = TextAreaField('Address', validators=[Optional()])
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    bio = TextAreaField('Bio', validators=[Optional()])
    license_number = StringField('License Number', validators=[DataRequired()])
    submit = SubmitField('Update Profile')

class PatientUpdateForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    date_of_birth = DateField('Date of Birth', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    phone = StringField('Phone', validators=[DataRequired()])
    address = TextAreaField('Address', validators=[Optional()])
    blood_type = SelectField('Blood Type', choices=[
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')
    ], validators=[Optional()])
    allergies = TextAreaField('Allergies', validators=[Optional()])
    emergency_contact_name = StringField('Emergency Contact Name', validators=[Optional()])
    emergency_contact_phone = StringField('Emergency Contact Phone', validators=[Optional()])
    submit = SubmitField('Update Profile')

class StaffUpdateForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    position = SelectField('Position', choices=[
        ('receptionist', 'Receptionist'),
        ('nurse', 'Nurse'),
        ('assistant', 'Medical Assistant')
    ])
    phone = StringField('Phone', validators=[DataRequired()])
    address = TextAreaField('Address', validators=[Optional()])
    assigned_doctor_id = SelectField('Assigned Doctor', coerce=int, validators=[Optional()])
    submit = SubmitField('Update Profile')

# Appointment Forms
class AppointmentForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Doctor', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    reason = TextAreaField('Reason for Visit', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Schedule Appointment')

    def validate_end_time(self, end_time):
        if self.start_time.data and end_time.data:
            if end_time.data <= self.start_time.data:
                raise ValidationError('End time must be after start time')

class AppointmentStatusForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no-show', 'No Show')
    ])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Update Status')

# Prescription Forms
class PrescriptionForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    diagnosis = TextAreaField('Diagnosis', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Prescription')

class MedicationForm(FlaskForm):
    name = StringField('Medication Name', validators=[DataRequired()])
    dosage = StringField('Dosage', validators=[DataRequired()])
    frequency = StringField('Frequency', validators=[DataRequired()])
    duration = StringField('Duration', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Add Medication')

# Medical Record Forms
class MedicalRecordForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    chief_complaint = TextAreaField('Chief Complaint', validators=[DataRequired()])
    diagnosis = TextAreaField('Diagnosis', validators=[DataRequired()])
    treatment_plan = TextAreaField('Treatment Plan', validators=[DataRequired()])
    vital_signs = TextAreaField('Vital Signs', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Medical Record')

# Invoice Forms
class InvoiceForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    appointment_id = SelectField('Related Appointment', coerce=int, validators=[Optional()])
    due_date = DateField('Due Date', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Create Invoice')

class InvoiceItemForm(FlaskForm):
    service_id = SelectField('Service', coerce=int, validators=[Optional()])
    description = StringField('Description', validators=[DataRequired()])
    quantity = IntegerField('Quantity', default=1, validators=[DataRequired()])
    unit_price = FloatField('Unit Price', validators=[DataRequired()])
    submit = SubmitField('Add Item')

# Admin Forms
class DepartmentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Department')

class ServiceForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    cost = FloatField('Cost', validators=[DataRequired()])
    duration_minutes = IntegerField('Duration (minutes)', validators=[Optional()])
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Service')

class UserApprovalForm(FlaskForm):
    user_id = HiddenField('User ID')
    approve = BooleanField('Approve')
    submit = SubmitField('Save')

# Search Forms
class PatientSearchForm(FlaskForm):
    search = StringField('Search Patients', validators=[Optional()])
    submit = SubmitField('Search')

class DoctorSearchForm(FlaskForm):
    search = StringField('Search Doctors', validators=[Optional()])
    specialty = SelectField('Specialty', validators=[Optional()])
    submit = SubmitField('Search')
