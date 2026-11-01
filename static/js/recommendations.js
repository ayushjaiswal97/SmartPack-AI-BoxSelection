/**
 * PackSmart Box Recommendation & Simulation Frontend Integration
 */
document.addEventListener('DOMContentLoaded', function () {
    // --- 1. EXISTING ORDER RECOMMENDATION API WORKFLOW ---
    const apiOrderSelect = document.getElementById('apiOrderSelect');
    const btnTriggerApi = document.getElementById('btnTriggerApi');
    const btnTriggerApiText = document.getElementById('btnTriggerApiText');
    const apiLoadingIndicator = document.getElementById('apiLoadingIndicator');
    const apiResultContainer = document.getElementById('apiResultContainer');
    const apiWinningBoxCard = document.getElementById('apiWinningBoxCard');

    if (apiOrderSelect && btnTriggerApi) {
        apiOrderSelect.addEventListener('change', function () {
            btnTriggerApi.disabled = !this.value;
        });

        btnTriggerApi.addEventListener('click', async function () {
            const orderId = apiOrderSelect.value;
            if (!orderId) return;

            // Show loading state and prevent duplicate click
            apiLoadingIndicator.classList.remove('d-none');
            apiResultContainer.classList.add('d-none');
            PackSmartAPI.ui.setLoading(btnTriggerApi, true, 'Running 3D Packing Optimization...');

            try {
                const data = await PackSmartAPI.recommendation.recommendBox(orderId);

                apiLoadingIndicator.classList.add('d-none');
                apiResultContainer.classList.remove('d-none');
                PackSmartAPI.ui.setLoading(btnTriggerApi, false);

                renderRecommendationResult(data);
                PackSmartAPI.ui.showToast(`Recommendation completed for Order #${data.order_number}`, 'success');
            } catch (err) {
                apiLoadingIndicator.classList.add('d-none');
                PackSmartAPI.ui.setLoading(btnTriggerApi, false);

                if (err.status === 404) {
                    PackSmartAPI.ui.showToast(`Order #${orderId} was not found in the warehouse database.`, 'warning');
                } else if (err.status === 400) {
                    PackSmartAPI.ui.showToast(err.detail || 'Order contains no items or invalid line items.', 'warning');
                } else {
                    PackSmartAPI.ui.showToast(err.detail || 'Failed to calculate packaging recommendation.', 'danger');
                }
            }
        });
    }

    function renderRecommendationResult(data) {
        const isFeasible = (data.selection_status === 'FEASIBLE' && data.selected_box);

        if (isFeasible) {
            apiWinningBoxCard.className = 'card border-0 shadow-sm mb-4 border-start border-4 border-success';
            document.getElementById('apiStatusBadge').className = 'badge bg-success-subtle text-success fs-6 fw-bold';
            document.getElementById('apiStatusBadge').innerHTML = '<i class="bi bi-award-fill me-1"></i> Recommended Lowest-Cost Box';
            document.getElementById('apiBoxName').textContent = data.selected_box.name;
            document.getElementById('apiPackagingCost').textContent = '$' + data.packaging_cost.toFixed(2);
            document.getElementById('apiBoxDimensions').textContent = `${data.selected_box.dimensions.length} × ${data.selected_box.dimensions.width} × ${data.selected_box.dimensions.height} cm`;
            document.getElementById('apiBoxMaxWeight').textContent = data.selected_box.max_weight_capacity.toFixed(3) + ' kg';
            document.getElementById('apiOrderWeight').textContent = data.total_order_weight.toFixed(3) + ' kg';
            document.getElementById('apiVolUtil').textContent = data.volume_utilization_pct.toFixed(1) + '%';
            document.getElementById('apiRuntime').textContent = data.execution_time_ms.toFixed(2) + ' ms execution';
            document.getElementById('apiExplanation').textContent = data.explanation;

            const btn3D = document.getElementById('btnOpen3DView');
            if (btn3D) {
                btn3D.href = `/recommendation/${data.order_number}/`;
                btn3D.classList.remove('d-none');
            }
        } else {
            apiWinningBoxCard.className = 'card border-0 shadow-sm mb-4 border-start border-4 border-danger';
            document.getElementById('apiStatusBadge').className = 'badge bg-danger-subtle text-danger fs-6 fw-bold';
            document.getElementById('apiStatusBadge').innerHTML = '<i class="bi bi-x-octagon-fill me-1"></i> Packaging Infeasible';
            document.getElementById('apiBoxName').textContent = 'No Feasible Shipping Box Found';
            document.getElementById('apiPackagingCost').textContent = '—';
            document.getElementById('apiBoxDimensions').textContent = 'Exceeds active inventory bounds';
            document.getElementById('apiBoxMaxWeight').textContent = '—';
            document.getElementById('apiOrderWeight').textContent = data.total_order_weight.toFixed(3) + ' kg';
            document.getElementById('apiVolUtil').textContent = '0.0%';
            document.getElementById('apiRuntime').textContent = data.execution_time_ms.toFixed(2) + ' ms execution';
            document.getElementById('apiExplanation').textContent = data.explanation || 'No active container can fit all products within certified weight tolerances and dimensional clearances.';

            const btn3D = document.getElementById('btnOpen3DView');
            if (btn3D) {
                btn3D.classList.add('d-none');
            }
        }

        // Render Rejected Candidate Boxes
        const tbody = document.getElementById('apiRejectedTableBody');
        if (tbody) {
            tbody.innerHTML = '';
            if (data.rejected_boxes && data.rejected_boxes.length > 0) {
                data.rejected_boxes.forEach(box => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><span class="fw-semibold text-slate-900">${escapeHtml(box.name)}</span></td>
                        <td><span class="badge bg-light text-dark border font-mono">${box.dimensions.length} × ${box.dimensions.width} × ${box.dimensions.height} cm</span></td>
                        <td><span class="font-mono text-muted">${box.max_weight_capacity.toFixed(3)} kg</span></td>
                        <td><span class="font-mono fw-bold text-slate-800">$${box.packaging_cost.toFixed(2)}</span></td>
                        <td><span class="text-danger small d-flex align-items-center gap-1"><i class="bi bi-x-circle flex-shrink-0"></i> ${escapeHtml(box.rejection_reason)}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3 text-muted">No other candidate boxes in inventory.</td></tr>';
            }
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // --- 2. CUSTOM ORDER BUILDER FORM WITH FETCH() ---
    const orderSimulatorForm = document.getElementById('orderSimulatorForm');
    if (orderSimulatorForm) {
        orderSimulatorForm.addEventListener('submit', async function (e) {
            // Check if we should submit via API or fallback
            const submitBtn = orderSimulatorForm.querySelector('button[type="submit"]');
            PackSmartAPI.ui.setLoading(submitBtn, true, 'Evaluating 3D Packing...');
            // Standard form submission continues to orderRecommendationView
        });
    }
});

