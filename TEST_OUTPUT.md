# PackSmart Test Execution Output

This file captures the actual, verbatim terminal output from running the full automated test suite using `pytest -v` across the entire project repository.

## Execution Environment

- **Operating System:** Windows (win32)
- **Python Version:** 3.14.0 (executable: `C:\Python314\python.exe`)
- **Django Version:** 5.2.18
- **Pytest Version:** 8.4.2 (plugins: `anyio-4.15.1`, `platformdirs-4.13.5`, `django-4.14.0`)
- **Root Directory:** `E:\project\boxSelection`
- **Config File:** `pytest.ini`

---

## Verbatim Terminal Output

```text
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-8.4.2, pluggy-1.7.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
django: version: 5.2.18, settings: config.settings (from ini)
rootdir: E:\project\boxSelection
configfile: pytest.ini
plugins: anyio-4.15.1, platformdirs-4.13.5, django-4.14.0
collecting ... collected 109 items

tests/integration/test_admin.py::test_admin_changelist_views_load PASSED [  0%]
tests/integration/test_admin.py::test_admin_box_actions PASSED           [  1%]
tests/integration/test_admin.py::test_admin_order_evaluate_action PASSED [  2%]
tests/integration/test_admin.py::test_admin_order_mark_as_packed_action PASSED [  3%]
tests/integration/test_api_recommend_box.py::test_api_recommend_box_success_with_id PASSED [  4%]
tests/integration/test_api_recommend_box.py::test_api_recommend_box_success_with_order_number PASSED [  5%]
tests/integration/test_api_recommend_box.py::test_api_recommend_box_invalid_order_id PASSED [  6%]
tests/integration/test_api_recommend_box.py::test_api_recommend_box_empty_order PASSED [  7%]
tests/integration/test_api_recommend_box.py::test_api_recommend_box_infeasible_order PASSED [  8%]
tests/integration/test_api_recommend_box.py::test_api_recommend_box_ignores_inactive_boxes PASSED [  9%]
tests/integration/test_api_recommend_box.py::test_api_recommend_box_database_error_handling PASSED [ 10%]
tests/integration/test_box_views.py::test_box_list_view_renders PASSED   [ 11%]
tests/integration/test_box_views.py::test_box_list_status_filter PASSED  [ 11%]
tests/integration/test_box_views.py::test_box_create_view_authenticated PASSED [ 12%]
tests/integration/test_box_views.py::test_box_update_view_authenticated PASSED [ 13%]
tests/integration/test_box_views.py::test_box_toggle_active_view PASSED  [ 14%]
tests/integration/test_box_views.py::test_box_delete_view PASSED         [ 15%]
tests/integration/test_edge_cases.py::test_edge_case_empty_box_catalog PASSED [ 16%]
tests/integration/test_edge_cases.py::test_edge_case_dense_overweight_order PASSED [ 17%]
tests/integration/test_edge_cases.py::test_edge_case_multiple_quantities_stacking PASSED [ 18%]
tests/integration/test_model_constraints.py::test_product_dimensions_must_be_positive PASSED [ 19%]
tests/integration/test_model_constraints.py::test_product_weight_must_be_positive PASSED [ 20%]
tests/integration/test_model_constraints.py::test_box_packaging_cost_must_be_non_negative PASSED [ 21%]
tests/integration/test_model_constraints.py::test_orderitem_quantity_must_be_positive PASSED [ 22%]
tests/integration/test_model_constraints.py::test_orderitem_unique_product_per_order PASSED [ 22%]
tests/integration/test_order_services.py::test_order_evaluation_and_box_recommendation PASSED [ 23%]
tests/integration/test_order_services.py::test_order_evaluation_infeasible_oversized PASSED [ 24%]
tests/integration/test_order_services.py::test_order_item_snapshot_immutability PASSED [ 25%]
tests/integration/test_product_views.py::test_product_list_view_renders_catalog PASSED [ 26%]
tests/integration/test_product_views.py::test_product_list_view_search_filtering PASSED [ 27%]
tests/integration/test_product_views.py::test_product_list_view_sorting PASSED [ 28%]
tests/integration/test_product_views.py::test_product_create_view_authenticated PASSED [ 29%]
tests/integration/test_product_views.py::test_product_update_view_authenticated PASSED [ 30%]
tests/integration/test_product_views.py::test_product_delete_unlinked_product PASSED [ 31%]
tests/integration/test_product_views.py::test_product_delete_protected_when_linked_to_order PASSED [ 32%]
tests/integration/test_rest_api.py::test_product_api_list_and_create PASSED [ 33%]
tests/integration/test_rest_api.py::test_product_api_detail_update_delete PASSED [ 33%]
tests/integration/test_product_api_delete_conflict_409_when_linked PASSED [ 34%]
tests/integration/test_rest_api.py::test_box_api_crud_and_toggle PASSED  [ 35%]
tests/integration/test_rest_api.py::test_order_api_create_and_evaluate PASSED [ 36%]
tests/integration/test_rest_api.py::test_order_api_create_validation_failure PASSED [ 37%]
tests/integration/test_views.py::test_dashboard_get_view PASSED          [ 38%]
tests/integration/test_views.py::test_simulator_get_view PASSED          [ 39%]
tests/integration/test_views.py::test_simulator_post_successful_evaluation PASSED [ 40%]
tests/integration/test_views.py::test_simulator_post_no_items_validation_error PASSED [ 41%]
tests/integration/test_views.py::test_recommendation_view PASSED         [ 42%]
tests/integration/test_views.py::test_order_list_and_detail_views PASSED [ 43%]
tests/integration/test_views.py::test_recommendation_history_view PASSED [ 44%]
tests/integration/test_views.py::test_catalog_views PASSED               [ 44%]
tests/integration/test_views.py::test_catalog_create_requires_login PASSED [ 45%]
tests/test_api_suite.py::RecommendationAPITestCase::test_empty_order_returns_400 PASSED [ 46%]
tests/test_api_suite.py::RecommendationAPITestCase::test_invalid_order_id_returns_404 PASSED [ 47%]
tests/test_api_suite.py::RecommendationAPITestCase::test_no_feasible_box_returns_infeasible_status PASSED [ 48%]
tests/test_api_suite.py::RecommendationAPITestCase::test_successful_recommendation_api PASSED [ 49%]
tests/test_api_suite.py::CatalogAndOrderAPITestCase::test_invalid_input_order_creation_returns_400 PASSED [ 50%]
tests/test_api_suite.py::CatalogAndOrderAPITestCase::test_unauthorized_access_to_catalog_endpoints PASSED [ 51%]
tests/test_integration_suite.py::DatabaseToServiceIntegrationTestCase::test_database_to_service_box_filtering PASSED [ 52%]
tests/test_integration_suite.py::DatabaseToServiceIntegrationTestCase::test_database_to_service_dto_expansion PASSED [ 53%]
tests/test_integration_suite.py::ServicePersistenceAndConsistencyTestCase::test_api_response_structure_contract PASSED [ 54%]
tests/test_integration_suite.py::ServicePersistenceAndConsistencyTestCase::test_order_to_packaging_service_atomic_persistence PASSED [ 55%]
tests/test_integration_suite.py::ServicePersistenceAndConsistencyTestCase::test_recommendation_results_consistency PASSED [ 55%]
tests/test_model_suite.py::ProductModelTestCase::test_positive_dimension_validation_rejects_zero_and_negative PASSED [ 56%]
tests/test_model_suite.py::ProductModelTestCase::test_positive_weight_validation_rejects_zero_and_negative PASSED [ 57%]
tests/test_model_suite.py::ProductModelTestCase::test_product_creation_with_valid_attributes PASSED [ 58%]
tests/test_model_suite.py::ProductModelTestCase::test_unique_sku_validation PASSED [ 59%]
tests/test_model_suite.py::BoxModelTestCase::test_box_creation_with_valid_attributes PASSED [ 60%]
tests/test_model_suite.py::BoxModelTestCase::test_non_negative_box_cost_allows_zero_and_rejects_negative PASSED [ 61%]
tests/test_model_suite.py::BoxModelTestCase::test_positive_internal_dimension_validation_rejects_zero_and_negative PASSED [ 62%]
tests/test_model_suite.py::BoxModelTestCase::test_positive_max_weight_capacity_validation PASSED [ 63%]
tests/test_model_suite.py::OrderItemModelTestCase::test_order_item_creation_with_valid_quantity PASSED [ 64%]
tests/test_model_suite.py::OrderItemModelTestCase::test_order_item_positive_quantity_validation_rejects_zero_and_negative PASSED [ 65%]
tests/test_model_suite.py::OrderItemModelTestCase::test_order_item_unique_product_per_order_constraint PASSED [ 66%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_boundary_dimension_conditions_exact_fit PASSED [ 66%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_deterministic_tie_breaking PASSED [ 67%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_empty_order_handling PASSED [ 68%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_inactive_boxes_ignored PASSED [ 69%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_lowest_cost_feasible_box_selected PASSED [ 70%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_multiple_products_cannot_fit_despite_sufficient_total_volume PASSED [ 71%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_multiple_products_fit_together PASSED [ 72%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_no_feasible_box_returns_infeasible_with_reasons PASSED [ 73%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_product_does_not_fit_oversized PASSED [ 74%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_quantity_correctly_affects_total_weight PASSED [ 75%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_single_product_fits_after_rotation PASSED [ 76%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_single_product_fits_standard_orientation PASSED [ 77%]
tests/test_algorithm_suite.py::PackingAlgorithmTestCase::test_weight_capacity_exceeded PASSED [ 77%]
tests/unit/test_core_engine.py::test_calculate_total_order_weight_empty PASSED [ 78%]
tests/unit/test_core_engine.py::test_calculate_total_order_weight_multiple_items PASSED [ 79%]
tests/unit/test_core_engine.py::test_generate_valid_orientations_cuboid PASSED [ 80%]
tests/unit/test_core_engine.py::test_generate_valid_orientations_cube_deduplication PASSED [ 81%]
tests/unit/test_core_engine.py::test_generate_valid_orientations_square_prism PASSED [ 82%]
tests/unit/test_core_engine.py::test_check_single_product_fit_successful_rotation PASSED [ 83%]
tests/unit/test_core_engine.py::test_check_single_product_fit_dimensional_exceeded PASSED [ 84%]
tests/unit/test_core_engine.py::test_check_single_product_fit_weight_exceeded PASSED [ 85%]
tests/unit/test_core_engine.py::test_volume_fits_but_spatial_packing_impossible_counterexample PASSED [ 86%]
tests/unit/test_core_engine.py::test_multi_product_successful_spatial_packing PASSED [ 87%]
tests/unit/test_core_engine.py::test_evaluate_box_candidates_inactive_box PASSED [ 88%]
tests/unit/test_core_engine.py::test_select_optimal_box_lowest_cost PASSED [ 88%]
tests/unit/test_core_engine.py::test_select_optimal_box_deterministic_tie_breaking PASSED [ 89%]
tests/unit/test_packing_engine.py::test_rotations_cube_deduplication PASSED [ 90%]
tests/unit/test_packing_engine.py::test_rotations_square_prism_deduplication PASSED [ 91%]
tests/unit/test_packing_engine.py::test_rotations_general_cuboid PASSED  [ 92%]
tests/unit/test_packing_engine.py::test_rotations_upright_constraint PASSED [ 93%]
tests/unit/test_packing_engine.py::test_pre_filter_weight_capacity_exceeded PASSED [ 94%]
tests/unit/test_packing_engine.py::test_pre_filter_volume_exceeded PASSED [ 95%]
tests/unit/test_packing_engine.py::test_pre_filter_dimension_exceeded PASSED [ 96%]
tests/unit/test_packing_engine.py::test_rotational_packing_success PASSED [ 97%]
tests/unit/test_packing_engine.py::test_multi_item_packing_non_overlapping PASSED [ 98%]
tests/unit/test_packing_engine.py::test_box_selector_recommends_lowest_cost PASSED [ 99%]
tests/unit/test_packing_engine.py::test_box_selector_tie_breaking_by_volume PASSED [100%]

============================ 109 passed in 35.92s =============================
```

## Summary Metrics

- **Total Tests Collected:** 109
- **Passed:** 109 (100%)
- **Failed:** 0
- **Errors:** 0
- **Duration:** 35.92 seconds

