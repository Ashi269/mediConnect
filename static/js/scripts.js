/**
 * MediConnect Pro - Main JavaScript
 * 
 * Common JavaScript functions for the entire application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize all popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Flash message auto-dismissal
    var alertList = document.querySelectorAll('.alert');
    alertList.forEach(function(alert) {
        if (!alert.classList.contains('alert-persistent')) {
            setTimeout(function() {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000); // Close after 5 seconds
        }
    });
    
    // Confirmation dialogs
    document.querySelectorAll('[data-confirm]').forEach(function(element) {
        element.addEventListener('click', function(e) {
            if (!confirm(this.getAttribute('data-confirm'))) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // Table row highlighting on hover
    document.querySelectorAll('.table-hover tr').forEach(function(row) {
        row.addEventListener('mouseover', function() {
            this.classList.add('table-active');
        });
        
        row.addEventListener('mouseout', function() {
            this.classList.remove('table-active');
        });
    });
    
    // Toggle password visibility
    document.querySelectorAll('.toggle-password').forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            const target = document.querySelector(this.getAttribute('data-target'));
            if (target.type === 'password') {
                target.type = 'text';
                this.innerHTML = '<i class="fas fa-eye-slash"></i>';
            } else {
                target.type = 'password';
                this.innerHTML = '<i class="fas fa-eye"></i>';
            }
        });
    });
    
    // Enable date pickers
    document.querySelectorAll('input[type="date"]').forEach(function(datePicker) {
        if (datePicker.value === '') {
            // Don't set a default date unless specifically required
            // datePicker.valueAsDate = new Date();
        }
    });
    
    // Add current year to footer copyright text
    const currentYearElements = document.querySelectorAll('.current-year');
    const currentYear = new Date().getFullYear();
    currentYearElements.forEach(function(element) {
        element.textContent = currentYear;
    });
    
    // Form validation styles
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Auto-expand textareas
    document.querySelectorAll('textarea.auto-expand').forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        
        // Trigger once to adjust initial content
        textarea.dispatchEvent(new Event('input'));
    });
    
    // Dynamic lists with add/remove functionality
    if (document.querySelector('.dynamic-list-container')) {
        initDynamicLists();
    }
    
    // Invoice calculation helpers
    if (document.querySelector('.invoice-form')) {
        initInvoiceCalculator();
    }
});

/**
 * Initialize dynamic lists (like medication lists in prescriptions)
 */
function initDynamicLists() {
    // Add item buttons
    document.querySelectorAll('.btn-add-item').forEach(function(button) {
        button.addEventListener('click', function() {
            const container = document.querySelector(this.getAttribute('data-container'));
            const template = document.querySelector(this.getAttribute('data-template'));
            const clone = template.content.cloneNode(true);
            const itemCount = container.querySelectorAll('.dynamic-item').length;
            
            // Update IDs and names for new elements
            clone.querySelectorAll('[name]').forEach(function(element) {
                const name = element.getAttribute('name');
                element.setAttribute('name', name.replace('INDEX', itemCount));
                element.setAttribute('id', name.replace('INDEX', itemCount));
            });
            
            // Add remove button event listener
            const removeBtn = clone.querySelector('.btn-remove-item');
            if (removeBtn) {
                removeBtn.addEventListener('click', function() {
                    this.closest('.dynamic-item').remove();
                });
            }
            
            container.appendChild(clone);
        });
    });
    
    // Remove item buttons
    document.querySelectorAll('.btn-remove-item').forEach(function(button) {
        button.addEventListener('click', function() {
            this.closest('.dynamic-item').remove();
        });
    });
}

/**
 * Initialize invoice calculator
 */
function initInvoiceCalculator() {
    const invoiceItems = document.querySelector('.invoice-items');
    const totalElement = document.querySelector('.invoice-total');
    
    // Function to update totals
    function updateTotals() {
        let total = 0;
        document.querySelectorAll('.item-row').forEach(function(row) {
            const quantity = parseInt(row.querySelector('.item-quantity').value) || 0;
            const price = parseFloat(row.querySelector('.item-price').value) || 0;
            const itemTotal = quantity * price;
            
            row.querySelector('.item-total').textContent = itemTotal.toFixed(2);
            total += itemTotal;
        });
        
        totalElement.textContent = total.toFixed(2);
    }
    
    // Add listeners to all inputs
    document.querySelectorAll('.item-quantity, .item-price').forEach(function(input) {
        input.addEventListener('input', updateTotals);
    });
    
    // Add item button
    document.querySelector('.btn-add-invoice-item').addEventListener('click', function() {
        const template = document.querySelector('#invoice-item-template');
        const clone = template.content.cloneNode(true);
        
        // Add event listeners to new inputs
        clone.querySelectorAll('.item-quantity, .item-price').forEach(function(input) {
            input.addEventListener('input', updateTotals);
        });
        
        // Add remove button functionality
        clone.querySelector('.btn-remove-invoice-item').addEventListener('click', function() {
            this.closest('.item-row').remove();
            updateTotals();
        });
        
        invoiceItems.appendChild(clone);
    });
    
    // Remove item buttons
    document.querySelectorAll('.btn-remove-invoice-item').forEach(function(button) {
        button.addEventListener('click', function() {
            this.closest('.item-row').remove();
            updateTotals();
        });
    });
    
    // Initialize totals on page load
    updateTotals();
}
