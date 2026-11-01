/**
 * PackSmart Shipping Box Inventory Frontend Integration
 */
document.addEventListener('DOMContentLoaded', function () {
    const modalAddBoxForm = document.getElementById('modalAddBoxForm');
    const deleteBoxForm = document.getElementById('deleteBoxForm');
    const addBoxModalEl = document.getElementById('addBoxModal');
    const deleteBoxModalEl = document.getElementById('deleteBoxModal');

    // 1. Add Box Form via fetch()
    if (modalAddBoxForm) {
        modalAddBoxForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const submitBtn = modalAddBoxForm.querySelector('button[type="submit"]');
            PackSmartAPI.ui.clearFieldErrors(modalAddBoxForm);
            PackSmartAPI.ui.setLoading(submitBtn, true, 'Registering Box...');

            const formData = new FormData(modalAddBoxForm);
            const payload = Object.fromEntries(formData.entries());
            payload.is_active = modalAddBoxForm.querySelector('input[name="is_active"]').checked;

            try {
                const response = await PackSmartAPI.boxes.create(payload);
                PackSmartAPI.ui.showToast(response.message || 'Box registered successfully!', 'success');

                if (addBoxModalEl && window.bootstrap && window.bootstrap.Modal) {
                    const modalInstance = bootstrap.Modal.getInstance(addBoxModalEl) || new bootstrap.Modal(addBoxModalEl);
                    modalInstance.hide();
                }

                setTimeout(() => window.location.reload(), 600);
            } catch (err) {
                PackSmartAPI.ui.setLoading(submitBtn, false);
                if (err.status === 400 && err.errors) {
                    PackSmartAPI.ui.displayFieldErrors(modalAddBoxForm, err.errors);
                } else if (err.status === 401) {
                    PackSmartAPI.ui.showToast('Please log in to add shipping boxes.', 'warning');
                } else {
                    PackSmartAPI.ui.showToast(err.detail || 'Failed to register shipping box.', 'danger');
                }
            }
        });
    }

    // 2. Delete Box Profile via fetch()
    if (deleteBoxForm) {
        deleteBoxForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const submitBtn = deleteBoxForm.querySelector('button[type="submit"]');
            PackSmartAPI.ui.setLoading(submitBtn, true, 'Deleting Container...');

            const deleteUrl = deleteBoxForm.getAttribute('action');
            const idMatch = deleteUrl.match(/\/boxes\/(\d+)\//);
            const boxId = idMatch ? idMatch[1] : null;

            if (!boxId) {
                deleteBoxForm.submit();
                return;
            }

            try {
                const response = await PackSmartAPI.boxes.delete(boxId);
                PackSmartAPI.ui.showToast(response.message || 'Box deleted.', 'success');

                if (deleteBoxModalEl && window.bootstrap && window.bootstrap.Modal) {
                    const modalInstance = bootstrap.Modal.getInstance(deleteBoxModalEl) || new bootstrap.Modal(deleteBoxModalEl);
                    modalInstance.hide();
                }

                setTimeout(() => window.location.reload(), 500);
            } catch (err) {
                PackSmartAPI.ui.setLoading(submitBtn, false);
                if (err.status === 409) {
                    alert(`Referential Integrity Conflict:\n\n${err.detail}`);
                } else if (err.status === 401) {
                    PackSmartAPI.ui.showToast('Authentication required to delete box profiles.', 'warning');
                } else {
                    PackSmartAPI.ui.showToast(err.detail || 'Failed to delete box.', 'danger');
                }
            }
        });
    }

    // 3. Fast Toggle Active Status via fetch()
    document.querySelectorAll('form[action*="toggle-active"]').forEach(form => {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            const actionUrl = form.getAttribute('action');
            const idMatch = actionUrl.match(/\/boxes\/(\d+)\//);
            const boxId = idMatch ? idMatch[1] : null;

            if (!boxId) {
                form.submit();
                return;
            }

            const button = form.querySelector('button');
            const originalHtml = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';

            try {
                const response = await PackSmartAPI.boxes.toggleActive(boxId);
                PackSmartAPI.ui.showToast(response.message, 'info');

                // Update UI badge directly without full page reload
                if (response.box.is_active) {
                    button.innerHTML = `
                        <span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill">
                            <i class="bi bi-check-circle-fill me-1"></i> Active
                        </span>
                    `;
                } else {
                    button.innerHTML = `
                        <span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle rounded-pill">
                            <i class="bi bi-slash-circle me-1"></i> Inactive
                        </span>
                    `;
                }
                button.disabled = false;
            } catch (err) {
                button.disabled = false;
                button.innerHTML = originalHtml;
                PackSmartAPI.ui.showToast(err.detail || 'Failed to toggle status.', 'danger');
            }
        });
    });
});

