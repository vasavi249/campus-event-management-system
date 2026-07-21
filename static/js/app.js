/**
 * Campus Event Management System - Modern JavaScript Core Module
 */

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

window.toggleSpinner = function(show) {};

function showToast(message, type = 'success') {
    if (type === 'danger') type = 'error';
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `custom-toast ${type}`;
    toast.innerHTML = `
        <div class="d-flex align-items-center gap-2">
            <i class="bi ${type === 'success' ? 'bi-check-circle-fill text-success' : 'bi-exclamation-triangle-fill text-danger'}"></i>
            <span>${message}</span>
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.4s ease';
        setTimeout(() => toast.remove(), 400);
    }, 4000);
}

function parseAPIErrorMessage(json) {
    if (!json) return 'An error occurred. Please check input values.';
    if (typeof json === 'string') return json;
    if (json.message) return json.message;
    if (json.detail) return json.detail;
    if (json.error) return json.error;
    if (json.errors) {
        if (typeof json.errors === 'string') return json.errors;
        if (typeof json.errors === 'object') {
            return Object.entries(json.errors)
                .map(([field, errs]) => `${field}: ${Array.isArray(errs) ? errs.join(', ') : errs}`)
                .join(' | ');
        }
    }
    if (typeof json === 'object') {
        const parts = [];
        for (const [key, val] of Object.entries(json)) {
            if (Array.isArray(val)) {
                parts.push(`${key}: ${val.join(', ')}`);
            } else if (typeof val === 'string') {
                parts.push(`${key}: ${val}`);
            }
        }
        if (parts.length > 0) return parts.join(' | ');
    }
    return 'An error occurred. Please check input values.';
}

async function fetchAPI(url, options = {}) {
    const defaultHeaders = {
        'X-CSRFToken': getCookie('csrftoken') || ''
    };

    if (!(options.body instanceof FormData)) {
        defaultHeaders['Content-Type'] = 'application/json';
    }

    const token = localStorage.getItem('auth_token');
    if (token && !url.includes('/api/auth/register') && !url.includes('/users/add')) {
        defaultHeaders['Authorization'] = `Token ${token}`;
    }

    options.headers = { ...defaultHeaders, ...(options.headers || {}) };

    try {
        const response = await fetch(url, options);
        const json = await response.json().catch(() => ({ message: 'Server returned non-JSON response.' }));

        if (!response.ok) {
            const errMsg = parseAPIErrorMessage(json);
            showToast(errMsg, 'error');
            return { ok: false, status: response.status, data: json, errorMessage: errMsg };
        }

        return { ok: true, status: response.status, data: json };
    } catch (err) {
        console.error('Fetch error:', err);
        showToast('Network error or server unreachable.', 'error');
        return { ok: false, status: 500, error: err, errorMessage: 'Network error or server unreachable.' };
    }
}

async function registerForEvent(eventId) {
    const res = await fetchAPI('/api/registrations/', {
        method: 'POST',
        body: JSON.stringify({ event: eventId })
    });

    if (res.ok) {
        showToast(res.data.message || 'Successfully registered for event!', 'success');
        setTimeout(() => location.reload(), 1200);
    }
}

async function cancelRegistration(registrationId) {
    if (!confirm('Are you sure you want to cancel your event registration?')) return;

    const res = await fetchAPI(`/api/registrations/${registrationId}/cancel/`, {
        method: 'POST'
    });

    if (res.ok) {
        showToast('Registration cancelled.', 'success');
        setTimeout(() => location.reload(), 1000);
    }
}

async function approveEvent(eventId, statusChoice) {
    const res = await fetchAPI(`/api/events/${eventId}/approve/`, {
        method: 'POST',
        body: JSON.stringify({ approval_status: statusChoice })
    });

    if (res.ok) {
        showToast(`Event status updated to ${statusChoice}.`, 'success');
        setTimeout(() => location.reload(), 1000);
    }
}

function showDigitalPass(ticketCode, eventTitle, studentName, venueName, eventDate) {
    const modalHtml = `
        <div class="modal fade" id="ticketModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content glass-card border-primary">
                    <div class="modal-header border-0 pb-0">
                        <h5 class="modal-title fw-bold text-white"><i class="bi bi-qr-code-scan text-primary me-2"></i>Digital Event Pass</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body text-center p-4">
                        <div class="ticket-pass mb-3">
                            <h4 class="text-white fw-bold mb-1">${eventTitle}</h4>
                            <p class="text-info small mb-3"><i class="bi bi-geo-alt-fill me-1"></i>${venueName} | ${eventDate}</p>
                            
                            <div class="p-3 bg-white d-inline-block rounded-3 shadow mb-3">
                                <img src="https://quickchart.io/qr?text=${encodeURIComponent(ticketCode)}&size=160" alt="Ticket QR Code" width="160" height="160">
                            </div>
                            
                            <div class="text-uppercase tracking-wider fw-bold text-warning font-monospace fs-5">${ticketCode}</div>
                            <small class="text-light opacity-75 d-block mt-1">Attendee: ${studentName}</small>
                        </div>
                        <p class="text-muted small mb-0"><i class="bi bi-info-circle me-1"></i>Present this QR code or Ticket ID at the venue gate for check-in.</p>
                    </div>
                    <div class="modal-footer border-0 justify-content-center">
                        <button type="button" class="btn btn-glass-secondary btn-sm" onclick="window.print()"><i class="bi bi-printer me-1"></i>Print Pass</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const existing = document.getElementById('ticketModal');
    if (existing) existing.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const bsModal = new bootstrap.Modal(document.getElementById('ticketModal'));
    bsModal.show();
}

async function handleCheckinSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('ticket_code_input');
    const ticketCode = input.value.trim();

    if (!ticketCode) return;

    const res = await fetchAPI('/api/attendance/checkin/', {
        method: 'POST',
        body: JSON.stringify({ ticket_code: ticketCode })
    });

    if (res.ok) {
        showToast(res.data.message, 'success');
        input.value = '';
        setTimeout(() => location.reload(), 1200);
    }
}
