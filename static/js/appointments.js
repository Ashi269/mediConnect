/**
 * MediConnect Pro - Appointments JavaScript
 * 
 * Handles appointment scheduling, time slot management,
 * and availability checking
 */

document.addEventListener('DOMContentLoaded', function() {
    const doctorSelect = document.getElementById('doctor_id');
    const dateInput = document.getElementById('date');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    const timeSlotsContainer = document.getElementById('time_slots');
    
    // Only initialize if we're on the appointment scheduling page
    if (doctorSelect && dateInput && timeSlotsContainer) {
        initAppointmentScheduler();
    }
    
    // Calendar view initialization (if available)
    const calendarEl = document.getElementById('appointment_calendar');
    if (calendarEl) {
        initAppointmentCalendar(calendarEl);
    }
});

/**
 * Initialize the appointment scheduler
 */
function initAppointmentScheduler() {
    const doctorSelect = document.getElementById('doctor_id');
    const dateInput = document.getElementById('date');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    const timeSlotsContainer = document.getElementById('time_slots');
    
    // Set minimum date to today
    const today = new Date();
    dateInput.min = today.toISOString().split('T')[0];
    
    // Handle doctor or date change to load available slots
    function loadAvailableSlots() {
        const doctorId = doctorSelect.value;
        const date = dateInput.value;
        
        if (!doctorId || !date) {
            return;
        }
        
        // Show loading state
        timeSlotsContainer.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
        
        // Fetch available slots
        fetch(`/appointments/get-slots?doctor_id=${doctorId}&date=${date}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    timeSlotsContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                    return;
                }
                
                // Display available slots
                if (data.available_slots.length === 0) {
                    timeSlotsContainer.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            No available slots for Dr. ${data.doctor_name} on ${formatDate(data.date)}.
                            Please select a different date.
                        </div>
                    `;
                } else {
                    timeSlotsContainer.innerHTML = `
                        <p class="mb-3">Available slots for Dr. ${data.doctor_name} on ${formatDate(data.date)}:</p>
                        <div class="row row-cols-2 row-cols-md-3 row-cols-lg-4 g-2" id="slots_grid"></div>
                    `;
                    
                    const slotsGrid = document.getElementById('slots_grid');
                    
                    data.available_slots.forEach(slot => {
                        const slotBtn = document.createElement('div');
                        slotBtn.className = 'col';
                        slotBtn.innerHTML = `
                            <button type="button" class="btn btn-outline-primary w-100 time-slot-btn"
                                data-start="${slot.start}" data-end="${slot.end}">
                                ${slot.formatted}
                            </button>
                        `;
                        slotsGrid.appendChild(slotBtn);
                    });
                    
                    // Add click handlers to slot buttons
                    document.querySelectorAll('.time-slot-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            // Remove active class from all buttons
                            document.querySelectorAll('.time-slot-btn').forEach(b => {
                                b.classList.remove('active', 'btn-primary');
                                b.classList.add('btn-outline-primary');
                            });
                            
                            // Add active class to clicked button
                            this.classList.remove('btn-outline-primary');
                            this.classList.add('active', 'btn-primary');
                            
                            // Update time inputs
                            startTimeInput.value = this.dataset.start;
                            endTimeInput.value = this.dataset.end;
                        });
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching slots:', error);
                timeSlotsContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Failed to load available slots. Please try again.
                    </div>
                `;
            });
    }
    
    // Format date for display
    function formatDate(dateString) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }
    
    // Event listeners
    doctorSelect.addEventListener('change', loadAvailableSlots);
    dateInput.addEventListener('change', loadAvailableSlots);
    
    // Load initial slots if values are preset
    if (doctorSelect.value && dateInput.value) {
        loadAvailableSlots();
    }
}

/**
 * Initialize the appointment calendar (for doctor/staff dashboards)
 * @param {HTMLElement} calendarEl - Calendar container element
 */
function initAppointmentCalendar(calendarEl) {
    // This would use a calendar library like FullCalendar.js
    // For this implementation, we'll just create a simplified version
    
    const currentDate = new Date();
    const currentMonth = currentDate.getMonth();
    const currentYear = currentDate.getFullYear();
    
    // Get appointments data from a data attribute
    const appointmentsData = JSON.parse(calendarEl.dataset.appointments || '[]');
    
    // Create a simple calendar with the current month
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                        'July', 'August', 'September', 'October', 'November', 'December'];
    
    // Create calendar header
    let calendarHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <button class="btn btn-sm btn-outline-primary" id="prev-month">
                <i class="fas fa-chevron-left"></i>
            </button>
            <h5 class="mb-0" id="calendar-month">${monthNames[currentMonth]} ${currentYear}</h5>
            <button class="btn btn-sm btn-outline-primary" id="next-month">
                <i class="fas fa-chevron-right"></i>
            </button>
        </div>
    `;
    
    // Create calendar grid
    calendarHTML += `
        <div class="calendar-grid">
            <div class="calendar-header">
                <div>Sun</div>
                <div>Mon</div>
                <div>Tue</div>
                <div>Wed</div>
                <div>Thu</div>
                <div>Fri</div>
                <div>Sat</div>
            </div>
            <div class="calendar-body" id="calendar-body"></div>
        </div>
    `;
    
    // Render the calendar
    calendarEl.innerHTML = calendarHTML;
    
    // Populate the calendar with days
    updateCalendarDays(currentMonth, currentYear, appointmentsData);
    
    // Event listeners for navigation
    document.getElementById('prev-month').addEventListener('click', function() {
        let month = parseInt(document.getElementById('calendar-month').dataset.month || currentMonth);
        let year = parseInt(document.getElementById('calendar-month').dataset.year || currentYear);
        
        month--;
        if (month < 0) {
            month = 11;
            year--;
        }
        
        document.getElementById('calendar-month').textContent = `${monthNames[month]} ${year}`;
        document.getElementById('calendar-month').dataset.month = month;
        document.getElementById('calendar-month').dataset.year = year;
        
        updateCalendarDays(month, year, appointmentsData);
    });
    
    document.getElementById('next-month').addEventListener('click', function() {
        let month = parseInt(document.getElementById('calendar-month').dataset.month || currentMonth);
        let year = parseInt(document.getElementById('calendar-month').dataset.year || currentYear);
        
        month++;
        if (month > 11) {
            month = 0;
            year++;
        }
        
        document.getElementById('calendar-month').textContent = `${monthNames[month]} ${year}`;
        document.getElementById('calendar-month').dataset.month = month;
        document.getElementById('calendar-month').dataset.year = year;
        
        updateCalendarDays(month, year, appointmentsData);
    });
}

/**
 * Update calendar days for the specified month
 * @param {number} month - Month (0-11)
 * @param {number} year - Year
 * @param {Array} appointments - Appointments data
 */
function updateCalendarDays(month, year, appointments) {
    const calendarBody = document.getElementById('calendar-body');
    if (!calendarBody) return;
    
    calendarBody.innerHTML = '';
    
    // Get first day of the month
    const firstDay = new Date(year, month, 1).getDay();
    
    // Get last day of the month
    const lastDay = new Date(year, month + 1, 0).getDate();
    
    // Get today's date for highlighting
    const today = new Date();
    const isCurrentMonth = today.getMonth() === month && today.getFullYear() === year;
    
    // Create the calendar days
    let date = 1;
    let dayElement;
    
    // Create empty cells for days before the first of the month
    for (let i = 0; i < firstDay; i++) {
        dayElement = document.createElement('div');
        dayElement.className = 'calendar-day empty';
        calendarBody.appendChild(dayElement);
    }
    
    // Create cells for days in the month
    while (date <= lastDay) {
        dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        dayElement.textContent = date;
        
        // Highlight today
        if (isCurrentMonth && date === today.getDate()) {
            dayElement.classList.add('today');
        }
        
        // Check for appointments on this day
        const currentDate = new Date(year, month, date);
        const dayAppointments = appointments.filter(appt => {
            const apptDate = new Date(appt.start_time);
            return apptDate.getDate() === date && 
                   apptDate.getMonth() === month && 
                   apptDate.getFullYear() === year;
        });
        
        // Add indicator dot for appointments
        if (dayAppointments.length > 0) {
            dayElement.classList.add('has-appointments');
            dayElement.setAttribute('data-bs-toggle', 'tooltip');
            dayElement.setAttribute('data-bs-placement', 'top');
            dayElement.setAttribute('title', `${dayAppointments.length} appointments`);
            
            const indicator = document.createElement('span');
            indicator.className = 'appointment-indicator';
            indicator.textContent = dayAppointments.length;
            dayElement.appendChild(indicator);
            
            // Make the day clickable to show appointments
            dayElement.style.cursor = 'pointer';
            dayElement.addEventListener('click', function() {
                showDayAppointments(currentDate, dayAppointments);
            });
        }
        
        calendarBody.appendChild(dayElement);
        date++;
    }
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Show appointments for a specific day in a modal
 * @param {Date} date - The date
 * @param {Array} appointments - Appointments for the day
 */
function showDayAppointments(date, appointments) {
    // Format the date
    const dateString = date.toLocaleDateString(undefined, { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    
    // Create modal content
    let modalContent = `
        <div class="modal-header">
            <h5 class="modal-title">Appointments for ${dateString}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
    `;
    
    if (appointments.length > 0) {
        modalContent += '<div class="list-group">';
        
        // Sort appointments by time
        appointments.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
        
        appointments.forEach(appt => {
            const startTime = new Date(appt.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const endTime = new Date(appt.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            let statusBadge = '';
            if (appt.status === 'scheduled') {
                statusBadge = '<span class="badge bg-warning text-dark">Scheduled</span>';
            } else if (appt.status === 'completed') {
                statusBadge = '<span class="badge bg-success">Completed</span>';
            } else if (appt.status === 'cancelled') {
                statusBadge = '<span class="badge bg-danger">Cancelled</span>';
            } else if (appt.status === 'no-show') {
                statusBadge = '<span class="badge bg-secondary">No Show</span>';
            }
            
            modalContent += `
                <div class="list-group-item">
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1">${startTime} - ${endTime}</h6>
                        ${statusBadge}
                    </div>
                    <p class="mb-1">
                        <strong>Patient:</strong> ${appt.patient_name}
                        <br>
                        <strong>Doctor:</strong> Dr. ${appt.doctor_name}
                    </p>
                    <p class="mb-1 small text-muted">${appt.reason}</p>
                    <a href="/appointments/${appt.id}" class="btn btn-sm btn-outline-primary mt-2">View Details</a>
                </div>
            `;
        });
        
        modalContent += '</div>';
    } else {
        modalContent += '<p class="text-center py-3">No appointments for this day.</p>';
    }
    
    modalContent += `
        </div>
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            <a href="/appointments/new?date=${date.toISOString().split('T')[0]}" class="btn btn-primary">
                <i class="fas fa-plus me-1"></i> New Appointment
            </a>
        </div>
    `;
    
    // Create modal element
    let modalEl = document.getElementById('day-appointments-modal');
    if (!modalEl) {
        modalEl = document.createElement('div');
        modalEl.className = 'modal fade';
        modalEl.id = 'day-appointments-modal';
        modalEl.tabIndex = '-1';
        modalEl.setAttribute('aria-labelledby', 'day-appointments-modal-label');
        modalEl.setAttribute('aria-hidden', 'true');
        
        modalEl.innerHTML = `
            <div class="modal-dialog modal-dialog-scrollable">
                <div class="modal-content" id="day-appointments-modal-content"></div>
            </div>
        `;
        
        document.body.appendChild(modalEl);
    }
    
    // Set modal content
    document.getElementById('day-appointments-modal-content').innerHTML = modalContent;
    
    // Show modal
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}
