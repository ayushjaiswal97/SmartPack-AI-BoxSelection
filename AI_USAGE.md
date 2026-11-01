# AI Usage Disclosure (AI_USAGE.md)

**Project:** PackSmart – AI-Assisted Box Selection System  
**Framework:** Python / Django  
**AI Tool:** Antigravity AI Assistant (Google DeepMind)

## 1. Purpose

This document explains how I used AI during the development of PackSmart. I used it to understand the requirements, plan the application, write and review code, fix issues, create tests, and prepare documentation.

I reviewed the suggestions before using them. I also changed or rejected suggestions that did not work correctly.

## 2. Tools Used

### Antigravity AI Assistant
I used Antigravity to help with:
- Understanding the assignment and planning the work.
- Designing Django models and application structure.
- Developing the box selection algorithm.
- Building backend APIs and the frontend.
- Creating test cases and reviewing code.

### Python and Pytest
I used Python and Pytest to run the code, check calculations, test the algorithm, and find errors.

## 3. Where I Used AI

### Requirement analysis
AI helped me break the assignment into smaller tasks and understand product dimensions, box dimensions, quantities, weight limits, and packaging costs. I also learned that checking volume alone cannot confirm whether products will physically fit inside a box.

### Database and Django design
AI helped me plan the `Product`, `Box`, `Order`, and `OrderItem` models, including their relationships and validations.

### Box selection algorithm
I used AI to explore ways to check product orientations, quantities, weight limits, product placement, collisions, and box cost.

### Backend and frontend
AI helped me build Django models, services, views, API endpoints, and error handling. It also helped with the HTML, CSS, JavaScript, and Bootstrap 5 interface for managing products, boxes, orders, and recommendations.

### Testing and review
AI suggested test cases and helped review validation, security, database queries, error handling, and code structure.

## 4. Main Prompts and Their Purpose

I used prompts for these tasks:

1. **Requirement analysis:** Understand the assignment, business rules, edge cases, and development steps.
2. **Database design:** Create Django models, relationships, field types, and validations.
3. **Box selection algorithm:** Check product rotations, quantities, weight, placement, and box cost.
4. **Backend development:** Connect the algorithm to Django services and API endpoints.
5. **Admin panel:** Configure product, box, and order management.
6. **Frontend development:** Build the warehouse interface using HTML, CSS, JavaScript, and Bootstrap 5.
7. **Frontend integration:** Connect the frontend to Django APIs using Fetch.
8. **Testing:** Create tests for models, the algorithm, APIs, and edge cases.
9. **Security review:** Check CSRF protection, input validation, XSS risks, and database query performance.
10. **Documentation:** Prepare setup instructions, architecture details, testing information, and AI usage notes.

## 5. AI Suggestions I Used

I used several suggestions after reviewing them:

- **Service layer:** Kept the box selection logic separate from Django views so it is easier to test and maintain.
- **Validation:** Added checks and database constraints for dimensions, weight, cost, and quantities.
- **Decimal calculations:** Used `Decimal` and Django's `DecimalField` for dimensions, weight, and money values.
- **Product rotations:** Checked up to six unique orientations for products with three different dimensions and removed duplicate orientations.
- **Test structure:** Organized tests for models, algorithms, APIs, and integration.

## 6. Suggestions I Changed or Rejected

Not every AI suggestion was suitable. I checked the code and changed these approaches:

### Volume-only box check
**Suggestion:** Compare the total product volume with the box volume.

**Problem:** Products can have a smaller total volume than the box and still not fit because of their shapes and dimensions.

**Change:** Used spatial placement and collision checks instead of relying only on volume.

### Unsafe JSON in templates
**Suggestion:** Use Django's `safe` filter to pass JSON into JavaScript.

**Problem:** This could create a script-injection risk.

**Change:** Used Django's `json_script` template tag instead.

### Unnecessary database queries
**Problem:** Calling `order.items.count()` during serialization could cause extra database queries.

**Change:** Reused prefetched related objects where available.

## 7. Issues Found During Review

| Area | Issue | Correction |
|---|---|---|
| Testing | An expected error message did not match the service response. | Updated the test assertion after checking the actual response. |
| Algorithm | A test expected a smaller box, but the products could not physically fit in it. | Checked the dimensions and corrected the test expectation. |
| Security | AI added `csrf_exempt` to the recommendation API. | Removed it and kept CSRF protection. |
| Performance | Dashboard and order pages ran several count queries. | Used conditional aggregation in Django ORM. |

These issues showed me that AI-generated code must be reviewed and tested before it is used.

## 8. How I Tested the Application

### Algorithm testing
I checked different product dimensions and orientations, multiple-product orders, weight limits, collisions, and cases where volume checks passed but actual placement failed.

### Automated tests
I ran:

```bash
pytest -v
```

**Reported results:**
- Total tests: 109
- Passed: 109
- Failed: 0
- Errors: 0

The actual terminal output should be saved in `TEST_OUTPUT.md`.

### Manual testing
I checked product and box management, order creation, quantity and weight calculations, box recommendations, lowest-cost selection, invalid box handling, API errors, and frontend results.

### Code review
I reviewed the separation of business logic, input validation, CSRF protection, database queries, error handling, and code readability.

## 9. Tasks Before Submission

### Original AI conversation
The assignment requires the original AI conversation. I need to export it directly from the AI tool, keep the prompts and responses unchanged, and add it to the GitHub repository.

**Suggested filename:** `PackSmart_Conversation.md`

### Personal learning reflection
I need to write about what I learned from the project, including the 3D packing algorithm, challenges, AI suggestions I corrected, testing, and possible improvements for real warehouse use.

This reflection should describe my own experience.

## 10. Final Checklist

Before submission, I will confirm that:

- Personal details are complete.
- The final code is pushed to GitHub.
- The 109 test results are confirmed by an actual test run.
- `TEST_OUTPUT.md` contains real terminal output.
- `README.md` has setup and run instructions.
- `AI_USAGE.md` accurately describes how I used AI.
- The original AI conversation and personal learning reflection are included.
