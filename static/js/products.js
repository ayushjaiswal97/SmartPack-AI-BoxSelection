/**
 * PackSmart Product Management Frontend Integration
 */
document.addEventListener('DOMContentLoaded', function () {
    const modalAddProductForm = document.getElementById('modalAddProductForm');
    const deleteProductForm = document.getElementById('deleteProductForm');
    const addProductModalEl = document.getElementById('addProductModal');
    const deleteProductModalEl = document.getElementById('deleteProductModal');

    // 1. Add Product Form via fetch()
    if (modalAddProductForm) {
        modalAddProductForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const submitBtn = modalAddProductForm.querySelector('button[type="submit"]');
            PackSmartAPI.ui.clearFieldErrors(modalAddProductForm);
            PackSmartAPI.ui.setLoading(submitBtn, true, 'Registering Product...');

            const formData = new FormData(modalAddProductForm);
            const payload = Object.fromEntries(formData.entries());

            try {
                const response = await PackSmartAPI.products.create(payload);
                PackSmartAPI.ui.showToast(response.message || 'Product created successfully!', 'success');

                // Close modal
                if (addProductModalEl && window.bootstrap && window.bootstrap.Modal) {
                    const modalInstance = bootstrap.Modal.getInstance(addProductModalEl) || new bootstrap.Modal(addProductModalEl);
                    modalInstance.hide();
                }

                // Reload or refresh after brief delay for visual feedback
                setTimeout(() => window.location.reload(), 600);
            } catch (err) {
                PackSmartAPI.ui.setLoading(submitBtn, false);
                if (err.status === 400 && err.errors) {
                    PackSmartAPI.ui.displayFieldErrors(modalAddProductForm, err.errors);
                } else if (err.status === 401) {
                    PackSmartAPI.ui.showToast('Please log in to add products.', 'warning');
                } else {
                    PackSmartAPI.ui.showToast(err.detail || 'Failed to create product.', 'danger');
                }
            }
        });
    }

    // 2. Delete Product with 409 Conflict Handling
    if (deleteProductForm) {
        deleteProductForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const submitBtn = deleteProductForm.querySelector('button[type="submit"]');
            PackSmartAPI.ui.setLoading(submitBtn, true, 'Deleting...');

            const deleteUrl = deleteProductForm.getAttribute('action');
            // Extract product ID from URL /catalog/products/<id>/delete/
            const idMatch = deleteUrl.match(/\/products\/(\d+)\//);
            const productId = idMatch ? idMatch[1] : null;

            if (!productId) {
                // Fallback to form submit if ID cannot be parsed
                deleteProductForm.submit();
                return;
            }

            try {
                const response = await PackSmartAPI.products.delete(productId);
                PackSmartAPI.ui.showToast(response.message || 'Product deleted.', 'success');

                if (deleteProductModalEl && window.bootstrap && window.bootstrap.Modal) {
                    const modalInstance = bootstrap.Modal.getInstance(deleteProductModalEl) || new bootstrap.Modal(deleteProductModalEl);
                    modalInstance.hide();
                }

                setTimeout(() => window.location.reload(), 500);
            } catch (err) {
                PackSmartAPI.ui.setLoading(submitBtn, false);
                if (err.status === 409) {
                    // Specific referential integrity message
                    alert(`Referential Integrity Conflict:\n\n${err.detail}`);
                } else if (err.status === 401) {
                    PackSmartAPI.ui.showToast('Authentication required to delete products.', 'warning');
                } else {
                    PackSmartAPI.ui.showToast(err.detail || 'Failed to delete product.', 'danger');
                }
            }
        });
    }
});

