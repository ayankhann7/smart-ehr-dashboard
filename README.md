# Hospital Patient Data Analytics & Smart EHR Dashboard

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

## Features
| Page | What it does |
|---|---|
| **Executive Dashboard** | Unique patients, encounters, condition records, average age; age, gender, top-condition, encounter-class and time charts; auto-generated descriptive findings |
| **Patient Analytics** | Age groups, population summary, counts by gender/race/ethnicity, searchable patient-ID list, optional measurements by age group |
| **Diagnosis Analysis** | Top-N conditions (records vs. unique patients), searchable table, conditions over time, demographic comparison |
| **Visit Trends** | Daily/monthly/yearly encounters, class distribution and comparison, aggregated table + CSV |
| **Patient Explorer** | One synthetic patient: encounters, conditions, observations, medications (read-only) |
| **Data Quality** | Files loaded, original vs. cleaned counts, missing values, duplicates, invalid dates, unmatched IDs, cleaning log, CSV downloads |

Also: global filters (date range, age, gender, encounter class, condition) with a reset button, a dataset status
indicator, a setup screen when files are missing, and a clearly labelled **demo dataset** option.

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
git clone <your-repo-url>
cd hospital_patient_dashboard

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

### 1. Streamlit Community Cloud (Recommended & 1-Click Free Hosting)
1. Push this repository to your GitHub account.
2. Sign in to [share.streamlit.io](https://share.streamlit.io/) with GitHub.
3. Click **"New app"**, select your repository, branch (`main`), and set **Main file path** to `app.py`.
4. Click **Deploy!** Streamlit handles WebSockets, persistent memory, and live updates automatically.

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
