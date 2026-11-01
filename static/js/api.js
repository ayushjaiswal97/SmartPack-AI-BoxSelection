/**
 * PackSmart Enterprise REST API & UI Helper Client
 *
 * Provides a unified, robust fetch() wrapper supporting CSRF token injection,
 * status code handling (400, 401, 403, 404, 409, 500), network failure recovery,
 * loading state management, duplicate submission prevention, and form error mapping.
 */

class APIError extends Error {
    constructor(status, message, data = {}) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
        this.detail = data.detail || message;
        this.errors = data.errors || {};
    }
}

const PackSmartAPI = (function () {
    'use strict';

    // Extract CSRF token from cookie or DOM
    function getCsrfToken() {
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input && input.value) {
            return input.value;
        }

        const cookies = document.cookie ? document.cookie.split(';') : [];
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                return decodeURIComponent(cookie.substring('csrftoken='.length));
            }
        }
        return '';
    }

    /**
     * Core Fetch Wrapper
     */
    async function request(url, options = {}) {
        const method = (options.method || 'GET').toUpperCase();
        const headers = {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            ...(options.headers || {})
        };

        // Attach CSRF token on unsafe requests
        if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
            const csrf = getCsrfToken();
            if (csrf) {
                headers['X-CSRFToken'] = csrf;
            }
        }

        // Handle JSON payloads
        let body = options.body;
        if (body && typeof body === 'object' && !(body instanceof FormData) && !(body instanceof URLSearchParams)) {
            headers['Content-Type'] = 'application/json';
            body = JSON.stringify(body);
        }

        const fetchOptions = {
            ...options,
            method,
            headers,
            body
        };

        let response;
        try {
            response = await fetch(url, fetchOptions);
        } catch (networkError) {
            // Handle offline or network failure
            const errorMsg = 'Network connectivity failure. Unable to contact the warehouse server.';
            ui.showToast(errorMsg, 'danger');
            throw new APIError(0, errorMsg, { detail: networkError.message });
        }

        // Parse response body safely
        let data = {};
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            try {
                data = await response.json();
            } catch (jsonErr) {
                data = { detail: 'Invalid JSON response from server.' };
            }
        } else {
            const text = await response.text();
            data = { detail: text };
        }

        // Handle HTTP Status Codes
        if (!response.ok) {
            const status = response.status;
            let message = data.detail || data.error || `HTTP ${status} Error`;

            switch (status) {
                case 400:
                    // Bad Request / Validation Failure
                    if (data.errors) {
                        message = 'Please correct the validation errors below.';
                    }
                    break;
                case 401:
                    message = 'Authentication required. Your session may have expired. Please log in.';
                    ui.showToast(message, 'warning');
                    break;
                case 403:
                    message = 'Access Denied: You do not have permission to perform this warehouse action.';
                    ui.showToast(message, 'danger');
                    break;
                case 404:
                    message = data.detail || 'The requested resource was not found in the warehouse database.';
                    ui.showToast(message, 'warning');
                    break;
                case 409:
                    // Conflict / Referential Integrity Violation
                    message = data.detail || 'Conflict: Referential integrity prevents completing this operation.';
                    ui.showToast(message, 'danger');
                    break;
                case 500:
                    message = data.detail || 'Internal Server Error: A warehouse database or algorithm failure occurred.';
                    ui.showToast(message, 'danger');
                    break;
                default:
                    ui.showToast(message, 'danger');
                    break;
            }

            throw new APIError(status, message, data);
        }

        return data;
    }

    /**
     * UI Feedback & DOM Helpers
     */
    const ui = {
        /**
         * Prevents duplicate clicks and shows spinner
         */
        setLoading(button, isLoading, loadingText = 'Processing...') {
            if (!button) return;
            if (isLoading) {
                if (!button.dataset.originalHtml) {
                    button.dataset.originalHtml = button.innerHTML;
                }
                button.disabled = true;
                button.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> ${loadingText}`;
            } else {
                if (button.dataset.originalHtml) {
                    button.innerHTML = button.dataset.originalHtml;
                    delete button.dataset.originalHtml;
                }
                button.disabled = false;
            }
        },

        /**
         * Clears all .is-invalid classes and feedback messages in a form
         */
        clearFieldErrors(form) {
            if (!form) return;
            form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            form.querySelectorAll('.invalid-feedback-dynamic').forEach(el => el.remove());
        },

        /**
         * Renders server-side validation errors next to corresponding form fields
         */
        displayFieldErrors(form, errors) {
            if (!form || !errors) return;
            this.clearFieldErrors(form);

            for (const [field, msgs] of Object.entries(errors)) {
                const message = Array.isArray(msgs) ? msgs.join(' ') : String(msgs);
                const input = form.querySelector(`[name="${field}"]`);
                if (input) {
                    input.classList.add('is-invalid');
                    const feedback = document.createElement('div');
                    feedback.className = 'invalid-feedback invalid-feedback-dynamic d-block';
                    feedback.textContent = message;
                    input.parentNode.appendChild(feedback);
                } else {
                    // Non-field error or formset error: show toast
                    this.showToast(`${field}: ${message}`, 'danger');
                }
            }
        },

        /**
         * Enterprise Bootstrap Toast Notification
         */
        showToast(message, type = 'info') {
            let container = document.getElementById('psToastContainer');
            if (!container) {
                container = document.createElement('div');
                container.id = 'psToastContainer';
                container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                container.style.zIndex = '1090';
                document.body.appendChild(container);
            }

            const bgClass = {
                'success': 'bg-success text-white',
                'danger': 'bg-danger text-white',
                'warning': 'bg-warning text-dark',
                'info': 'bg-primary text-white'
            }[type] || 'bg-dark text-white';

            const toastId = 'toast-' + Date.now();
            const toastEl = document.createElement('div');
            toastEl.id = toastId;
            toastEl.className = `toast align-items-center ${bgClass} border-0 shadow`;
            toastEl.setAttribute('role', 'alert');
            toastEl.setAttribute('aria-live', 'assertive');
            toastEl.setAttribute('aria-atomic', 'true');

            toastEl.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body small fw-semibold">
                        ${message}
                    </div>
                    <button type="button" class="btn-close ${type !== 'warning' ? 'btn-close-white' : ''} me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;

            container.appendChild(toastEl);
            if (window.bootstrap && window.bootstrap.Toast) {
                const toast = new bootstrap.Toast(toastEl, { delay: 4500 });
                toast.show();
                toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
            } else {
                setTimeout(() => toastEl.remove(), 4500);
            }
        }
    };

    /**
     * Product Catalog Resource Client
     */
    const products = {
        list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return request(`/api/products/${query ? '?' + query : ''}`);
        },
        get(id) {
            return request(`/api/products/${id}/`);
        },
        create(data) {
            return request('/api/products/', { method: 'POST', body: data });
        },
        update(id, data) {
            return request(`/api/products/${id}/`, { method: 'PUT', body: data });
        },
        delete(id) {
            return request(`/api/products/${id}/`, { method: 'DELETE' });
        }
    };

    /**
     * Shipping Box Inventory Resource Client
     */
    const boxes = {
        list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return request(`/api/boxes/${query ? '?' + query : ''}`);
        },
        get(id) {
            return request(`/api/boxes/${id}/`);
        },
        create(data) {
            return request('/api/boxes/', { method: 'POST', body: data });
        },
        update(id, data) {
            return request(`/api/boxes/${id}/`, { method: 'PUT', body: data });
        },
        delete(id) {
            return request(`/api/boxes/${id}/`, { method: 'DELETE' });
        },
        toggleActive(id) {
            return request(`/api/boxes/${id}/toggle-active/`, { method: 'POST' });
        }
    };

    /**
     * Customer Order Dispatch Resource Client
     */
    const orders = {
        list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return request(`/api/orders/${query ? '?' + query : ''}`);
        },
        get(id) {
            return request(`/api/orders/${id}/`);
        },
        create(data) {
            return request('/api/orders/', { method: 'POST', body: data });
        }
    };

    /**
     * 3D Box Packaging Recommendation Engine Client
     */
    const recommendation = {
        recommendBox(orderId) {
            return request(`/api/orders/${orderId}/recommend-box/`, { method: 'POST' });
        }
    };

    return {
        request,
        ui,
        products,
        boxes,
        orders,
        recommendation
    };
})();

// Attach globally
window.PackSmartAPI = PackSmartAPI;

