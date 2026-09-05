# ⚡ ChargeSure

### Predictive EV Charging Intelligence for Safer, Smarter Journeys

<p align="center">

**Don't just find a charger. Find a charger you can trust.**

</p>

---

## 🚀 Overview

**ChargeSure** is an intelligent EV charging and route-planning platform built to solve a critical problem in electric mobility:

> **“Will this charger actually work when I reach it?”**

Most EV applications primarily help users locate charging stations. ChargeSure goes beyond location-based discovery by evaluating **whether a charger is reachable, compatible, reliable, available, and trustworthy for a specific journey**.

ChargeSure combines:

**🔋 Range Safety** · **🤖 ML Reliability** · **🔌 Connector Compatibility** · **📊 Crowd Intelligence** · **⚡ Grid-Aware Charging** · **📅 Booking**

into a single decision-making platform.

### The difference

**Traditional EV apps ask:**

> Where can I charge?

**ChargeSure asks:**

> **Where should I charge, can I safely reach it, is it compatible, will it probably work, and when should I charge?**

---

# 🎯 Problem

EV drivers face a problem that simple charger maps do not solve.

A charger can be:

* physically close but outside the vehicle's safe range
* available but unreliable
* powerful but incompatible with the vehicle
* operational historically but currently receiving negative reports
* geographically convenient but less suitable from a grid-load perspective

For electric 2-wheelers and 3-wheelers, these problems become even more important because limited range can make a poor charging decision significantly more costly.

ChargeSure therefore treats charging as an **intelligent decision problem**, not simply a location search.

---

# 💡 Our Solution

ChargeSure creates a journey-aware recommendation by combining multiple sources of intelligence.

```text
Trip + Vehicle + Battery
          │
          ▼
     Route Planning
          │
          ▼
   Chargers Along Route
          │
    ┌─────┼─────────┐
    ▼     ▼         ▼
  Range  Connector  ML
  Safety Compatibility Reliability
    │     │         │
    └─────┼─────────┘
          ▼
 Availability + Trust
          │
          ▼
   Crowd Intelligence
          │
          ▼
 Charger Ranking Engine
          │
          ▼
 Grid-Aware Slot
          │
          ▼
       Booking
```

The result is a recommendation based on the **journey context**, rather than simply the nearest charger.

---

# ✨ Key Features

## 🗺️ Intelligent Route Planning

Users provide an origin, destination, vehicle, battery state, and connector type.

ChargeSure calculates:

* road route
* total route distance
* estimated travel duration
* charging requirements
* charging stations along the journey
* safe candidate chargers
* ranked recommendations

The system evaluates charger position relative to the actual route instead of treating every nearby charger equally.

---

## 🔋 Battery & Range Safety

ChargeSure evaluates whether the vehicle can safely reach a charger.

The decision considers:

* vehicle class
* vehicle range
* current battery percentage
* charger location
* charger position along the route
* required travel distance

Unsafe charging candidates are filtered before final recommendation.

> **Range safety comes before convenience.**

---

## 🤖 Machine-Learning Reliability

ChargeSure uses an **XGBoost** model to estimate charger reliability on a **0–100 scale**.

The platform also provides an evidence-based confidence level:

* 🟢 High
* 🟡 Medium
* 🔴 Low

This makes the system more transparent by communicating both the prediction and the strength of the supporting evidence.

### Important

A reliability score such as:

> **99.1 / 100**

is presented as a **reliability score**, not as a claim of 99.1% probability.

---

## 🔌 Connector Compatibility

ChargeSure verifies whether the selected charger matches the vehicle's connector.

Possible states:

| State          | Meaning                                     |
| -------------- | ------------------------------------------- |
| ✅ Compatible   | Charger supports the selected connector     |
| ❌ Incompatible | Charger does not support the connector      |
| ❓ Unknown      | Connector data is unavailable or unverified |

Unknown connector information is **not assumed to be compatible**.

---

## 📊 Crowd Intelligence

ChargeSure incorporates real-world user reports about charging stations.

Supported observations include:

* Available
* Occupied
* Working
* Faulted
* Offline
* Busy
* Broken
* Wrong Location

Crowd reports help strengthen the platform's operational availability and trust signals.

This creates a feedback loop between:

**Predicted intelligence + Real-world observations**

---

## ⚡ Grid-Aware Charging

ChargeSure introduces a grid-aware decision layer.

When practical, the system can recommend a lower-load charging period instead of automatically choosing the earliest possible slot.

This moves charging decisions from:

> **“Charge whenever possible.”**

towards:

> **“Charge at a better time when practical.”**

---

## 📅 Charging Slot Booking

The recommendation does not stop at information.

Users can book charging slots directly through the platform.

The backend protects against conflicting reservations, including duplicate upcoming bookings associated with the same:

* charger
* user
* vehicle

---

## 📱 Interactive EV Dashboard

The frontend provides a complete journey workflow:

* route planning
* vehicle selection
* battery state
* interactive route map
* charger recommendations
* reliability scores
* reliability confidence
* connector compatibility
* crowd reports
* charging slot recommendations
* booking
* charger details
* trip information

---

# 🏆 Recommendation Intelligence

ChargeSure ranks eligible charging stations using a multi-factor scoring system.

| Factor                  |  Weight |
| ----------------------- | ------: |
| Reliability             | **40%** |
| Distance                | **20%** |
| Availability            | **10%** |
| Trust                   | **10%** |
| Connector Compatibility | **20%** |

This means:

> **The nearest charger is not automatically the best charger.**

The recommendation engine prioritizes:

### **Trust + Range Safety + Intelligence**

Safety and compatibility are handled as decision constraints before final ranking.

---

# 🤖 Machine Learning

### Model

**XGBoost**

### Output

**Charger Reliability Score: 0–100**

### Model Evaluation

| Metric    |      Score |
| --------- | ---------: |
| Accuracy  |   **0.97** |
| Precision | **0.9535** |
| Recall    | **0.9762** |
| F1 Score  | **0.9647** |
| ROC-AUC   | **0.9910** |

The reliability pipeline combines operational evidence and charging behaviour to estimate charger dependability.

Crowd-derived operational signals can additionally influence the availability/trust intelligence around a charger.

---

# 🧠 System Architecture

ChargeSure follows a layered architecture:

```text
┌──────────────────────────────┐
│       Presentation Layer     │
│       React + Leaflet        │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│      API / Application       │
│           FastAPI            │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│     Domain / Decision        │
│   Range + Ranking + Trust    │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│     Machine Learning         │
│          XGBoost             │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│          Routing             │
│            OSRM              │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│     Interoperability         │
│    Future OCPI / Beckn       │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│      Data / Intelligence     │
│     PostgreSQL + PostGIS     │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│       Infrastructure         │
│            Docker            │
└──────────────────────────────┘
```

---

# 🛠️ Technology Stack

| Layer            | Technology               |
| ---------------- | ------------------------ |
| Frontend         | React, JavaScript, Vite  |
| Maps             | Leaflet                  |
| Backend          | Python, FastAPI, Uvicorn |
| Database         | PostgreSQL               |
| Spatial Data     | PostGIS                  |
| Machine Learning | XGBoost                  |
| Routing          | OSRM                     |
| Infrastructure   | Docker                   |

---

# 📂 Project Structure

```text
prototype-ChargeSure/
│
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── models/
│   │   └── ...
│   └── docker-compose.yml
│
├── data_pipeline/
│   ├── clean/
│   ├── intelligence/
│   ├── load/
│   ├── ml/
│   ├── validate/
│   └── ...
│
├── database/
│   └── schema/
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── docs/
│
├── docker-compose.yml
├── .env
└── README.md
```

---

# ⚙️ Installation & Setup

## 1. Clone the repository

```bash
git clone https://github.com/crypticlumen/prototype-ChargeSure.git
cd prototype-ChargeSure
```

---

## 2. Create a Python virtual environment

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

## 3. Install backend dependencies

```powershell
python -m pip install -r backend/requirements.txt
```

---

## 4. Start PostgreSQL + PostGIS

```powershell
docker compose up -d
```

Verify the database container:

```powershell
docker ps
```

Expected container:

```text
chargesure-postgres
```

---

## 5. Start the backend

Run from the project root:

```powershell
$env:PYTHONPATH = ".;backend"
python -m uvicorn backend.app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 6. Start the frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 🔑 Environment Variables

Create a `.env` file in the project root.

```env
DATABASE_URL=postgresql://chargesure:chargesure_dev@localhost:5432/chargesure
OSRM_BASE_URL=https://router.project-osrm.org
```

Keep `.env` local and never commit secrets or credentials to the repository.

---

# 🔌 API

ChargeSure exposes a FastAPI backend with routes for trip planning, charger discovery, reliability intelligence, crowd reporting, booking, and reports.

### Route Planning

```http
POST /routes/plan
```

Creates a vehicle-aware route and charger recommendation plan.

### Charger Discovery

```http
GET /chargers/nearby
```

Retrieves nearby charging stations.

### Charger Reliability

```http
GET /reliability/{charger_id}
```

Returns charger reliability intelligence.

### Crowd Reports

```http
POST /chargers/{charger_id}/crowd-reports
```

Records an observed real-world charger condition.

### Booking

```http
POST /bookings
```

Creates a charging reservation.

### Reports

```http
POST /reports
```

Creates a charger-related report.

For the complete API surface, run the backend and open:

```text
http://127.0.0.1:8000/docs
```

---

# 🎯 End-to-End Decision Flow

For an EV journey, ChargeSure performs the following process:

```text
1. User enters trip
        ↓
2. Vehicle and battery selected
        ↓
3. Route is calculated
        ↓
4. Chargers along the route are identified
        ↓
5. Range safety is evaluated
        ↓
6. Connector compatibility is checked
        ↓
7. Reliability is predicted
        ↓
8. Availability + trust are evaluated
        ↓
9. Crowd intelligence is incorporated
        ↓
10. Eligible chargers are ranked
        ↓
11. Charging slot is recommended
        ↓
12. User books the charger
```

---

# 🔬 Why the Architecture Matters

ChargeSure separates **prediction** from **decision-making**.

The ML layer answers:

> **How reliable does this charger appear to be?**

The decision layer answers:

> **Should this charger actually be recommended for this journey?**

This distinction is important because a highly reliable charger can still be the wrong recommendation when:

* it cannot be safely reached
* the connector is incompatible
* its position is unsuitable for the route
* another charger provides a better overall choice

---

# 🛡️ Trust & Safety Philosophy

ChargeSure follows one core principle:

> ## **Never recommend a charger just because it is nearby.**

A strong recommendation considers:

```text
Reachability
     +
Compatibility
     +
Reliability
     +
Availability
     +
Trust
     +
Route Position
```

This makes the system focused on **actionable trust**, rather than simple charger discovery.

---

# ✅ Current MVP

### Route & Mobility

* ✅ Intelligent route planning
* ✅ Battery-aware range safety
* ✅ Charger discovery along the route
* ✅ Route-position intelligence
* ✅ Charging-stop recommendations

### Intelligence

* ✅ XGBoost reliability prediction
* ✅ 0–100 reliability scoring
* ✅ Evidence-based confidence levels
* ✅ Multi-factor charger ranking
* ✅ Explainable recommendations

### Compatibility & Operations

* ✅ Connector compatibility
* ✅ Availability intelligence
* ✅ Crowd reports
* ✅ Crowd-informed operational signals
* ✅ Trust scoring
* ✅ Unknown-data handling

### Charging Experience

* ✅ Grid-aware charging slots
* ✅ Charging-slot booking
* ✅ Booking conflict prevention

### Platform

* ✅ React dashboard
* ✅ Interactive maps
* ✅ FastAPI backend
* ✅ PostgreSQL integration
* ✅ PostGIS spatial queries
* ✅ Docker-based database infrastructure

---

# 🔮 Future Roadmap

ChargeSure is designed as a foundation that can grow into a broader EV infrastructure intelligence platform.

### Interoperability

* OCPI integration
* Beckn network interoperability
* Charger-operator integrations

### Real-Time Intelligence

* Live charger telemetry
* Real-time charger status
* Vehicle telemetry
* Dynamic availability updates

### Advanced Routing

* Traffic-aware routing
* Dynamic charging-stop optimization
* Personalized journey planning

### Predictive Intelligence

* Improved reliability calibration
* Charger demand forecasting
* Predictive station congestion
* Personalized charging strategies

### Scale

* Nationwide charger intelligence
* Larger operational datasets
* Expanded 2W / 3W / 4W support

---

# 🏁 Hackathon Value Proposition

ChargeSure transforms charger discovery into **predictive charging intelligence**.

### Instead of:

> **“Here are the nearest chargers.”**

### ChargeSure provides:

> **“Here are the chargers you can safely reach, that match your vehicle, are more trustworthy based on available evidence, and make sense for your journey.”**

The strongest value proposition is simple:

## **Trust the charger before you trust the journey.**

---

# 👥 Authors & Team

## Team Leader

### **Jeeraj Pal**

Jeeraj Pal is the **Team Leader** for the ChargeSure project, coordinating the overall project development, integration, and hackathon execution.

## Authors

### **Kaavy Mittal**

### **Kavisha Srivastava**

### **Kavya Sharma**

### **Jeeraj Pal**

The team collaboratively contributed to the development of the **frontend, backend, machine-learning pipeline, data pipeline, database, route intelligence, recommendation engine, charging workflow, and overall product architecture**.

---

# 📌 Repository

**GitHub:**
https://github.com/crypticlumen/prototype-ChargeSure

---

# 📜 Project Status

**ChargeSure is an actively developed hackathon prototype / MVP.**

The current implementation focuses on demonstrating the complete intelligent charging journey from:

**Trip Planning → Safe Charger Selection → Reliability Intelligence → Charging Slot → Booking**

---

<p align="center">

## ⚡ ChargeSure

### **Trust the charger. Trust the route. Complete the journey.**

</p>
