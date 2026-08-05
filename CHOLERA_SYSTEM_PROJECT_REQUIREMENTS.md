# NASRDA Project Requirements: Cholera-Environment Correlation and Surveillance System

## 1) Purpose

This document defines the project requirements for delivering a production-ready cholera environmental surveillance, correlation analysis, and early warning platform.

It is intended as the formal baseline for:
- Scope definition
- Delivery roadmap
- Deliverables and acceptance criteria
- Handover obligations
- Client and implementation assumptions

This version intentionally excludes cost and commercial terms.

---

## 2) Project Objective

Build and deploy a web-based, GIS-enabled cholera surveillance system that:
- Integrates epidemiological and environmental data.
- Quantifies how environmental factors, especially flooding, correlate with cholera trends.
- Generates cholera risk maps and hotspot analytics.
- Supports early warning and intervention planning.
- Produces operational and executive reports.

The system must be fully handed over to the client for independent operation after delivery.

---

## 3) Functional Requirements

### A. Risk Mapping and Geospatial Intelligence

1. The system shall provide interactive map visualization at LGA level (and ward level where data is available).
2. The system shall render risk categories (Low/Moderate/High/Critical) using configurable thresholds.
3. The system shall support temporal filtering (weekly/monthly/custom date range).
4. The system shall provide drill-down views for selected geographies.

### B. Environmental-Cholera Correlation Analytics

1. The system shall compute correlation outputs between cholera indicators and environmental indicators across time and geography.
2. Environmental indicators shall prioritize flood-related variables, and also include rainfall and other agreed environmental datasets.
3. The system shall provide time-lag analysis views (for example, environmental conditions versus cholera outcomes after 1-4 weeks) where data supports it.
4. The system shall present trend overlays and comparative charts showing cholera series against environmental series.
5. The system shall provide downloadable correlation tables/plots for technical review and decision meetings.
6. The system shall clearly indicate that correlation outputs are decision-support signals and not standalone proof of causation.

### C. Cholera Analytics Dashboard

1. The system shall display epidemiological indicators, including cases, deaths (if available), and trend direction.
2. The system shall display environmental indicators, including rainfall and flood-related indices (subject to data availability).
3. The system shall present hotspot ranking and priority lists for response planning.
4. The system shall allow comparison of current versus previous periods.

### D. Data Ingestion and Data Quality

1. The system shall accept CSV/Excel templates for epidemiological and environmental datasets.
2. The system shall validate uploaded files and reject malformed data with clear error reporting.
3. The system shall apply deduplication and integrity checks before persistence.
4. The system shall keep audit logs for data uploads and key modifications.

### E. Cholera Risk Engine

1. The system shall implement a weighted risk model combining epidemiological and environmental indicators.
2. The model shall support configurable weights and thresholds by authorized administrators.
3. The system shall execute scheduled risk recomputation at defined intervals.
4. The system shall retain historical risk scores for trend analysis.

### F. Alerts and Early Warning

1. The system shall support rule-based alerts for predefined cholera risk conditions.
2. The system shall provide an alert dashboard with status, severity, and timestamp.
3. The system shall support exportable alert logs.
4. Optional outbound notifications (email/SMS/other) may be enabled as an extension requirement.

### G. Reporting and Export

1. The system shall generate weekly and monthly surveillance reports.
2. The system shall support PDF and CSV export for analytics and alerts.
3. The system shall provide printable executive summary views.

### H. User Management and Security

1. The system shall implement role-based access control (Admin, Analyst, Data Uploader, Viewer).
2. The system shall enforce authenticated access to protected modules.
3. The system shall log user actions for administrative traceability.
4. The system shall secure API access using industry-standard controls.

### I. Administration and System Operations

1. The system shall provide admin controls for configuration of thresholds, weights, and metadata.
2. The system shall provide backup and restore procedures.
3. The system shall expose system-health and diagnostics views for administrators.

---

## 4) Non-Functional Requirements

1. **Availability:** Production service target availability shall be defined in deployment SLA.
2. **Performance:** Core dashboards and map views should load within acceptable operational thresholds under expected user concurrency.
3. **Scalability:** Architecture shall support incremental expansion to additional geographies and data volume.
4. **Security:** Data protection controls, secure authentication, and role restrictions must be enforced.
5. **Maintainability:** Codebase, architecture, and deployment must be documented to enable client-managed operation.
6. **Interoperability:** System should support integration via documented APIs and import/export interfaces.

---

## 5) Scope Boundaries

### In Scope (Phase 1)

- Web platform (frontend + backend + database).
- Cholera risk mapping, environmental correlation analytics, and dashboards.
- Data upload and validation workflows.
- Rule-based alerts dashboard.
- Reporting and export.
- User management and role controls.
- Documentation, training, and handover package.

### Out of Scope (Phase 1)

- Native Android/iOS field application.
- Hardware procurement and endpoint devices.
- Full nationwide rollout beyond agreed coverage.
- Complex bidirectional integration with all external HMIS/EMR systems unless explicitly approved.
- Advanced AI forecasting models beyond agreed baseline risk-scoring model.

---

## 6) Delivery Roadmap

Estimated duration: **24 weeks (6 months)**.

### Phase 0: Inception and Requirement Finalization (Weeks 1-3)

- Stakeholder engagement and workflow confirmation.
- Requirement sign-off and data dictionary finalization.
- Correlation framework definition (indicators, lag windows, interpretation rules).
- Architecture and security blueprint.

**Deliverables**
- Inception report
- Final functional requirements specification
- Data specification and integration plan
- Correlation analysis specification (methods, assumptions, and reporting templates)
- UI/UX wireframes

### Phase 1: Core Platform Build (Weeks 4-10)

- Backend API framework and database schema.
- Frontend core modules and geospatial baseline.
- Data ingestion and validation pipeline.

**Deliverables**
- Alpha environment
- Core modules ready for internal review
- Draft technical documentation

### Phase 2: Cholera Risk and Analytics Completion (Weeks 11-16)

- Risk model implementation and calibration.
- Full analytics dashboard, hotspot logic, and correlation analysis views.
- Admin configuration controls for thresholds/weights.

**Deliverables**
- Beta environment
- Risk-model definition and calibration note
- Correlation baseline report (initial findings from available data)
- Stakeholder validation demo

### Phase 3: Alerts, Reporting, QA and UAT (Weeks 17-21)

- Alert rule engine and monitoring dashboard.
- Report generation and export features.
- End-to-end QA, defect resolution, and UAT cycles.

**Deliverables**
- Release candidate
- QA report
- UAT sign-off report
- User manual (near-final)

### Phase 4: Production Deployment and Handover (Weeks 22-24)

- Production deployment and hardening.
- Training of admin and end users.
- Documentation completion and handover.

**Deliverables**
- Production go-live
- Source code and deployment assets
- Technical/admin/user documentation pack
- Handover and acceptance records

---

## 7) Deliverables and Acceptance Criteria

### Core Deliverables

1. Deployed cholera surveillance web platform.
2. Fully functional map, analytics, environmental-correlation, data ingestion, risk, alert, and reporting modules.
3. API documentation, architecture documentation, and runbooks.
4. User guide and administrator guide.
5. Training sessions and recorded handover materials (if required by client policy).
6. Source code, database schema, and migration scripts.

### Acceptance Criteria

1. All agreed functional modules pass UAT test cases.
2. Data upload, validation, and reporting workflow functions without critical defects.
3. Risk and alert outputs align with approved rule definitions.
4. Correlation outputs are reproducible for provided test datasets and documented with interpretation guidance.
5. Role-based access controls and audit logging are operational.
6. Documentation is complete and sufficient for independent client operation.

---

## 8) Handover and Post-Delivery Model

### Ownership Transfer

At completion, NASRDA shall transfer:
- Complete source code and configuration artifacts.
- Database design and migration assets.
- API and deployment documentation.
- Operations runbooks and support knowledge base.

The client assumes full ownership and operational control after formal handover.

### Warranty/Defect Liability Period

- A defined post-go-live defect resolution window shall apply for issues within delivered scope.
- New feature requests, integrations, or enhancements are excluded from defect liability and handled separately.

### Optional Maintenance (Separate Engagement)

If the client requests continued support after handover, maintenance can be procured under a separate maintenance contract with its own SLA, scope, and fees.

---

## 9) Client Dependencies and Assumptions

Successful delivery assumes:
- Timely access to required epidemiological and environmental datasets.
- Availability of flood and other environmental time-series at usable temporal/spatial resolution.
- Availability of client focal persons for workshops, reviews, and UAT.
- Confirmation of policy thresholds and intervention triggers.
- Timely approval of requirements, test outcomes, and deployment decisions.
- Hosting and governance decisions are provided according to project timeline.

Schedule impact may occur if dependencies are delayed.

---

## 10) Project Closeout Checklist

At closeout, the following must be completed:
- Production deployment completed and validated.
- UAT sign-off obtained.
- All agreed documentation delivered.
- Training and knowledge-transfer sessions completed.
- Source code and operational assets transferred.
- Formal handover and acceptance documented.

This ensures the client can independently operate, maintain, and extend the cholera platform.
