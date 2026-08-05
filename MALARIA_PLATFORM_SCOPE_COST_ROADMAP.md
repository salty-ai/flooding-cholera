# NASRDA Proposal Draft: Malaria Environmental Surveillance Platform

## 1) Purpose

This document defines the proposed scope, budget, roadmap, and delivery model for building a malaria-focused platform similar to the current flooding-cholera system, adapted for malaria surveillance, risk mapping, and decision support.

The proposed implementation model is:
- Build and deploy a full production-ready platform.
- Transfer complete ownership and operational control to the client at handover.
- Offer maintenance as an optional post-handover service under a separate agreement.

---

## 2) What We Reviewed in the Existing App

The current app already provides strong reusable foundations:
- Web GIS risk map with LGA-level visualization.
- Analytics dashboards and trend charts.
- Data upload and ingestion pipelines.
- API-driven architecture (FastAPI + React + PostGIS).
- Scheduled risk-score recalculation workflow.

What must change for malaria:
- Disease model: cholera logic must be replaced with malaria risk logic.
- Indicators: include malaria-relevant climate and epidemiological variables.
- Alert rules: malaria thresholds and intervention triggers.
- Domain workflows: case and vector-control reporting formats.

---

## 3) Proposed Scope (Malaria Version)

### A. Core Functional Modules

1. **Malaria Risk Mapping**
- LGA/Ward map layers with risk classes (Low/Moderate/High/Critical).
- Time-aware risk maps (weekly/monthly views).
- Drill-down by state, LGA, and facility catchment where data exists.

2. **Malaria Analytics Dashboard**
- Cases, test positivity, admissions/deaths (if provided), and trend analytics.
- Climate overlays (rainfall, temperature, humidity) for correlation analysis.
- Hotspot ranking and priority intervention lists.

3. **Data Ingestion and Validation**
- CSV/Excel upload templates for health and environmental data.
- Validation checks, error reporting, and deduplication rules.
- Audit trail for uploaded datasets.

4. **Risk Engine (Malaria-Specific)**
- Weighted risk scoring model combining:
  - Epidemiological indicators (recent cases, test positivity, incidence trend)
  - Environmental indicators (rainfall, temperature, humidity, flood-prone areas where relevant)
  - Vulnerability indicators (population density, housing/water-related proxies where available)
- Configurable weights and thresholds for policy adjustment.

5. **Alerts and Early Warning**
- Rule-based triggers (example: sustained high rainfall + rising case trend).
- Alert dashboard and exportable alert reports.
- Optional notification channels (email/SMS/WhatsApp integration as add-ons).

6. **Reporting and Export**
- Auto-generated weekly/monthly situation reports.
- Export to PDF/CSV for planning meetings and executive briefings.

7. **User and Access Management**
- Role-based access control (Admin, Analyst, Viewer, Data Uploader).
- Authentication and session security.

8. **Admin and Handover Readiness**
- Configuration panel for weights, thresholds, and metadata.
- Backup and restore procedures.
- Full technical and user documentation.

### B. Out of Scope (Phase 1)

- Native Android/iOS field app.
- Full EMR/HMIS bidirectional integration beyond agreed API files.
- Hardware procurement (servers, tablets, data capture devices).
- Nationwide rollout beyond agreed states/LGAs without change request.

---

## 4) Delivery Approach and Roadmap

Total duration: **24 weeks (about 6 months)**.

### Phase 0: Inception and Design (Weeks 1-3)
- Stakeholder sessions and requirement confirmation.
- Indicator definition and data dictionary sign-off.
- Architecture and security design.

**Deliverables**
- Inception report
- Functional specification
- Data schema and integration specification
- UI wireframes

### Phase 1: Platform Core Build (Weeks 4-10)
- Backend APIs, database schema, user management.
- Core frontend shell, map framework, baseline dashboard.
- Data upload pipeline with validation.

**Deliverables**
- Working alpha environment
- Core modules functional
- API and database technical documentation (draft)

### Phase 2: Malaria Risk Engine and Analytics (Weeks 11-16)
- Implement malaria-specific risk model.
- Build analytical views and hotspot ranking.
- Add configurable thresholds and scenario settings.

**Deliverables**
- Beta release with risk engine
- Calibration report (model logic and weight rationale)
- Stakeholder review demo

### Phase 3: Alerts, Reporting, QA/UAT (Weeks 17-21)
- Alert rules and alert dashboard.
- Scheduled report generation and exports.
- System hardening, testing, bug fixing, UAT.

**Deliverables**
- Release candidate
- QA and UAT sign-off report
- User manuals (draft final)

### Phase 4: Production Deployment and Handover (Weeks 22-24)
- Production deployment and performance checks.
- Training sessions for admin and analyst teams.
- Knowledge transfer and full source handover.

**Deliverables**
- Production go-live
- Source code repositories and deployment scripts
- Admin/user manuals and runbooks
- Handover certificate and completion report

---

## 5) Budget and Cost Justification

## Recommended Project Budget: **N20,000,000**

This budget is balanced for a robust, production-quality build with proper documentation, quality assurance, and transfer readiness.

### A. Personnel Cost (Primary Cost Driver)

| Role | Level of Effort | Amount (N) |
|---|---:|---:|
| Technical Project Lead / PM | 0.4 FTE x 6 months | 1,200,000 |
| Backend + Geospatial Engineer | 1.0 FTE x 6 months | 5,400,000 |
| Frontend Engineer | 1.0 FTE x 6 months | 4,500,000 |
| Data Scientist / Epidemiology Analyst | 0.5 FTE x 6 months | 2,400,000 |
| QA / Test Engineer | 0.5 FTE x 4 months | 1,200,000 |
| DevOps / Platform Engineer | 0.3 FTE x 6 months | 1,080,000 |
| UI/UX Designer | 0.3 FTE x 2 months | 300,000 |
| **Subtotal Personnel** |  | **16,080,000** |

### B. Infrastructure and Operational Cost (Build + Stabilization Window)

| Item | Basis | Amount (N) |
|---|---:|---:|
| Cloud compute (API + worker + staging) | 6-month estimate | 900,000 |
| Managed Postgres/PostGIS | 6-month estimate | 360,000 |
| Storage and backup | 6-month estimate | 180,000 |
| Monitoring/logging/error tracking | 6-month estimate | 180,000 |
| Domain/SSL/email/SMS baseline | 6-month estimate | 220,000 |
| Security scanning/tooling/compliance overhead | Project allocation | 260,000 |
| **Subtotal Infrastructure/Ops** |  | **2,100,000** |

### C. Contingency and Delivery Risk Buffer

| Item | Amount (N) |
|---|---:|
| Scope-change and integration buffer (~9.1%) | 1,820,000 |
| **Total Project Cost** | **20,000,000** |

### Why N20,000,000 is Justified

- The largest cost is skilled personnel for specialized geospatial, epidemiological, and software engineering work.
- The app requires secure production architecture, not only a prototype.
- Quality assurance, training, and full handover artifacts are included.
- The contingency protects delivery from data-quality and integration uncertainties common in public health projects.

---

## 6) Optional Lean Budget Scenario (If Required)

If the client requires a tighter budget, a limited **N16,000,000 - N17,500,000** scope can be offered by:
- Reducing features in Phase 1 (for example, fewer reports, reduced alert complexity).
- Limiting geography in first release (pilot states only).
- Deferring advanced analytics and notification integrations to Phase 2.

This option reduces risk coverage and may extend the timeline for full-scale capability.

---

## 7) Handover, Ownership, and Post-Delivery Support

### Ownership and Transfer

At project completion, NASRDA hands over:
- Full source code (frontend, backend, scripts, configuration templates).
- Database schema and migration scripts.
- API documentation and deployment runbooks.
- User manuals and admin guides.
- Knowledge transfer sessions for technical and operational teams.

The client receives complete ownership and operational control.

### Warranty Window

- **60-day post-go-live warranty support** for defect fixes related to delivered scope.
- Does not include new features, major integrations, or scope expansion.

### Optional Maintenance (Separate Contract)

If requested after handover, maintenance can be contracted separately for:
- Infrastructure monitoring and uptime support.
- Security patching and dependency updates.
- Data pipeline support and incident response.
- Feature enhancements and change requests.

Indicative maintenance fee (optional): **N1,500,000 - N2,500,000 per month**, depending on SLA and scope.

---

## 8) Client Dependencies and Assumptions

Project success assumes the client provides:
- Access to required historical and ongoing malaria/environmental datasets.
- Timely focal persons for requirement validation and UAT.
- Policy guidance for threshold definitions and intervention priorities.
- Hosting preference decision (client-managed or vendor-managed during build window).

Delays in data access or approvals may affect timeline.

---

## 9) Final Delivery Checklist

At closeout, NASRDA will provide:
- Production-ready malaria surveillance platform.
- Deployed environment and deployment scripts.
- Source code and technical documentation pack.
- Training and handover sessions.
- Signed completion and acceptance records.

This ensures the client can independently operate and extend the system after handover.
