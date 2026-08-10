# HabotConnect — LSA Service Booking Module

**Developer Name:** Antigravity / Candidate  
**Contact Info:** candidate@example.com  

---

## 1. Setup Instructions

This backend is built with Django 5.x, Django REST Framework, and PostgreSQL (with SQLite fallback for local development).

### Prerequisites
- Python 3.11+
- Git

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/iamshammas/habot_backend.git
   cd habot_backend
   ```
2. **Set up the virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables:**
   Copy the example environment file.
   ```bash
   cp .env.example .env
   ```
   *Note: If no database credentials are provided in `.env`, the app safely defaults to a local SQLite database.*
5. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```
6. **Run the Development Server:**
   ```bash
   python manage.py runserver
   ```
7. **Run Automated Tests:**
   ```bash
   pytest
   ```

---

## 2. API Specification

All endpoints are prefixed with `/api/v1/`.

### 2.1 Search LSAs
**`GET /api/v1/lsas/search/`**  
Returns a paginated list of active Learning Support Assistants (LSAs).

* **Query Parameters:**
  * `skills` (optional): Comma-separated list of skills (e.g. `?skills=Math,Science`).
  * `page` (optional): Page number (defaults to 1).
  * `page_size` (optional): Items per page (defaults to 10).
* **Response (200 OK):**
  ```json
  {
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": 1,
        "full_name": "Jane Smith",
        "email": "jane@example.com",
        "skills": [{"id": 1, "name": "Math"}],
        "hourly_rate": "25.00",
        "is_active": true,
        "created_at": "2026-08-10T12:00:00Z"
      }
    ]
  }
  ```

### 2.2 Create a Booking
**`POST /api/v1/bookings/`**  
Creates a new booking for a specific parent and LSA. Fails if the time slot overlaps with an existing pending/confirmed booking (Poka-yoke).

* **Payload:**
  ```json
  {
    "parent_id": 1,
    "lsa_id": 1,
    "start_time": "2026-08-12T10:00:00Z",
    "end_time": "2026-08-12T11:00:00Z"
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "id": 5,
    "parent_id": 1,
    "lsa_id": 1,
    "start_time": "2026-08-12T10:00:00Z",
    "end_time": "2026-08-12T11:00:00Z",
    "status": "pending"
  }
  ```
* **Response (400 Bad Request - Overlap/Conflict):**
  ```json
  {
    "non_field_errors": ["The selected time slot overlaps with an existing booking for this LSA."]
  }
  ```

### 2.3 Payment Gateway Webhook
**`POST /api/v1/payments/webhook/`**  
Receives asynchronous payment events and transitions the booking state. Protected by an idempotency guard on `provider_reference`.

* **Payload:**
  ```json
  {
    "event_type": "payment.success",
    "provider_reference": "stripe-ref-999",
    "booking_id": 5,
    "amount": "25.00"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "detail": "Processed"
  }
  ```
  *(Returns 200 OK early if the webhook payload has already been processed previously).*

---

## 3. Schema Overview & State Machine

### 3.1 Data Model
* **Parent:** Stores parent profiles (`full_name`, `email` unique).
* **Skill:** Stores a dictionary of LSA skills (`name` unique).
* **LSA_Profile:** Stores LSA details (`full_name`, `email`, `hourly_rate`, `is_active`). Has a Many-to-Many relationship with `Skill`.
* **Booking:** The core operational entity. Links `Parent` (FK) and `LSA_Profile` (FK). Includes `start_time`, `end_time`, and `status`. Protected by a composite index on `(lsa, start_time, end_time)`.
* **Payment:** Tracks payment ledger. Has a strict One-to-One relationship with `Booking` and a unique index on `provider_reference` to guarantee idempotency.

### 3.2 State Machine
The core system acts as a deterministic state machine driven by webhooks:

**Booking State Transitions:**
* `pending` ──(payment.success)──> `confirmed`
* `pending` ──(payment.failed)───> `cancelled`
* `confirmed` ──(manual/time-based)──> `completed`

**Payment State Transitions:**
* `pending` ──> `success`
* `pending` ──> `failed`

*Note: A Booking is created as `pending` and never becomes `confirmed` until its strictly linked Payment receives a successful webhook.*

---

## 4. Design Decisions

### 4.1 MVT (Model-View-Template) Justification
While this is a purely REST API-driven prototype (often described as Model-View-Controller in other frameworks), Django's MVT architecture was intentionally utilized:
* **Models (M):** Django's ORM is heavily leveraged to enforce data integrity (e.g. `OneToOneField` for strict Payment-Booking coupling, `is_active` validation, unique constraints). 
* **Views (V):** We utilized DRF Generic Views (`ListAPIView`, `CreateAPIView`) alongside `APIView` for the webhook because it significantly minimizes boilerplate code, implicitly handles standard 201/400 serialization loops, and safely integrates with `transaction.atomic()`.
* **Templates (T):** DRF handles the serialization of JSON natively, substituting traditional HTML templates. This cleanly maps domain objects to standard JSON contracts for the frontend. 

The monolithic MVT approach guarantees fast local development iteration and natively prevents fragmented business logic.

### 4.2 Query Optimization (N+1 Prevention)
In the LSA Search endpoint (`GET /api/v1/lsas/search/`), each `LSA_Profile` has a Many-to-Many relationship with `Skill`. A naive implementation iterates through the returned LSAs and runs an independent database query to fetch the skills for *each* LSA (the N+1 query problem).

To resolve this, `prefetch_related('skills')` was implemented on the queryset. 
* **Before Optimization:** Fetching 10 LSAs resulted in **12 database queries** (1 pagination count + 1 LSA fetch + 10 individual skill fetches).
* **After Optimization:** Fetching 10 LSAs results in exactly **3 database queries** (1 pagination count + 1 LSA fetch + 1 bulk prefetch of all related skills combined).

This enforces a strictly flat query count, ensuring the endpoint scales effortlessly as the database grows.
