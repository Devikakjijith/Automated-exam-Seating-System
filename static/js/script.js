/**
 * Main JavaScript file for common functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length > 0) {
        setTimeout(() => {
            flashMessages.forEach(msg => {
                msg.style.opacity = '0';
                setTimeout(() => {
                    msg.remove();
                }, 500);
            });
        }, 5000);
    }
    
    // PDF Generation functionality (if needed)
    if (typeof generatePDF === 'function') {
        // PDF generation functions are defined in individual templates
    }
    
    // Form validations
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Get all required inputs
            const requiredInputs = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredInputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    // Add error styling
                    input.style.borderColor = 'rgba(255, 0, 0, 0.5)';
                    input.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
                    
                    // Reset styling on input
                    input.addEventListener('input', function() {
                        input.style.borderColor = 'rgba(255, 255, 255, 0.3)';
                        input.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                    }, { once: true });
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                // Display error message (if not already present)
                const errorMsgExists = form.querySelector('.form-error-message');
                if (!errorMsgExists) {
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'form-error-message';
                    errorMsg.textContent = 'Please fill in all required fields.';
                    errorMsg.style.color = '#ff4444';
                    errorMsg.style.textAlign = 'center';
                    errorMsg.style.marginTop = '10px';
                    form.appendChild(errorMsg);
                    
                    // Remove message on next input
                    form.addEventListener('input', function() {
                        const msg = form.querySelector('.form-error-message');
                        if (msg) msg.remove();
                    }, { once: true });
                }
            }
        });
    });
    
    // Room selection in seating page
    const roomButtons = document.querySelectorAll('.room-button');
    if (roomButtons.length > 0) {
        const roomDetails = document.querySelectorAll('.room-detail');
        
        // Show first room by default
        if (roomButtons.length > 0 && roomDetails.length > 0) {
            roomButtons[0].classList.add('active');
            document.getElementById('room-' + roomButtons[0].dataset.room).classList.add('active');
        }
        
        // Add click handlers
        roomButtons.forEach(button => {
            button.addEventListener('click', function() {
                const roomId = this.dataset.room;
                
                // Remove active class from all buttons and details
                roomButtons.forEach(btn => btn.classList.remove('active'));
                roomDetails.forEach(detail => detail.classList.remove('active'));
                
                // Add active class to clicked button and corresponding detail
                this.classList.add('active');
                document.getElementById('room-' + roomId).classList.add('active');
            });
        });
    }
});

/**
 * Generate PDF from HTML content
 * @param {string} elementId - The ID of the element to convert to PDF
 * @param {string} filename - The filename for the PDF
 */
function generateGenericPDF(elementId, filename = 'download.pdf') {
    // Make sure the libraries are loaded
    if (typeof html2canvas === 'undefined' || typeof jspdf === 'undefined') {
        console.error('PDF generation libraries not loaded');
        return;
    }

    const element = document.getElementById(elementId);
    if (!element) {
        console.error('Element not found:', elementId);
        return;
    }
    
    // Create a clone of the element to modify for PDF
    const clone = element.cloneNode(true);
    
    // Style the clone for PDF
    clone.style.background = 'white';
    clone.style.color = 'black';
    clone.style.padding = '20px';
    
    // Change all text to black for better visibility in PDF
    const allElements = clone.querySelectorAll('*');
    allElements.forEach(el => {
        el.style.color = 'black';
        if (el.tagName === 'TABLE') {
            el.style.border = '1px solid #ddd';
        }
        if (el.tagName === 'TH' || el./**
 * Seatify - Main JavaScript file
 * Contains common functions used across the application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 5000);
    });

    // Add validation for file uploads
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const fileExtension = file.name.split('.').pop().toLowerCase();
                if (!['xlsx', 'xls'].includes(fileExtension)) {
                    alert('Please select a valid Excel file (.xlsx or .xls)');
                    this.value = ''; // Clear the file input
                }
            }
        });
    });

    // Initialize date inputs to today's date if they don't have a value
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];
    
    dateInputs.forEach(input => {
        if (!input.value) {
            input.value = today;
        }
    });

    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});

/**
 * Generate PDF from an HTML element
 * @param {string} elementId - The ID of the HTML element to convert
 * @param {string} filename - The filename for the PDF
 */
function generatePDF(elementId, filename) {
    const element = document.getElementById(elementId);
    
    if (!element) {
        console.error('Element not found:', elementId);
        return;
    }
    
    // Style for PDF
    const clone = element.cloneNode(true);
    clone.style.background = 'white';
    clone.style.color = 'black';
    clone.style.padding = '20px';
    
    // Change all text to black for better visibility in PDF
    const allElements = clone.querySelectorAll('*');
    allElements.forEach(el => {
        el.style.color = 'black';
        if (el.tagName === 'TABLE') {
            el.style.border = '1px solid #ddd';
        }
        if (el.tagName === 'TH' || el.tagName === 'TD') {
            el.style.border = '1px solid #ddd';
            el.style.background = '#f9f9f9';
        }
    });
    
    // Remove buttons and actions
    const buttons = clone.querySelectorAll('button, .actions');
    buttons.forEach(button => {
        if (button.parentNode) {
            button.parentNode.removeChild(button);
        }
    });
    
    // Temporarily add to document for html2canvas
    clone.style.position = 'absolute';
    clone.style.left = '-9999px';
    document.body.appendChild(clone);
    
    // Generate PDF
    html2canvas(clone).then(canvas => {
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jspdf.jsPDF('p', 'mm', 'a4');
        const width = pdf.internal.pageSize.getWidth();
        const height = canvas.height * width / canvas.width;
        
        pdf.addImage(imgData, 'PNG', 0, 0, width, height);
        pdf.save(filename);
        
        // Clean up
        document.body.removeChild(clone);
    });
}

/**
 * Toggle visibility of an element
 * @param {string} elementId - The ID of the element to toggle
 */
function toggleElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        if (element.style.display === 'none' || element.style.display === '') {
            element.style.display = 'block';
        } else {
            element.style.display = 'none';
        }
    }
}

/**
 * Confirm action with a custom message
 * @param {string} message - The confirmation message
 * @param {function} callback - The function to call if confirmed
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}
