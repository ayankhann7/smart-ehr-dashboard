# Hospital Patient Data Analytics & Smart EHR Dashboard

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://smart-ehr-dashboard-5j49yc9ggln4dbf8hghwvf.streamlit.app/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> 🌐 **Live Web Application:** [https://smart-ehr-dashboard-5j49yc9ggln4dbf8hghwvf.streamlit.app/](https://smart-ehr-dashboard-5j49yc9ggln4dbf8hghwvf.streamlit.app/)

An educational mini-project for **Data Science for Health and Social Care**. It loads the **Synthea** synthetic
electronic-health-record CSV export, cleans and validates it with Pandas, and presents the results in an
interactive, mobile-responsive Streamlit dashboard.

> **Disclaimer.** Educational and analytical use only. All data are synthetic. The dashboard is not intended for
> clinical diagnosis, treatment decisions, or real patient care. Findings reflect Synthea's simulation rules, not
> real-world health patterns.

## Problem statement
Hospital records are spread across several linked tables (patients, visits, diagnoses, measurements). Analysts need
a reproducible way to check data quality, summarise the population, and explore visit and diagnosis patterns
without ever touching real patient data.

## Objectives
Load and validate real CSV contents · clean with Pandas · compute descriptive statistics · visualise interactively ·
filter and explore · look up a synthetic patient · document data quality · test the pipeline automatically.

## Dashboard Pages & Module Descriptions

The application is structured into 6 specialised interactive pages:

### 1. 🏥 Executive Dashboard (`pages/0_Executive_Dashboard.py`)
Provides hospital administrators, CMOs, and clinical department heads with high-level operational visibility and executive KPIs.
- **Executive KPIs**: Real-time summary cards displaying Total Unique Patients, Total Encounters, Documented Diagnoses, and Average Patient Age.
- **Encounter Volume & Mix**: Interactive time-series trends tracking historical patient volumes across Emergency, Ambulatory, Inpatient, Urgent Care, and Wellness visits.
- **Condition Spotlight**: One-click dropdown selector to instantly spotlight key chronic cohorts (e.g., Diabetes, Hypertension, Asthma) across all top-level metrics.
- **Demographic Overviews**: High-level age and gender distribution charts.
- **Automated Narrative Findings**: Natural-language analytical insights generated dynamically to summarise peak utilization years, top visit drivers, and population age patterns.

### 2. 👥 Patient Analytics (`pages/1_Patient_Analytics.py`)
Detailed demographic segmentation and epidemiological cohort analysis across the entire synthetic patient population.
- **Age Cohort Distribution**: Granular age brackets (Pediatric, Young Adult, Middle Age, Senior) highlighting demographic distribution.
- **Diversity & Demographics**: Interactive breakdown of patient population by Gender, Race, and Ethnicity.
- **Payer & Coverage Analysis**: Distribution of healthcare coverage across insurance payers (Medicare, Medicaid, Dual Eligible, Commercial, Uninsured).
- **Vitals & Measurements by Cohort**: Cross-sectional analysis of clinical observations (e.g., Blood Pressure, BMI, Glucose) across age categories.
- **Searchable Patient Registry**: Interactive directory allowing filtering and selection of individual synthetic patients for deep-dive review.

### 3. 🩺 Diagnosis Analysis (`pages/2_Diagnosis_Analysis.py`)
Comprehensive analysis of disease prevalence, chronic illness burden, and clinical condition trends.
- **Disease Category Presets**: Instant filter dropdown for major disease categories including Diabetes, Hypertension, Asthma, Mental Health, Viral Infections, and Musculoskeletal disorders.
- **Prevalence vs. Occurrence**: Compares total diagnostic event counts against unique patient prevalence to differentiate between frequent exacerbations and widespread conditions.
- **Longitudinal Condition Trends**: Multi-year timeline tracking how diagnosis detection rates evolve over time.
- **Demographic Breakdown**: Cross-tabulation comparing diagnosis frequency across gender cohorts and age groups.
- **Diagnosis Explorer**: Fast, searchable table with ICD-10 / SNOMED condition descriptions and frequency metrics.

### 4. 📈 Visit Trends (`pages/3_Visit_Trends.py`)
Longitudinal utilization patterns and operational workflow analytics for hospital capacity planning.
- **Temporal Volume Analysis**: Multi-resolution encounter volume trends aggregated by Year, Month, or Day.
- **Encounter Class Breakdown**: Visualizes the proportion of Emergency department visits, Outpatient encounters, Inpatient admissions, Urgent Care, and Wellness checkups.
- **Length of Stay (LOS)**: Distribution of visit durations for inpatient stays and emergency admissions.
- **Data Export**: Clean aggregated visit summary tables with one-click CSV download for custom offline analysis.

### 5. 🔍 Patient Explorer (`pages/4_Patient_Explorer.py`)
A 360-degree longitudinal synthetic Electronic Health Record (EHR) viewer for individual patient case studies.
- **Patient Banner**: Key identity card showing synthetic Patient ID, age, birth date, gender, race, vital status, and total lifetime visits.
- **Longitudinal Clinical Timeline**: Chronological journey mapping every encounter throughout the patient's recorded history.
- **Detailed Clinical Subsections**:
  - **Encounters**: Chronological list of visit dates, encounter classes, and reason for admission.
  - **Conditions**: All documented active and historical diagnoses.
  - **Medications**: Prescribed drug regimens, dosages, and active treatment windows.
  - **Vitals & Observations**: Longitudinal tracking of lab measurements (Blood Pressure, BMI, Heart Rate, Cholesterol, Glucose).
- **Safe & Ethical**: Strictly synthetic data simulation with read-only access ensuring total patient privacy.

### 6. ✅ Data Quality & Management (`pages/5_Data_Quality.py`)
Data engineering governance, ETL validation, and dynamic dataset file management.
- **Ingestion & Cleaning Audit**: Compares raw input row counts against clean validated records, tracking removed duplicates and imputed values.
- **Missingness Matrix**: Column-by-column null value breakdown across all loaded clinical tables.
- **Referential Integrity Validation**: Identifies orphan records (e.g., encounters or conditions referencing unlisted patient IDs).
- **Temporal Sanity Checks**: Audits for invalid future dates, inverted encounter start/stop timestamps, or impossible patient ages.
- **📁 Dataset File Manager**: Allows users to dynamically upload new CSV files, inspect file schemas, and safely delete/replace existing tables directly through the browser with automatic cache invalidation.

---

### Global Features & Navigation
- **Universal Sidebar Filters**: Date range slider, age bracket multiselect, gender filter, encounter class selector, and condition preset picker that reactively update all charts across all pages.
- **Responsive Healthcare Theme**: Clean clinical teal-and-blue theme, mobile-optimized cards, and guaranteed zero-overflow horizontal layout.
- **Accessible & Interactive**: Clickable hospital logo navigation, and interactive Plotly visualizations with zoom and tooltips.

## Technology stack
Python 3.11+ · Streamlit · Pandas · NumPy · Plotly · Pytest. (SQLite is not used: the app has no persistent
settings that need it.)

## Project structure
```
hospital_patient_dashboard/
├── app.py                      # entry point: page shell + st.navigation router
├── pages/
│   ├── 0_Executive_Dashboard.py
│   ├── 1_Patient_Analytics.py
│   ├── 2_Diagnosis_Analysis.py
│   ├── 3_Visit_Trends.py
│   ├── 4_Patient_Explorer.py
│   └── 5_Data_Quality.py
├── src/
│   ├── data_loader.py          # find/read CSVs, schema-mapping layer, validation of required columns
│   ├── data_cleaning.py        # dates, duplicates, categories, orphan rows, ages, quality report
│   ├── analytics.py            # filters + all statistics (pure pandas, no UI imports)
│   ├── charts.py               # Plotly figure builders
│   ├── ui.py                   # Streamlit shell, sidebar, filters, cards, caching
│   ├── demo_data.py            # generator for the labelled DEMO dataset
│   └── utils.py                # shared constants (age groups), helpers
├── tests/                      # pytest suite using tiny synthetic fixtures (no download needed)
├── assets/logo.svg
├── .streamlit/config.toml      # theme (healthcare teal/blue)
├── data/README.md              # where the dataset goes
├── requirements.txt · pytest.ini · .gitignore · README.md
```
`app.py` is a router (`st.navigation`) so the sidebar labels are friendly; `pages/` holds the page scripts.

## Dataset & Pre-packaged 1K Synthea Sample
This repository comes pre-configured with the **1K Synthea Sample Dataset** in [`data/csv/`](file:///data/csv), so the dashboard runs out of the box with real synthetic healthcare data:
- `patients.csv` (1,163 patients)
- `encounters.csv` (61,459 encounters)
- `conditions.csv` (38,094 records)
- `observations.csv` (531,144 records)
- `medications.csv` (56,430 records)

You can also dynamically **upload**, **add**, or **delete** CSV files directly through the web UI via the **📁 Dataset File Manager** in the sidebar and on the **Data Quality** page.

### Expected Files and Columns
| File | Required Columns (Accepted Headers) | Optional Columns Used |
|---|---|---|
| `patients.csv` (required) | `Id` | `BIRTHDATE`, `DEATHDATE`, `GENDER`, `RACE`, `ETHNICITY` |
| `encounters.csv` (required) | `PATIENT`, `START` | `Id`, `STOP`, `ENCOUNTERCLASS`, `DESCRIPTION` |
| `conditions.csv` (required) | `PATIENT` and `DESCRIPTION` or `CODE` | `ENCOUNTER`, `START`, `STOP`, `CODE` |
| `observations.csv` (optional) | `PATIENT`, `DESCRIPTION` or `CODE` | `ENCOUNTER`, `DATE`, `VALUE`, `UNITS`, `TYPE` |
| `medications.csv` (optional) | `PATIENT`, `DESCRIPTION` or `CODE` | `ENCOUNTER`, `START`, `STOP` |

Headers are normalised (case/spacing) and mapped through the schema table in `src/data_loader.py` (`SCHEMA`), so
variants such as `patient_id`, `dob`, `sex` or `encounter_date` also work. **Only mapped columns are read**; names, addresses and other identifiers in the export are never loaded.

## Installation and Run

```bash
# Clone the repository
git clone https://github.com/ayankhann7/smart-ehr-dashboard.git
cd smart-ehr-dashboard

# Create virtual environment (optional but recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run automated tests
pytest -v

# Launch the Streamlit application
streamlit run app.py
```
The application will open in your default browser at `http://localhost:8501`.

## Deployment Options

### 1. Streamlit Community Cloud (Live Production App)
The application is live and hosted at:
👉 **[https://smart-ehr-dashboard-5j49yc9ggln4dbf8hghwvf.streamlit.app/](https://smart-ehr-dashboard-5j49yc9ggln4dbf8hghwvf.streamlit.app/)**

To deploy your own fork or updates:
1. Push changes to the `main` branch of your GitHub repository.
2. Sign in to [share.streamlit.io](https://share.streamlit.io/) with GitHub.
3. Streamlit Community Cloud automatically rebuilds and deploys updates on every push.

### 2. Vercel / Serverless Deployment
A `vercel.json` configuration file is included in this repository. 
When deploying on Vercel:
1. Connect your GitHub repository to Vercel.
2. Select **Python** as the runtime.
3. Deploy! (Note: Because Streamlit relies on WebSocket connections for live interactivity, Streamlit Community Cloud or Render/Docker is recommended for full real-time charting).

## Testing
`python -m pytest -v` runs the full test suite (39 unit tests) covering:
- CSV schema loading and header normalisation
- Missing file tolerance and helpful validation errors
- Error-tolerant date parsing and duplicate removal
- Anchored completed-age calculations
- Global reactive filter cascades and condition presets (Diabetes, Hypertension, Asthma, etc.)
- Dataset file manager (upload, list, and delete)
- Responsive Plotly figure builders

## Limitations
* Synthea is simulated: results reflect simulation rules, not real-world epidemiology.
* Ages are relative to the dataset's latest encounter date, not today.
* Read-only: no data entry or real clinical EHR usage (educational analytics only).
* Responsive design relies on Streamlit's layout plus scoped CSS.

## License
MIT License. Free for educational and research use.
