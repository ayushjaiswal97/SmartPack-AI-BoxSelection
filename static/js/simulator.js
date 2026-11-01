/**
 * PackSmart Multi-Item Order Simulator Dynamics
 */
document.addEventListener('DOMContentLoaded', function () {
    const itemsContainer = document.getElementById('items-container');
    const addItemBtn = document.getElementById('add-item-btn');
    const totalFormsInput = document.getElementById('id_items-TOTAL_FORMS');

    // PRODUCT_CATALOG is defined globally or attached to window
    const catalog = window.PRODUCT_CATALOG || {};

    function updateRowSpecs(row) {
        const select = row.querySelector('.product-selector');
        const preview = row.querySelector('.specs-preview');
        const prodId = select ? select.value : null;

        if (prodId && catalog[prodId]) {
            const p = catalog[prodId];
            preview.innerHTML = `<span class="badge bg-light text-dark border font-mono">${p.length}×${p.width}×${p.height} cm</span> <span class="badge bg-light text-secondary border font-mono">${p.weight} kg</span>`;
        } else {
            preview.innerHTML = `<span class="text-muted small">Select a product...</span>`;
        }
        recalculateSummary();
    }

    function recalculateSummary() {
        let totalUnits = 0;
        let totalWeight = 0;
        let totalVolume = 0;

        if (!itemsContainer) return;
        const rows = itemsContainer.querySelectorAll('.item-row');
        rows.forEach(row => {
            if (row.style.display === 'none') return;
            const select = row.querySelector('.product-selector');
            const qtyInput = row.querySelector('.item-quantity');
            const prodId = select ? select.value : null;
            const qty = parseInt(qtyInput ? qtyInput.value : 0) || 0;

            if (prodId && catalog[prodId] && qty > 0) {
                const p = catalog[prodId];
                totalUnits += qty;
                totalWeight += (p.weight * qty);
                totalVolume += (p.length * p.width * p.height * qty);
            }
        });

        const unitsEl = document.getElementById('summary-units-count');
        const weightEl = document.getElementById('summary-total-weight');
        const volumeEl = document.getElementById('summary-total-volume');

        if (unitsEl) unitsEl.textContent = totalUnits;
        if (weightEl) weightEl.textContent = totalWeight.toFixed(3) + ' kg';
        if (volumeEl) volumeEl.textContent = totalVolume.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' cm³';
    }

    function attachRowListeners(row) {
        const select = row.querySelector('.product-selector');
        const qtyInput = row.querySelector('.item-quantity');
        const removeBtn = row.querySelector('.remove-row-btn');

        if (select) {
            select.addEventListener('change', () => updateRowSpecs(row));
        }
        if (qtyInput) {
            qtyInput.addEventListener('input', recalculateSummary);
        }
        if (removeBtn) {
            removeBtn.addEventListener('click', function () {
                const visibleRows = itemsContainer.querySelectorAll('.item-row:not([style*="display: none"])');
                if (visibleRows.length <= 1) {
                    PackSmartAPI.ui.showToast('An order must contain at least one line item.', 'warning');
                    return;
                }
                const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
                if (deleteCheckbox) {
                    deleteCheckbox.checked = true;
                    row.style.display = 'none';
                } else {
                    row.remove();
                }
                recalculateSummary();
            });
        }
    }

    if (itemsContainer) {
        document.querySelectorAll('.item-row').forEach(row => {
            attachRowListeners(row);
            updateRowSpecs(row);
        });
    }

    if (addItemBtn && totalFormsInput && itemsContainer) {
        addItemBtn.addEventListener('click', function () {
            const currentFormCount = parseInt(totalFormsInput.value);
            const firstRow = document.querySelector('.item-row');
            if (!firstRow) return;

            const newRow = firstRow.cloneNode(true);
            newRow.style.display = '';
            newRow.setAttribute('data-row-index', currentFormCount);

            const select = newRow.querySelector('.product-selector');
            if (select) {
                select.name = `items-${currentFormCount}-product`;
                select.id = `id_items-${currentFormCount}-product`;
                select.value = '';
            }

            const qtyInput = newRow.querySelector('.item-quantity');
            if (qtyInput) {
                qtyInput.name = `items-${currentFormCount}-quantity`;
                qtyInput.id = `id_items-${currentFormCount}-quantity`;
                qtyInput.value = '1';
            }

            const idInput = newRow.querySelector('input[name$="-id"]');
            if (idInput) {
                idInput.name = `items-${currentFormCount}-id`;
                idInput.id = `id_items-${currentFormCount}-id`;
                idInput.value = '';
            }

            const deleteBox = newRow.querySelector('input[name$="-DELETE"]');
            if (deleteBox) {
                deleteBox.name = `items-${currentFormCount}-DELETE`;
                deleteBox.id = `id_items-${currentFormCount}-DELETE`;
                deleteBox.checked = false;
            }

            const preview = newRow.querySelector('.specs-preview');
            if (preview) {
                preview.innerHTML = '<span class="text-muted small">Select a product...</span>';
            }

            itemsContainer.appendChild(newRow);
            totalFormsInput.value = currentFormCount + 1;
            attachRowListeners(newRow);
            recalculateSummary();
        });
    }
});

