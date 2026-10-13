"""Dataset file management: upload, delete, and inspect CSV files.

Allows users to dynamically manage Synthea CSV exports or custom hospital data files
directly within the web dashboard.
"""
from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from . import data_loader

logger = logging.getLogger(__name__)

# Known file classifications
FILE_ROLES: dict[str, tuple[str, bool]] = {
    "patients.csv": ("Required: Patient Demographics", True),
    "encounters.csv": ("Required: Healthcare Visits", True),
    "conditions.csv": ("Required: Diagnoses & Conditions", True),
    "observations.csv": ("Optional: Lab Tests & Measurements", False),
    "medications.csv": ("Optional: Prescriptions & Meds", False),
    "procedures.csv": ("Additional: Clinical Procedures", False),
    "allergies.csv": ("Additional: Known Allergies", False),
    "immunizations.csv": ("Additional: Vaccines & Immunizations", False),
    "careplans.csv": ("Additional: Care Plans", False),
    "imaging_studies.csv": ("Additional: Imaging Studies", False),
    "devices.csv": ("Additional: Medical Devices", False),
    "supplies.csv": ("Additional: Supplies Used", False),
    "claims.csv": ("Additional: Billing & Claims", False),
    "payers.csv": ("Additional: Insurance Payers", False),
    "providers.csv": ("Additional: Healthcare Providers", False),
    "organizations.csv": ("Additional: Organizations & Facilities", False),
}


def format_bytes(num_bytes: int) -> str:
    """Format byte size into human-readable text."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_dataset_target_dir(base_dir: Path | str) -> Path:
    """Determine where CSV files reside or should be written.

    If an existing dataset directory is found (e.g. data/csv or data), return it.
    Otherwise default to base_dir/csv or base_dir.
    """
    base = Path(base_dir).resolve()
    found = data_loader.find_dataset_dir(base)
    if found is not None:
        return Path(found)
    
    # Check if a 'csv' subfolder exists
    csv_sub = base / "csv"
    if csv_sub.is_dir():
        return csv_sub
    
    # If base exists, use base, otherwise create base
    base.mkdir(parents=True, exist_ok=True)
    return base


def list_dataset_csv_files(folder: Path | str) -> list[dict[str, Any]]:
    """List all CSV files in the target directory with metadata."""
    folder = Path(folder)
    if not folder.is_dir():
        return []

    files = []
    for p in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
        if p.is_file() and p.suffix.lower() == ".csv":
            stat = p.stat()
            fname_lower = p.name.lower()
            role_desc, is_req = FILE_ROLES.get(
                fname_lower, ("Additional: Custom CSV File", False)
            )
            mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            files.append({
                "name": p.name,
                "path": p,
                "size_bytes": stat.st_size,
                "size_str": format_bytes(stat.st_size),
                "modified": mod_time,
                "role": role_desc,
                "is_required": is_req,
            })
    return files


def save_uploaded_csv(target_dir: Path | str, uploaded_file) -> tuple[bool, str]:
    """Save an uploaded file safely to target_dir. Validates extension."""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    name = Path(uploaded_file.name).name
    if not name.lower().endswith(".csv"):
        return False, f"'{name}' is not a CSV file."

    dest_path = target_dir / name
    try:
        content = uploaded_file.getvalue()
        if len(content) == 0:
            return False, f"'{name}' is empty."
        with open(dest_path, "wb") as f:
            f.write(content)
        logger.info("Saved uploaded file: %s (%d bytes)", dest_path, len(content))
        return True, f"Saved '{name}' ({format_bytes(len(content))}) successfully."
    except Exception as exc:
        logger.exception("Failed to write uploaded file %s", name)
        return False, f"Failed to save '{name}': {exc}"


def delete_csv_file(file_path: Path | str) -> tuple[bool, str]:
    """Safely delete a CSV file from disk."""
    p = Path(file_path)
    if not p.exists():
        return False, f"File '{p.name}' does not exist."
    if not p.is_file():
        return False, f"Path '{p.name}' is not a file."
    try:
        p.unlink()
        logger.info("Deleted file: %s", p)
        return True, f"Deleted '{p.name}' successfully."
    except Exception as exc:
        logger.exception("Failed to delete file %s", p.name)
        return False, f"Failed to delete '{p.name}': {exc}"


def render_file_manager(folder: Path | str, is_sidebar: bool = False, key_prefix: str = "fm") -> None:
    """Render the interactive upload, list, and delete UI for dataset CSV files."""
    target_dir = get_dataset_target_dir(folder)

    if not is_sidebar:
        st.markdown("### 📁 Dataset File Manager")
        st.markdown(
            f"Manage active CSV files in: `{target_dir}`. "
            "Upload new or replacement files, add additional tables, or remove unused files."
        )

    # 1. Uploader Section
    with st.container():
        uploaded = st.file_uploader(
            "Upload CSV file(s) (patients, encounters, conditions, etc.)",
            type=["csv"],
            accept_multiple_files=True,
            key=f"{key_prefix}_uploader",
            help="Drag and drop one or more CSV files to add or update records."
        )
        if uploaded:
            col1, col2 = st.columns([2, 3])
            with col1:
                if st.button("📥 Save & Process Files", type="primary", key=f"{key_prefix}_save_btn"):
                    saved_count = 0
                    errors = []
                    for uf in uploaded:
                        ok, msg = save_uploaded_csv(target_dir, uf)
                        if ok:
                            saved_count += 1
                        else:
                            errors.append(msg)
                    if saved_count:
                        st.cache_data.clear()
                        st.toast(f"Saved {saved_count} file(s) successfully!", icon="✅")
                        st.success(f"Saved {saved_count} file(s). Reloading dataset...")
                        st.rerun()
                    for err in errors:
                        st.error(err)
            with col2:
                st.caption(f"{len(uploaded)} file(s) selected ready to upload.")

    # 2. Existing Files List & Delete Controls
    files = list_dataset_csv_files(target_dir)

    if not files:
        st.warning(f"No CSV files found in `{target_dir}`. Please upload required files (`patients.csv`, `encounters.csv`, `conditions.csv`).")
        return

    if is_sidebar:
        st.caption(f"**Current files in folder** ({len(files)} total):")
        for f in files:
            cols = st.columns([4, 2])
            with cols[0]:
                st.markdown(f"**{f['name']}**  \n<small>{f['size_str']}</small>", unsafe_allow_html=True)
            with cols[1]:
                with st.popover("🗑️", help=f"Delete {f['name']}"):
                    st.write(f"Delete **{f['name']}**?")
                    if f["is_required"]:
                        st.warning("⚠️ Required table!")
                    if st.button("Confirm", key=f"{key_prefix}_sdel_{f['name']}", type="primary"):
                        ok, msg = delete_csv_file(f["path"])
                        if ok:
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(msg)
    else:
        # Full view table with controls
        st.markdown(f"#### Active Dataset Files ({len(files)} files)")

        # Quick summary stats
        total_size = sum(f["size_bytes"] for f in files)
        req_present = sum(1 for f in files if f["name"].lower() in ("patients.csv", "encounters.csv", "conditions.csv"))
        opt_present = sum(1 for f in files if f["name"].lower() in ("observations.csv", "medications.csv"))

        s1, s2, s3 = st.columns(3)
        s1.metric("Total Files", f"{len(files)}")
        s2.metric("Total Size", format_bytes(total_size))
        s3.metric("Required Tables", f"{req_present} of 3", delta="All loaded" if req_present == 3 else "Missing some", delta_color="normal" if req_present == 3 else "inverse")

        # Table rows with Delete action
        for f in files:
            row_cols = st.columns([3, 3, 2, 2, 2])
            with row_cols[0]:
                badge = "🔴 Required" if f["is_required"] else ("🟡 Optional" if "Optional" in f["role"] else "⚪ Additional")
                st.markdown(f"**{f['name']}**  \n`{badge}`")
            with row_cols[1]:
                st.caption(f"{f['role']}")
            with row_cols[2]:
                st.text(f"{f['size_str']}")
            with row_cols[3]:
                st.caption(f"{f['modified']}")
            with row_cols[4]:
                with st.popover("🗑️ Delete", help=f"Delete {f['name']}"):
                    st.warning(f"Delete `{f['name']}` from dataset?")
                    if f["is_required"]:
                        st.error("⚠️ This file is required by the dashboard. Deleting it will disable related views until re-uploaded.")
                    if st.button("Yes, delete file", key=f"{key_prefix}_del_{f['name']}", type="primary"):
                        ok, msg = delete_csv_file(f["path"])
                        if ok:
                            st.cache_data.clear()
                            st.toast(msg, icon="🗑️")
                            st.rerun()
                        else:
                            st.error(msg)
            st.divider()
