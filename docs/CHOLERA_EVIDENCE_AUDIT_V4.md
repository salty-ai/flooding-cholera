# Nigeria Flooding–Cholera Manuscript: Evidence Audit (Pass 1 — No Rewrite)

## Scope and audit rule

This is the evidence audit requested before manuscript rewriting. The manuscript was extracted from `CHOLERA_PAPER_Finalization_PublicationReady_V4.docx`; the requirements, audit prompt, repository documentation, source code, tests, and available local datasets were inspected. No manuscript rewrite has been performed.

**Location convention:** The supplied DOCX extraction exposes section and extracted-line locations, but not reliable rendered page numbers. Claims below therefore use manuscript section and extracted line range; page numbers must be populated after rendering the DOCX.

**Evidence rule:** A screenshot, seeded/demo record, UI label, code path, placeholder, or README assertion is not empirical validation. A capability implemented in code is not evidence that it was exercised with real data or scientifically validated.

## Executive audit result

The manuscript currently overstates empirical evidence. The repository demonstrates a substantial prototype/platform with nationwide boundary assets, a real-looking cholera CSV, a large FMOH facility GeoJSON, Groundsource/NEMA-related data assets, risk-score and alert code, and correlation code. However, the supplied evidence does **not** establish the manuscript's central quantitative claims: Pearson `r = 0.68–0.82`, a statistically significant 30-day lag, a 4-week operational window, PCA-calibrated weights, predictive performance, validated early warning, NCDC/SORMAS integration, 46,146 *validated* facilities, or a 74-case/0-death sentinel pilot as a documented epidemiological study.

The implementation itself contains important contradictions to the manuscript: the correlation service aggregates monthly data, tests lags 0–4 months, uses `MIN_OVERLAP = 3`, and returns ordinary Pearson p-values without the required time-series/spatial corrections; the risk engine uses fixed hand-coded weights and heuristic normalization rather than PCA calibration; the README describes the system as Cross River-focused while also asserting nationwide coverage; the README explicitly allows mock satellite precipitation fallback; and the authentication summary says authentication is demo-only with no password validation or backend calls.

## Evidence inventory reviewed

### Supplied documents

- `/root/flooding-cholera-solar-review/CHOLERA_PAPER_Finalization_PublicationReady_V4.docx`
- `/root/flooding-cholera-sync/CHOLERA_SYSTEM_PROJECT_REQUIREMENTS.md`
- `/root/flooding-cholera-solar-review/SOLAR_PRO_4_AUDIT_PROMPT.md`
- `/root/flooding-cholera-sync/README.md`
- `/root/flooding-cholera-sync/IMPLEMENTATION_SUMMARY.md`

### Repository/code/data inspected

- Correlation: `backend/app/services/correlation_service.py`
- Risk engine: `backend/app/services/risk_calculator.py`
- GEE/Sentinel-2/Sentinel-1/MODIS integration: `backend/app/services/earth_engine.py`
- Groundsource importer: `backend/app/services/groundsource_importer.py`
- Data seeding/import paths, including `seed_cholera.py`, `seed_database.py`, `seed_fmoh_facilities.py`, `seed_nema_floods.py`, and `data_importer.py`
- Models/routers for cases, facilities, flood events, analytics, upload, alerts, and LGAs
- Backend tests and frontend source tree
- Local data assets including `backend/data/cholera_real/nigeria_cholera_2020_2025.csv`, `backend/data/external_real/fmoh_nigeriahealthfacilities.json.json`, NEMA files, `backend/data/groundsource_2026.parquet`, and `backend/data/boundaries/nigeria_lgas_774.geojson`
- Git working tree: repository has extensive uncommitted modifications, deleted paper screenshots, and newly added real-data files; this materially complicates reproducibility and provenance.

## Claim ledger

| ID | Exact manuscript claim | Section / location | Evidence supplied | Support assessment | Classification | Missing evidence | Safer replacement |
|---|---|---|---|---|---|---|---|
| C01 | “development, pilot validation, and scale-up of a nationwide Earth Observation-enabled environmental health intelligence hub” | Title; Abstract; Conclusion | Working repository with frontend/backend, maps, risk engine, uploads, alerts; no study protocol or validation report | Development is supported at prototype level; pilot validation and national empirical scale-up are not demonstrated | PARTIALLY VERIFIED | Dated deployment record, validation protocol, UAT/field study, real national operating logs | “development and technical demonstration of an EO-enabled environmental health intelligence platform designed for national LGA-level use” |
| C02 | “across all 774 Local Government Areas (LGAs) in Nigeria” | Abstract; Methods 3.1; Results 4.1/4.3; Conclusion | `nigeria_lgas_774.geojson`; loader docstring says 774; README says nationwide; database population/count and completeness audit not supplied | Boundary asset supports intended/available geographic coverage; it does not prove all data layers or analyses cover all 774 LGAs | PARTIALLY VERIFIED | Counted unique LGAs, 36-state+FCT reconciliation, per-layer coverage, missingness map, executed national run | “the platform includes a national LGA boundary layer intended to represent Nigeria’s 36 states, FCT, and 774 LGAs; empirical data completeness varied by source” |
| C03 | “Nigeria’s six geopolitical zones and 774 LGAs” | Introduction | General geographic fact; no source supplied in audit bundle | 774 LGA count can be checked against boundary data; six-zone assignment is not shown in code/data | PARTIALLY VERIFIED | Official boundary/geopolitical-zone source and reproducible crosswalk | “Nigeria’s 36 states and FCT, represented in the study system by an LGA boundary layer” |
| C04 | “surveillance latency (30–90 days)” and “reporting lags ranging from several weeks to months” | Abstract; Introduction | No latency dataset, timestamps, or citation directly supporting these ranges | Not auditable from supplied evidence | UNVERIFIED | Source-specific reporting timestamps and formal citation | “surveillance timeliness can vary across reporting settings; the magnitude was not estimated in this study” |
| C05 | “high-resolution hydrometeorological satellite streams—including NASA GPM IMERG, Sentinel-2 NDWI, Landsat NDVI, and SAR flood extent” | Abstract; Methods 3.2 | GEE code implements Sentinel-2 NDWI and Sentinel-1 VH change detection; MODIS LST exists; no demonstrated GPM/Landsat national extraction run | Some code support, not evidence of executed multi-sensor streams | PARTIALLY VERIFIED | API logs, image IDs, date ranges, preprocessing outputs, data manifest, national extraction artifacts | “the codebase contains integrations for selected satellite-derived indicators, including Sentinel-2 NDWI and Sentinel-1 change detection; executed national time series were not established in this audit” |
| C06 | “coupling ... with NCDC case registries” | Abstract; Methods 3.2 | Local cholera CSV and acknowledgements mention NCDC; no provenance certificate, NCDC delivery record, or metadata | File presence does not establish NCDC provenance | UNVERIFIED | Data-use authorization, source metadata, extraction date, schema/data dictionary, chain of custody | “a local cholera case CSV was available for analysis; its provenance and relationship to NCDC records require documentation” |
| C07 | “SORMAS electronic disease reporting” / “SORMAS summaries” | Introduction; Methods; Table 3 | Search/code inspection found no demonstrated SORMAS connector; future roadmap explicitly says “Establishing” SORMAS API synchronization | Contradicted as an implemented integration; historical background may be cited separately | CONTRADICTED | Actual SORMAS export/API logs, credentials/governance, mapping, synchronization tests | “SORMAS integration was identified as a future interoperability requirement; no operational connector was evidenced” |
| C08 | “initial 30-day sentinel pilot ... analysed 74 reported cases and 0 deaths across riverine communities” | Abstract; Table 1; Results 4.2 | Table lists Biase 42 + Yakurr 32 = 74 and 0%; repository contains demo/seed scenario code and Cross River assets; no dated pilot dataset, protocol, case line list, or denominators | Arithmetic in manuscript table is internally consistent, but the epidemiological pilot is not evidenced | UNVERIFIED | Raw line list, dates, case definitions, source, inclusion criteria, LGA/community identifiers, verification/ethics | “The manuscript presents a 30-day Cross River sentinel example totaling 74 reported cases and no recorded deaths; the underlying pilot dataset and validation protocol were not supplied for independent verification” |
| C09 | “Cross River State” is a pilot while system is national | Abstract; Results | Cross River GeoJSON and 18-LGA references; national boundary file also present | Geographic distinction is conceptually present but manuscript repeatedly presents pilot/system evidence as national empirical evidence | PARTIALLY VERIFIED | Separate pilot-vs-national data tables and coverage accounting | “Cross River was treated as a sentinel pilot; the intended system scope remained Nigeria-wide” |
| C10 | “system was subsequently scaled nationwide, integrating ... risk scoring engine v2.0 ... for all 774 LGAs” | Abstract | `RiskCalculator.calculate_all()` loops over all database LGAs; national boundary/import code | Code supports capability to calculate for loaded LGAs, not executed national output or completeness | PARTIALLY VERIFIED | Run manifest, database row counts, error counts, dates, output checksum | “the implementation includes a national LGA risk-score calculation path; national empirical performance was not validated” |
| C11 | “dynamic 14-day and 30-day vulnerability projections” | Abstract | Risk code uses recent cases over 14 days and flood-event lookback over 30 days; it calculates current scores, not forecast projections | “Projections” is unsupported; windows are lookback inputs | CONTRADICTED | Forecast design, future outcome labels, horizon-specific evaluation | “risk scores use a 14-day recent-case window and a 30-day flood-event lookback; they are not validated forecasts” |
| C12 | “Cross-correlation analytics revealed a statistically significant 30-day temporal lag” | Abstract; Results 4.3 | Correlation code tests monthly lags 0–4; no supplied executed output or statistical report | The method can produce Pearson p-values, but the specific finding is not evidenced; monthly lag ≠ demonstrated 30-day lag | UNVERIFIED | Exact input series, n, r/p/CI per lag, selected-lag rule, corrections, output file | “The implementation provides exploratory monthly lagged Pearson correlations; no independently verified 30-day association is reported here” |
| C13 | “Pearson’s r = 0.68 to 0.82” | Abstract; Results | No result artifact, script output, or table with values; code does not hard-code these values | Unsupported by supplied evidence | UNVERIFIED | Reproducible analysis script, frozen data, exact scope, n, results table, CI | Remove until reproduced; if reproduced: “exploratory Pearson correlations ranged from ... in the prespecified analysis” |
| C14 | “p < 0.001” / “statistically significant” | Results 4.3 | Code calls `scipy.stats.pearsonr`; no output, no n, no multiple-testing/time-series adjustment | Cannot verify and likely anti-conservative if applied to autocorrelated series and multiple lags | UNVERIFIED | Correct inferential model, effective sample size, adjusted p-values, CI, multiplicity plan | “Nominal Pearson p-values were calculated in the prototype; inferential significance was not established because dependence and multiplicity were not addressed” |
| C15 | “providing public health authorities with a 4-week operational window” | Abstract; Discussion; Conclusion | No prospective alert evaluation, sensitivity/specificity, lead-time distribution, or intervention study | Causal/operational conclusion exceeds evidence | UNVERIFIED | Prospective or held-out evaluation and operational impact study | “A 30-day lag is a proposed operational hypothesis requiring prospective validation; no operational window was demonstrated” |
| C16 | “PCA-calibrated weights” / “weights dynamically calibrated using PCA against historical NCDC epidemic outbreaks” | Methods 3.5 | Risk code uses fixed weights: flood .25, flood-event .20, rain .20, cases .25, vulnerability .10; no PCA code found | Directly contradicted by implementation | CONTRADICTED | PCA/calibration script, training data, loadings, fitting protocol, validation | “The implemented v2.0 score uses fixed heuristic weights (0.25, 0.20, 0.20, 0.25, 0.10); these weights were not PCA-calibrated in the supplied code” |
| C17 | “geostatistical risk scoring” | Title; Methods; Results | Weighted MCDA code and spatial database; no geostatistical model/variogram/spatial regression found in inspected paths | Terminology overstates method | PARTIALLY VERIFIED | Formal spatial model and spatial validation | “LGA-level weighted composite risk scoring” |
| C18 | “daily composite cholera vulnerability score” | Methods 3.5 | Risk calculator computes a score anchored to latest case date; persistence exists; no scheduler/run history supplied | Calculation capability supported; daily operation not evidenced | PARTIALLY VERIFIED | Scheduler logs, score dates, historical completeness | “a composite score can be calculated for an LGA at a specified data anchor date” |
| C19 | “predictive public health intelligence” / “predictive early warning system” | Introduction; Abstract; Conclusion | Risk code uses current/recent cases as an input and no train/test forecasting; requirements explicitly exclude advanced AI forecasting beyond baseline risk scoring | Unsupported and misleading | CONTRADICTED | Forecast model, temporal holdout, prospective metrics | “decision-support risk scoring” |
| C20 | “validated healthcare facilities” / “46,146 validated healthcare facilities” | Abstract; Results 4.1; Figure 7 | GeoJSON declares `totalFeatures: 46146`; seed script can load records; records contain functional status values, including Unknown; no validation audit | Count is supported as a source-file feature count, but “validated” is not | PARTIALLY VERIFIED | Provenance, deduplication, coordinate validation, field completeness, functional-status validation, date/version | “a local FMOH facility registry extract containing 46,146 feature records was available; record validation was not independently established” |
| C21 | “real-time” / “near-real-time” environmental monitoring | Abstract; Methods 3.4; Figure captions; README | GEE request functions and UI labels; no scheduled ingestion, latency measurement, or continuously updated production log; README says optional credentials | Not evidenced as operational real-time | UNVERIFIED | Ingestion schedule, timestamps, latency SLO, uptime/logs, failure handling | “on-demand or configured satellite-data retrieval” |
| C22 | “10-year historical means” and current anomalies | Methods 3.4 | No baseline tables, code path, or data manifest demonstrating ten years | Unsupported | UNVERIFIED | Ten-year per-LGA baseline data and anomaly calculation script | Remove or state as planned methodology |
| C23 | “NDWI values greater than zero indicate open water bodies and inundated terrain” | Methods 2.2 | Code uses threshold 0.3; remote-sensing indicator definition is oversimplified and context-dependent | Threshold wording conflicts with implementation and needs validation | PARTIALLY VERIFIED | Sensor-specific threshold calibration/accuracy assessment and cloud/mask protocol | “NDWI was used as a water-related indicator; the implementation used an NDWI threshold of 0.3 for a flood mask, subject to local validation” |
| C24 | “SAR ... directly correlates with extended water contamination duration” | Methods 2.2 | SAR code detects backscatter change; no contamination measurements | Causal ecological claim unsupported | UNVERIFIED | Water-quality samples, contamination outcomes, validated proxy relationship | “SAR-derived change detection can identify areas consistent with surface-water change; contamination duration was not measured” |
| C25 | “empirical lag analysis reveals a critical 1-to-3 month lag” | Methods 2.2 | No analysis result supplied; implementation has exploratory monthly lags | Unsupported | UNVERIFIED | Full lag analysis and prespecified selection | “The study proposed monthly lag analysis; the empirical lag distribution requires reproducible analysis” |
| C26 | “all 774 LGAs over a 5-year multi-year window (2020–2025)” | Results 4.3 | Cholera filename spans 2020–2025; no completeness audit; Groundsource file named 2026; no national environmental time series shown | Intended date range partly supported; complete panel not established | PARTIALLY VERIFIED | Per-year/per-LGA data availability, missingness, environmental dates, panel construction | “The available cholera file is labelled 2020–2025; completeness and alignment with environmental records must be reported before claiming a national five-year panel” |
| C27 | “threshold rules (3-day rainfall >50mm, NDWI increase >15%, 7-day case surge >10)” | Results 4.4 | Alert engine/rules exist; exact thresholds need trace to rule seed/config; no alert performance evaluation | Implemented rule capability may be supported; thresholds are operational rules, not validated predictors | PARTIALLY VERIFIED | Rule configuration export, provenance, alert audit, sensitivity/PPV/lead time | “The prototype supports configurable rule-based alerts; example thresholds were operational defaults and were not clinically validated” |
| C28 | “multi-LLM Surveillance Copilot integrating DeepSeek V4, Gemini 3.6 Flash, and Claude” | Abstract; Results 4.4 | Agent service and UI routing paths exist; current provider availability/configuration not shown; Claude code paths may be fallback/mock | At most implementation capability | PARTIALLY VERIFIED | Provider config, live integration logs, model/version, prompt/evaluation set, data governance | “The interface includes a conversational assistant and model-routing hooks; live multi-provider operation was not independently evidenced” |
| C29 | “Agent Explorer ... autonomous ... schema detection, column mapping, and geocoding to 774 LGA centroids” | Results 4.4 | Agent service and upload routes exist; no end-to-end real-file trace and accuracy evaluation | Capability partially supported, scientific performance not | PARTIALLY VERIFIED | Test files, mapping accuracy, error logs, geocoding match rates | “The prototype provides assisted upload and schema-mapping workflows; geocoding accuracy was not evaluated” |
| C30 | “publication-grade SitReps in PDF and CSV” | Results 4.4 | `report_service.py`, export routes, frontend components exist | Export capability likely implemented; quality/accuracy not evidenced | PARTIALLY VERIFIED | Generated artifacts, template/version, content validation, reproducible examples | “The system includes PDF/CSV report export functionality” |
| C31 | “transition ... from reactive crisis response to proactive ... management” | Discussion; Conclusion | No implementation-impact study or decision outcome data | Interpretive policy aspiration, not result | INTERPRETIVE | User study, response-time/outcome comparison | “The platform is intended to support earlier situational awareness; its effect on response or outcomes remains untested” |
| C32 | “national health registries” / multi-agency shared awareness across NASRDA, NCDC, FMOH, NEMA, ministries | Methods; Discussion | Files and acknowledgements; no agreements, live integrations, governance or user logs | Institutional linkage not evidenced | UNVERIFIED | Data-sharing agreements, integration logs, institutional approvals, user acceptance | “The architecture is designed to combine environmental and health-related datasets; institutional interoperability was not demonstrated” |
| C33 | “cloud-native, microservices-based ... secure multi-agency data sovereign access” | Methods 3.1 | FastAPI/React/PostGIS code; no deployment architecture, security audit, access-control evidence; demo auth summary explicitly says no real auth | Architecture description partly supported; security/data sovereignty claim unsupported | PARTIALLY VERIFIED | Deployment manifests, threat model, RBAC tests, audit logs, encryption, hosting evidence | “The prototype uses a web application architecture with FastAPI, React, and spatial database components; production security and sovereignty controls require separate verification” |
| C34 | “validated” / “pilot validation” generally | Title; Abstract; Table 1 | Implementation summary says build status; no validation protocol or independent test | Software tests/build are not scientific validation | UNVERIFIED | Prespecified validation design, independent dataset, acceptance criteria, outcomes | Replace with “technical demonstration” unless formal validation evidence is supplied |
| C35 | “Case fatality rate” for pilot rows 0.0% | Table 1; Results | Table gives cases and zero deaths; no case definition, follow-up window, ascertainment, or denominator documentation | Arithmetic descriptive value only if the table data are authentic and complete | PARTIALLY VERIFIED | Case/death ascertainment and completeness | “Recorded deaths were zero among the reported cases in the supplied table; completeness was not assessed” |
| C36 | “Cross River ... riverine communities” | Abstract; Results | Cross River scope and LGA names; no community-level geography or riverine classification file | Cross River pilot location supported; riverine-community generalization not | PARTIALLY VERIFIED | Community identifiers and classification method | “selected Cross River LGAs” |
| C37 | “Landsat NDVI ... soil moisture retention” | Methods | Code inspected contains MODIS LST and Sentinel indices; no demonstrated Landsat NDVI pipeline in supplied excerpts | Not evidenced as implemented end-to-end | UNVERIFIED | Landsat collection, preprocessing, masking, outputs | “NDVI was proposed as an environmental covariate; its execution in the supplied pipeline requires confirmation” |
| C38 | “high-resolution” / “1–5 day revisit” / “continuously tracking” | Section 2.1 | General EO background and citations; sensor-specific resolution/revisit depends on platform, clouds, orbit and processing | Requires precise source-specific citations; not a result of this system | PARTIALLY VERIFIED | Correct citations and operational acquisition statistics | Describe sensor-specific nominal resolution/revisit with citations; avoid “continuous” |
| C39 | “all 36 states and FCT” | Methods; facility figure | Nationwide boundary/facility files likely include states; no computed unique-state audit supplied | Plausible but not independently counted in this pass | PARTIALLY VERIFIED | Scripted state-count/FCT audit and join coverage | “national files were intended to represent 36 states and FCT; coverage was to be verified by a reproducible audit” |
| C40 | “NCDC 2024 annual report” and other references support national findings | References; Results | Bibliography entries exist; references do not evidence the repository’s specific derived statistics | Citations are not substitutes for analysis provenance | PARTIALLY VERIFIED | Citation-to-claim mapping and data extraction records | Retain only claims directly supported by each cited source; cite the actual analysis dataset for derived results |

## System–paper reconciliation

| Feature / paper claim | Formal requirement | Implementation/evidence observed | Status | Required correction |
|---|---|---|---|---|
| LGA map and drill-down | LGA map; ward where available; temporal filters; drill-down | React map, LGA routes, GeoJSON, filters and detail views present | IMPLEMENTED/EVIDENCED at software level | Do not equate UI presence with geographic/data completeness |
| Nationwide 774-LGA scope | Requirements actually say full nationwide rollout is out of scope for Phase 1 | National boundary asset and loader path exist; README also describes Cross River focus | IMPLEMENTED BUT UNVALIDATED | Frame as national-capable architecture/asset, with Cross River sentinel pilot; report data coverage |
| Correlation analytics | Compute correlation, lag views, plots/tables, causation caveat | `correlation_service.py` computes monthly aggregation, lags 0–4 months, Pearson r/p | IMPLEMENTED BUT UNVALIDATED | Report exploratory method; do not report r/p/lag without frozen outputs and corrected inference |
| 30-day lag | Requirements allow 1–4 week lag “where data supports it” | Code uses month bins and 1–4 month lag indices; no 30-day selection evidence | UNSUPPORTED AS EMPIRICAL CLAIM | Reanalyse daily/weekly or explicitly call it a monthly lag hypothesis |
| Risk engine | Weighted configurable risk model; scheduled recompute; history | Fixed v2 weights and heuristic normalisation; persisted history/upsert; no PCA | IMPLEMENTED BUT UNVALIDATED; PCA CLAIM CONTRADICTED | Describe fixed heuristic MCDA; remove PCA/calibration language |
| Predictive/forecasting model | Requirements exclude advanced AI forecasting in Phase 1 | No train/test forecast model; risk uses contemporaneous/recent cases | UNSUPPORTED | Call output risk score/decision-support signal, not prediction/forecast |
| Rule-based alerts | Configurable threshold rules, dashboard, export | Alert models/routers/seed rules/UI present | IMPLEMENTED BUT UNVALIDATED | State rules are operational and require retrospective/prospective evaluation |
| Early warning | Requirements use early warning/intervention planning as objective | Alert engine exists; no lead-time/performance evidence | IMPLEMENTED BUT UNVALIDATED | Use “early-warning capability” or “candidate alerting,” not validated early warning |
| Upload/validation/deduplication | CSV/Excel, schema rejection, deduplication, audit logs | Upload/data importer code present; audit-log completeness not demonstrated | IMPLEMENTED BUT UNVALIDATED | Provide acceptance tests and upload audit examples |
| NCDC/SORMAS integration | Requirements require interoperability/interfaces, not necessarily live SORMAS | Local cholera CSV; no SORMAS connector evidenced; roadmap says future | NCDC PROVENANCE UNVERIFIED; SORMAS UNSUPPORTED | Distinguish local imported file from live institutional integration |
| Satellite processing | Environmental indicators subject to availability | GEE code for S2 NDWI, S1 change, MODIS LST; NASA GPM has mock fallback; no run artifacts | IMPLEMENTED BUT UNVALIDATED | Supply acquisition/preprocessing manifest and real-output checksums; disclose unavailable sources |
| FMOH 46,146 facilities | Facility overlay is a useful system feature | GeoJSON metadata says 46,146; records have status including Unknown | IMPLEMENTED/EVIDENCED AS FILE COUNT; VALIDATED UNSUPPORTED | Say “46,146 source records,” not validated facilities |
| Multi-LLM copilot | Not a core scientific validity requirement | Agent/UI hooks; provider live status not supplied | IMPLEMENTED BUT UNVALIDATED | Separate product capability from epidemiological evidence |
| Agent Explorer | No-code ingestion is described in paper but not a formal core requirement | Agent service and UI paths present | IMPLEMENTED BUT UNVALIDATED | Provide real-file trace and accuracy metrics or downgrade to prototype capability |
| PDF/CSV reports | Formal reporting/export requirement | Report service and export routes present | IMPLEMENTED BUT UNVALIDATED | Include generated examples and content checks |
| RBAC/security | Formal RBAC and authenticated protected modules | Demo auth summary explicitly says no password validation/backend calls; no security audit | UNSUPPORTED AS PRODUCTION CLAIM | Do not claim secure multi-agency production operation |
| UAT/handover/production | Formal requirements include UAT, deployment, handover, documentation | No UAT sign-off, deployment record, handover/acceptance package supplied | PLANNED/UNSUPPORTED | Remove production/validated language until records exist |

## Immediate audit conclusions

1. **The central quantitative result is not currently publishable.** No frozen data-to-result artifact supports `r = 0.68–0.82`, `p < 0.001`, or a 30-day peak lag.
2. **The PCA statement is contradicted by code.** The actual risk engine uses fixed heuristic weights and does not implement PCA calibration.
3. **The risk engine is not a forecasting model.** It includes recent case burden, which creates leakage if evaluated as prediction of near-future cases.
4. **The 74-case/0-death pilot is a table assertion, not an auditable pilot dataset.** The repository’s demo/seed pathways make provenance especially important.
5. **The national scope must remain national in intent but not be presented as nationally validated evidence.** Cross River remains the sentinel pilot; the national layer is a system capability/data-coverage question.
6. **“Real-time,” “validated,” “predictive,” “statistically significant,” and “early warning” must be withheld or explicitly qualified.**
7. **The source tree is not in a clean reproducibility state.** There are uncommitted modifications, deleted paper screenshots, and newly added data/assets. A frozen commit or archive is required before analysis claims can be reproduced.

## Evidence still required before any rewrite can safely preserve quantitative findings

- Frozen repository commit/DOI/archive, dependency lockfiles, and analysis environment specification.
- Raw case data with provenance, case definitions, dates, LGA codes, suspected/confirmed status, deduplication rules, and permission/ethics documentation.
- Raw environmental data manifest: satellite collection IDs, image IDs, dates, cloud masks, QA bands, projections, composites, spatial resolution, zonal-statistics code, and output hashes.
- Exact 774-LGA and 36-state+FCT coverage audit for every data layer.
- Reproducible correlation script and output containing sample size per lag, exact variables, missingness, r, CI, p, adjusted p, and selected-lag rule.
- A prespecified lag-analysis protocol using an appropriate temporal resolution and dependence-aware inference.
- Independent calibration/validation split; forecast horizon and outcome definition; discrimination/calibration metrics; confidence intervals; baseline comparator.
- PCA/calibration artifacts if the PCA claim is to be retained; otherwise remove it.
- Facility registry provenance, version/date, deduplication and validation report; avoid treating `totalFeatures` as validation.
- Demonstrated SORMAS/NCDC integration evidence or explicit statement that it was not available.
- Alert audit log, historical replay evaluation, lead-time distribution, sensitivity, specificity, PPV/NPV, false-alert burden, and prospective validation plan.
- Security/RBAC/UAT/handover evidence before production or institutional claims.

## Statistical/methodological review — preliminary, before rewriting

### Sample size and unit of analysis

The inspected correlation implementation uses monthly observations and permits `MIN_OVERLAP = 3`. A five-year monthly series could have at most about 60 time points before missingness, but the actual `n` per lag is not supplied. If analyses are pooled across LGAs, the unit of analysis, repeated measures, and clustering must be explicit. The 74 pilot cases are counts, not a sample size for a flood–cholera correlation unless accompanied by the number and timing of independent observations.

### p-values, confidence intervals, and dependence

`scipy.stats.pearsonr` produces nominal p-values under independent paired observations. Monthly cholera and environmental series are likely serially autocorrelated, and LGA observations are spatially correlated. Standard Pearson p-values can therefore be anti-conservative. Report effect-size CIs and use an appropriate time-series/spatiotemporal model, block bootstrap, effective sample-size correction, or permutation scheme that preserves dependence.

### Lag selection and multiple testing

The code evaluates lags `(0,1,2,3,4)` months. Selecting the maximum correlation after examining several lags requires a prespecified rule and multiplicity control or resampling. A monthly index cannot by itself establish an exact 30-day biological or operational lag. Analyse daily/weekly data if a 30-day claim is essential, or call the result a monthly lag association.

### Confounding and reverse causality

Rainfall, flooding, seasonality, temperature, WASH, population movement, access to care, reporting intensity, and outbreak response may confound the association. The risk engine includes recent cases, so it is not a clean prospective environmental predictor. The paper must separate environmental association from case-informed risk scoring and must not imply causation.

### Calibration and train/test separation

No train/test separation or calibration protocol was found. If weights or thresholds were chosen using the same outcome period used for evaluation, performance is optimistic. Freeze a training period, tune weights/thresholds only there, and evaluate on a later temporal holdout, with geographic holdout or leave-one-region-out sensitivity analysis.

### Missing data and surveillance bias

The manuscript acknowledges variable reporting completeness but does not quantify missingness. Provide a data-completeness matrix by LGA/month/source, missingness mechanisms, imputation rules, sensitivity analyses, and reporting-bias proxies. Zero cases or deaths cannot be interpreted as true zero without ascertainment evidence.

### Satellite preprocessing

Document collection/version, cloud and shadow masking, compositing, speckle filtering, orbit/polarization choices, before/after windows, threshold calibration, mixed pixels, permanent water masking, geometric alignment, and validation against reference flood maps or field observations. The inspected SAR implementation uses a 50 m focal mean and −3 dB change threshold; these are methodological choices, not validated truth.

### Reproducibility

The codebase has local data and import paths but no single analysis entry point producing the manuscript’s reported numbers, no frozen result artifact, no provenance table, and a dirty working tree. The paper should include a reproducibility appendix with exact commands, environment lockfiles, input hashes, data-access constraints, and a one-command or documented multi-step rerun.

## Required next audit step

The next step is to produce a rendered-page claim map and a machine-generated data/provenance inventory, then run the repository’s actual backend/frontend checks in a clean, non-gateway execution context. Only after those outputs are available should the manuscript be rewritten.

**No revised manuscript is included in this pass, as requested.**

---

## Audit status

This document is an evidence audit, not a final rewritten paper. It should be updated after the exact CSV/Parquet schemas and quantitative row counts are independently extracted and after the repository tests are run from an allowed shell context.

## Sources inspected

- Manuscript DOCX and extracted sections 1–8.
- Requirements document, especially §§3–10 and acceptance criteria.
- Solar Pro audit prompt.
- Repository README and implementation summary.
- `correlation_service.py`, `risk_calculator.py`, `earth_engine.py`, `groundsource_importer.py`, and related seed/import/router/test paths.
- Local boundary, cholera, facility, flood and NEMA data assets.

## Claims deliberately not treated as evidence

Screenshots/figure captions, seeded/demo values, UI labels, README assertions, comments/docstrings, model names in configuration/UI, a GeoJSON `totalFeatures` field, and bibliography entries without data-to-claim provenance.

## Reproducibility blockers observed

- Git working tree contains uncommitted modifications and deleted paper screenshots.
- The first attempted repository test command referenced `backend/venv/bin/pytest`, which is absent in the inspected tree; the correct environment/command must be determined and recorded in a clean external shell.
- The supplied requirements document describes national rollout as out of scope for Phase 1, while the manuscript presents nationwide deployment as completed; this scope conflict must be resolved explicitly.
- The README contains both Cross River-focused system language and nationwide-coverage language; the paper must distinguish sentinel-pilot evidence from national architecture/data assets.

## Decision gate for rewriting

Do not preserve any specific correlation range, p-value, exact lag, predictive/early-warning performance, PCA calibration, NCDC/SORMAS live integration, “validated facilities,” or national empirical validation statement unless the missing evidence listed above is supplied and reproduced.