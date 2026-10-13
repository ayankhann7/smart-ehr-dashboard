# Dataset folder

Put the **Synthea CSV export** here (or in a `csv/` sub-folder, which is how Synthea ZIP files unpack):

| File | Status |
|---|---|
| `patients.csv` | required |
| `encounters.csv` | required |
| `conditions.csv` | required |
| `observations.csv` | optional |
| `medications.csv` | optional |

Download page: <https://synthetichealth.github.io/downloads.html> (choose a sample **CSV** set; the 1K-patient set is plenty for a first run).

## Why the data is not committed

* Synthea exports are large (tens to hundreds of MB), which bloats a Git repository permanently.
* The files are regenerable/downloadable from the official source, so there is nothing to preserve.
* `.gitignore` excludes everything in this folder except this README.

You can also point the app at another folder with the sidebar *Data folder* box or the `EHR_DATA_DIR` environment variable.

`data/demo/` is created only if you click *Generate demo dataset*. It holds randomly generated demo data (marked by `DEMO_DATASET.txt`) and is **not** Synthea output.
