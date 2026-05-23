import json
import os
from datetime import datetime, date
import pandas as pd
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates

# ==============================================================================
# RULE 1: DATA PERSISTENCE (JSON ENGINE WITH STATE MIRRORING)
# ==============================================================================
DB_FILE = "dental_app_data.json"

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, default=json_serial, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Critical Data Save Error: {e}")

def get_state_val(key, default_value):
    db_data = load_db()
    if key not in st.session_state:
        if key in db_data:
            val = db_data[key]
            if isinstance(default_value, date) and isinstance(val, str):
                try:
                    st.session_state[key] = datetime.fromisoformat(val).date()
                except ValueError:
                    st.session_state[key] = default_value
            else:
                st.session_state[key] = val
        else:
            st.session_state[key] = default_value
    return st.session_state[key]

def sync_input_to_db(key):
    if key in st.session_state:
        db_data = load_db()
        db_data[key] = st.session_state[key]
        save_db(db_data)

# ==============================================================================
# STATE SEEDING & PRICING REGISTRY INITIALIZATION
# ==============================================================================
CENTERS = ["Istanbul Tower", "Elsifa Medical Center"]

# Path to your uploaded tooth diagram
TOOTH_DIAGRAM_PATH = "tooth_grid.png" # Place your uploaded image as this filename in the app directory

# Master definition of Click Zones [x_min, y_min, x_max, y_max, label]
# Based on common tooth mapping for your diagram
CLICK_ZONES = [
    # Top Row (Deciduous & Permanent)
    [31, 28, 97, 85, "1.8"], [115, 28, 180, 85, "1.7"], [200, 28, 271, 85, "1.6"], [289, 28, 353, 85, "1.5"], [374, 28, 437, 85, "1.4"], [456, 28, 517, 85, "1.3"], [539, 28, 600, 85, "1.2"], [623, 28, 680, 85, "1.1"],
    [717, 28, 773, 85, "2.1"], [798, 28, 855, 85, "2.2"], [877, 28, 936, 85, "2.3"], [959, 28, 1022, 85, "2.4"], [1042, 28, 1109, 85, "2.5"], [1129, 28, 1201, 85, "2.6"], [1219, 28, 1286, 85, "2.7"], [1305, 28, 1373, 85, "2.8"],
    # Middle Row (Adult/Labels)
    [290, 105, 350, 163, "Upper Right Q"], [370, 105, 437, 163, "Upper Right Q"], [457, 105, 517, 163, "Upper Left Q"], [539, 105, 597, 163, "Upper Left Q"],
    [31, 218, 95, 275, "4.8"], [117, 218, 178, 275, "4.7"], [200, 218, 271, 275, "4.6"], [289, 218, 350, 275, "4.5"], [373, 218, 437, 275, "4.4"], [456, 218, 517, 275, "4.3"], [539, 218, 598, 275, "4.2"], [623, 218, 681, 275, "4.1"],
    [717, 218, 774, 275, "3.1"], [797, 218, 856, 275, "3.2"], [877, 218, 937, 275, "3.3"], [959, 218, 1022, 275, "3.4"], [1042, 218, 1107, 275, "3.5"], [1129, 218, 1200, 275, "3.6"], [1218, 218, 1286, 275, "3.7"], [1305, 218, 1373, 275, "3.8"],
]

# Seed initial customizable Treatment Prices Database matching your file models
get_state_val("treatment_catalog_db", {
    "Children Dentistry": {
        "Fluoride Application": 150.0,
        "Fissure Sealant": 200.0,
        "Pediatric Extraction": 250.0,
        "Pulpotomy": 450.0
    },
    "Adult Dentistry": {
        "Composite Filling": 300.0,
        "Root Canal Treatment (RCT)": 800.0,
        "Porcelain Crown": 1200.0,
        "Deep Scaling & Polishing": 350.0,
        "Surgical Tooth Extraction": 700.0
    }
})

# Base Patient Registration records
get_state_val("patients_registry", {
    "P0001": {"name": "Yusuf Demir", "phone": "+90 532 123 4567", "center": "Istanbul Tower", "age": 28, "birth_date": "1998-05-12"},
    "P0002": {"name": "Amina El-Amin", "phone": "+90 555 987 6543", "center": "Elsifa Medical Center", "age": 9, "birth_date": "2017-08-20"}
})

# Central tooth history tracker
get_state_val("tooth_history_ledger", {
    "P0001": {
        "16 Mesial": [{"date": "2026-02-15", "treatment": "Composite Filling", "center": "Istanbul Tower", "notes": "Mesial decay managed."}]
    }
})

# Working inputs memory anchors
get_state_val("session_patient_id", "P0001")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "Composite Filling")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")

# Add Patient Form States
get_state_val("new_pat_name", "")
get_state_val("new_pat_phone", "")
get_state_val("new_pat_birth", date(2000, 1, 1))
get_state_val("new_pat_center", CENTERS[0])

# Price Catalog Editor States
get_state_val("edit_cat_select", "Adult Dentistry")
get_state_val("edit_treat_select", "Composite Filling")
get_state_val("edit_price_val", 300.0)

# ==============================================================================
# RULE 4: CLEAN STATE CALLBACKS (PROCESS FLOW CONTROL)
# ==============================================================================
def cb_add_new_patient():
    name = st.session_state.get("new_pat_name", "").strip()
    phone = st.session_state.get("new_pat_phone", "").strip()
    bdate = st.session_state.get("new_pat_birth")
    center = st.session_state.get("new_pat_center")
    if not name or not phone: return
    registry = st.session_state.get("patients_registry", {})
    new_code = f"P{len(registry)+1:04d}"
    registry[new_code] = {"name": name, "phone": phone, "center": center, "age": date.today().year - bdate.year, "birth_date": bdate.isoformat()}
    st.session_state["patients_registry"] = registry
    sync_input_to_db("patients_registry")
    for k in ["new_pat_name", "new_pat_phone"]: st.session_state[k] = ""
    st.sidebar.success(f"Registered patient {name} under {new_code}!")

def cb_update_treatment_price():
    catalog = st.session_state.get("treatment_catalog_db", {})
    catalog[st.session_state["edit_cat_select"]][st.session_state["edit_treat_select"]] = float(st.session_state["edit_price_val"])
    st.session_state["treatment_catalog_db"] = catalog
    sync_input_to_db("treatment_catalog_db")

def cb_toggle_tooth_label(label_str):
    current_list = list(st.session_state.get("session_selected_teeth", []))
    if label_str in current_list: current_list.remove(label_str)
    else: current_list.append(label_str)
    st.session_state["session_selected_teeth"] = current_list
    sync_input_to_db("session_selected_teeth")

def cb_save_session_log():
    pid, cat, treat, teeth = st.session_state["session_patient_id"], st.session_state["session_category"], st.session_state["session_treatment"], st.session_state["session_selected_teeth"]
    if not teeth: return
    center = st.session_state["patients_registry"][pid]["center"]
    history = st.session_state.get("tooth_history_ledger", {})
    if pid not in history: history[pid] = {}
    for t in teeth:
        if t not in history[pid]: history[pid][t] = []
        history[pid][t].append({"date": date.today().isoformat(), "treatment": f"[{cat}] {treat}", "center": center, "notes": st.session_state["session_notes"]})
    st.session_state["tooth_history_ledger"] = history
    sync_input_to_db("tooth_history_ledger")
    st.session_state["session_selected_teeth"] = []
    st.session_state["session_notes"] = ""

# ==============================================================================
# RULE 2: COMPUTATION VS UI (PRE-EVALUATE PIPELINES)
# ==============================================================================
patients_db, catalog_db, history_db = st.session_state["patients_registry"], st.session_state["treatment_catalog_db"], st.session_state["tooth_history_ledger"]
active_teeth = st.session_state["session_selected_teeth"]

unit_price = catalog_db[st.session_state["session_category"]].get(st.session_state["session_treatment"], 0.0)
gross_cost = unit_price * max(len(active_teeth), 1)

patient_selectors = {k: f"{v['name']} [{k}]" for k, v in patients_db.items()}

# ==============================================================================
# UI VISUAL PRESENTATION LAYOUT LAYER
# ==============================================================================
st.set_page_config(page_title="Havence Dental Diagram Workspace", layout="wide")
st.title("🦷 Havence Clinical Diagram Workspace")
st.markdown("---")

tab_sessions, tab_adm = st.tabs(["🩺 Diagram Session Planner", "👥 Patient Admissions & Catalog"])

# ------------------------------------------------------------------------------
# TAB 1: DIAGRAM SESSION PLANNER
# ------------------------------------------------------------------------------
with tab_sessions:
    l_box, r_box = st.columns([2, 3])
    with l_box:
        st.subheader("Session Parameters")
        st.selectbox("Select Patient", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="session_patient_id", on_change=sync_input_to_db, args=("session_patient_id",))
        st.selectbox("Category", options=list(catalog_db.keys()), key="session_category", on_change=sync_input_to_db, args=("session_category",))
        st.selectbox("Treatment", options=list(catalog_db[st.session_state.get("session_category", "Adult Dentistry")].keys()), key="session_treatment", on_change=sync_input_to_db, args=("session_treatment",))
        st.text_area("Operations Log", key="session_notes", on_change=sync_input_to_db, args=("session_notes",))
        
        st.markdown("### Transaction Matrix")
        m1, m2 = st.columns(2)
        m1.metric("Catalog Base Price", f"${unit_price:,.2f}")
        m2.metric("Calculated Accumulated Cost", f"${gross_cost:,.2f}")
        st.button("💾 Commit Operations Plan", on_click=cb_save_session_log, type="primary")

    with r_box:
        st.subheader("Interactive Odontogram Diagram")
        st.caption("Tap/Click on any tooth, deciduous cluster, or quadrant label to select them for this treatment session.")
        
        # DISPLAY IMAGE AND CATCH CLICKS
        # Image is displayed at original resolution; coordinates must match image mapping definition
        if not os.path.exists(TOOTH_DIAGRAM_PATH):
            st.error(f"Missing Image: Place your dental diagram named '{TOOTH_DIAGRAM_PATH}' in the app directory.")
        else:
            value = streamlit_image_coordinates(TOOTH_DIAGRAM_PATH, use_column_width=False, key="click_map")
            
            # HANDLE CLICKS (Find zone matching click coordinates)
            if value is not None:
                x, y = value['x'], value['y']
                for z in CLICK_ZONES:
                    if z[0] <= x <= z[2] and z[1] <= y <= z[3]:
                        cb_toggle_tooth_label(z[4])
                        # Force rerun to immediately show results on the left column (Streamlit specific need)
                        st.experimental_rerun()
                # (Else click was outside any mapped tooth zone)

            # Inform user about their selections
            if active_teeth:
                st.info(f"Active Selection Matrix: **{', '.join(sorted(active_teeth))}**")
            else:
                st.warning("Click on the diagram to select teeth/regions.")

# ------------------------------------------------------------------------------
# TAB 2: PATIENT ADMISSIONS & CATALOG MANAGEMENT
# ------------------------------------------------------------------------------
with tab_adm:
    col_adm_1, col_adm_2 = st.columns(2)
    with col_adm_1:
        st.info("#### ➕ Patient Registry Intake Form")
        st.text_input("Full Name", key="new_pat_name")
        st.text_input("Mobile Phone", key="new_pat_phone")
        st.date_input("Birth Date", key="new_pat_birth")
        st.selectbox("Facility Base", options=CENTERS, key="new_pat_center")
        st.button("🚀 Register Intake", on_click=cb_add_new_patient, use_container_width=True)
    with col_adm_2:
        st.info("#### ✏️ Catalog Tariff Editor")
        st.selectbox("Category Sector", options=list(catalog_db.keys()), key="edit_cat_select")
        st.selectbox("Treatment Protocol", options=list(catalog_db.get(st.session_state.get("edit_cat_select", "Adult Dentistry"), {}).keys()), key="edit_treat_select")
        st.number_input("Standard Fee Schedule ($)", step=10.0, key="edit_price_val")
        st.button("💾 Apply Updated Price", on_click=cb_update_treatment_price, use_container_width=True, type="primary")
