# AI-Assisted Box Selection System

An enterprise-grade Django web application designed for ecommerce warehouse fulfillment centers to automatically determine the **lowest-cost feasible shipping box** for multi-item customer orders.

The system incorporates a **3D Extreme Points Bin Packing Heuristic** supporting full **6-axis orthogonal rotations**, strict weight capacity enforcement, collision detection, and deterministic tie-breaking.

---

## 🌟 Key Features

1. **3D Rotational Bin Packing Engine:**
   - Evaluates whether items physically fit inside candidate boxes in 3D space with non-overlapping bounding coordinates $(x, y, z)$.
   - Supports 6-axis orthogonal orientations ($x, y, z$ axis swaps).
   - Prunes redundant rotations for symmetric objects (cubes and square prisms) to maximize throughput.
   - Includes an optional "Strict Upright Packing Only" mode for fragile or liquid items.

2. **Cost-Optimal Box Selection:**
   - Evaluates active shipping boxes in ascending order of unit packaging cost.
   - Automatically recommends the lowest-cost box that satisfies both physical fit and maximum weight limits.
   - Implements a secondary tie-breaker prioritizing smaller internal box volume (minimizing void fill and dimensional courier charges).

3. **Dynamic Interactive Warehouse Simulator:**
   - Bootstrap 5 responsive UI built for desktop terminals and warehouse barcode tablets.
   - Add/remove multiple products with arbitrary quantities dynamically via JavaScript.
   - Live real-time preview of aggregate order weight and item volume.
   - Interactive HTML5 Canvas isometric 3D visualization showing packed item arrangements inside the box wireframe.
   - Full placement coordinates manifest $(X, Y, Z)$ and oriented dimensions $(DX, DY, DZ)$.

4. **Production Architecture & Separation of Concerns:**
   - **Models:** Relational data schemas with exact `DecimalField` precision for dimensions, weights, and currency. Snapshots historical item specs on order creation for audit immutability.
   - **Domain Layer (`packing_engine`):** Pure Python domain service completely decoupled from the Django ORM and HTTP request lifecycle. Can be tested and benchmarked independently.
   - **Service Layer (`orders/services.py`):** Orchestrates database queries, pre-filters, packing execution, and atomic transactions.
   - **Forms & Views:** Clean Django FormSets, generic class-based views, and role-based login guards.

---

## 🏗️ Architecture & Technology Stack

- **Backend:** Python 3.14+, Django 5.2+
- **Database:** SQLite (default local development) / PostgreSQL ready
- **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons
- **Testing:** Pytest, pytest-django
- **Code Standards:** Strict PEP 8, decimal precision (zero float rounding drift)

### Project Layout

```
box_selection_project/
├── config/                      # Django project configuration & settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── catalog/                 # Product & Shipping Box models, forms, views
│   │   ├── models.py            # Product & ShippingBox entities
│   │   ├── forms.py             # ProductForm, ShippingBoxForm
│   │   ├── views.py             # Catalog management views
│   │   └── management/commands/ # seed_data.py, create_demo_user.py
│   ├── orders/                  # Order composition, evaluations & history
│   │   ├── models.py            # Order, OrderItem, PackingResult
│   │   ├── forms.py             # OrderForm, OrderItemFormSet
│   │   ├── services.py          # Service Layer (ORM <-> Packing Engine)
│   │   └── views.py             # OrderSimulatorView, OrderRecommendationView
│   └── packing_engine/          # PURE DOMAIN LAYER (Zero Django DB coupling)
│       ├── dataclasses.py       # ItemDTO, BoxDTO, PlacementDTO, PackingResultDTO
│       ├── rotations.py         # 3D Orthogonal Matrix rotation generator
│       ├── pre_filters.py       # O(1) & O(N) boundary, volume & weight checks
│       ├── selector.py          # BoxSelectorService (cost optimization & tie-breaking)
│       └── algorithms/
│           └── extreme_points.py# 3D Extreme Points Heuristic Bin Packing Algorithm
├── templates/                   # Bootstrap 5 responsive templates
│   ├── base.html
│   ├── catalog/
│   └── orders/
├── static/                      # Custom CSS & JS assets
├── tests/
│   ├── unit/                    # Unit tests for rotations, geometry, pre-filters
│   └── integration/             # Integration tests for service layer, views, edge cases
├── manage.py
└── pytest.ini
```

---

## 🚀 Quick Start Guide

### 1. Clone & Set Up Environment

```bash
cd boxSelection
```

### 2. Apply Migrations

```bash
python manage.py migrate
```

### 3. Seed Catalog with Realistic Warehouse Data

A management command is included to seed 10 realistic ecommerce products (phones, shoes, monitors, textbooks, dumbbells, etc.) and 6 standardized shipping box sizes:

```bash
python manage.py seed_data
```

### 4. Create Demo Admin Account

```bash
python manage.py create_demo_user
```
* **Username:** `admin`
* **Password:** `admin123password`

### 5. Run Development Server

```bash
python manage.py runserver
```

Open your browser at **`http://127.0.0.1:8000/`** to launch the **AI Box Selection Simulator**.

---

## 🧪 Automated Test Suite

Run the full automated test suite using `pytest`:

```bash
pytest -v
```

### Test Coverage Highlights:
- **Unit Tests:**
  - Cube rotation deduplication ($6 \to 1$ unique orientation).
  - Square prism deduplication ($6 \to 3$ unique orientations).
  - General cuboid permutations ($6$ orthogonal orientations).
  - Upright-only rotation constraints.
  - O(1) Weight capacity disqualification.
  - O(1) Volumetric limit disqualification.
  - Dimension boundary incompatibility checks.
  - Collision-free pairwise 3D coordinates.
  - Optimal cost selection and volumetric tie-breaking.
- **Integration Tests:**
  - Multi-item order composition and automatic box assignment.
  - OrderItem dimensional snapshot immutability.
  - Dynamic FormSet submissions via HTTP POST.
  - Rejection and error messages for oversized or overweight orders.
  - Role-based login enforcement on catalog mutations.

---

## 📦 Box Selection Algorithm Strategy

The 3D Bin Packing Problem (3D-BPP) is NP-hard. Our system implements a 3-stage optimization pipeline:

```
[ Incoming Order Items ]
           │
           ▼
┌──────────────────────────────────────────┐
│ Stage 1: Fast O(1) Disqualification      │
│ - Total Items Weight > Box.MaxWeight     │
│ - Total Items Volume > Box.InternalVolume│
│ - Max Item Dimension > Max Box Dimension │
└──────────────────────────────────────────┘
           │
           ▼ (Remaining Viable Boxes)
┌──────────────────────────────────────────┐
│ Stage 2: Cost-Ascending Sort             │
│ - Primary: PackagingCost ASC             │
│ - Tie-breaker 1: InternalVolume ASC      │
│ - Tie-breaker 2: MaxWeight ASC           │
└──────────────────────────────────────────┘
           │
           ▼ (Test Box Candidates Sequentially)
┌──────────────────────────────────────────┐
│ Stage 3: 3D Rotational Extreme Points    │
│ - Best-Fit Decreasing (BFD) item sorting │
│ - 6-axis orthogonal rotation test        │
│ - Collision-free coordinate placement    │
└──────────────────────────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
[ Feasible ]   [ Infeasible ]
    │             │
    ▼             ▼
Stop & Return   Try Next Candidate
Lowest-Cost Box (or Fail if none left)
```

Because boxes are tested in ascending order of cost, the **first box that successfully packs the order is mathematically guaranteed to be the lowest-cost feasible box**.

