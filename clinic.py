import json
import os
from datetime import datetime, date
import pandas as pd
import streamlit as st

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

# Seed base Patient Registration database record map
get_state_val("patients_registry", {
    "P0001": {"name": "Yusuf Demir", "phone": "+90 532 123 4567", "center": "Istanbul Tower", "age": 28, "birth_date": "1998-05-12"},
    "P0002": {"name": "Amina El-Amin", "phone": "+90 555 987 6543", "center": "Elsifa Medical Center", "age": 9, "birth_date": "2017-08-20"}
})

# Central tooth history tracker
get_state_val("tooth_history_ledger", {
    "P0001": {
        "16": [{"date": "2026-02-15", "treatment": "Composite Filling", "center": "Istanbul Tower", "notes": "Mesial decay managed."}]
    }
})

# Working inputs memory anchors
get_state_val("session_patient_id", "P0001")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "Composite Filling")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")

# Add Patient Form Working States
get_state_val("new_pat_name", "")
get_state_val("new_pat_phone", "")
get_state_val("new_pat_birth", date(2000, 1, 1))
get_state_val("new_pat_center", "Istanbul Tower")

# Price Catalog Editor Working States
get_state_val("edit_cat_select", "Adult Dentistry")
get_state_val("edit_treat_select", "Composite Filling")
get_state_val("edit_price_val", 300.0)

# ==============================================================================
# RULE 4: CLEAN STATE CALLBACKS (PROCESS FLOW CONTROL)
# ==============================================================================
def cb_add_new_patient():
    """Generates next incremental ID and saves a fresh profile registry."""
    name = st.session_state.get("new_pat_name", "").strip()
    phone = st.session_state.get("new_pat_phone", "").strip()
    bdate = st.session_state.get("new_pat_birth")
    center = st.session_state.get("new_pat_center")
    
    if not name or not phone:
        st.sidebar.error("Validation Failed: Please fill in both Name and Phone Fields.")
        return
        
    registry = st.session_state.get("patients_registry", {})
    next_index = len(registry) + 1
    new_code = f"P{next_index:04d}"
    
    # Pre-calculate age inside callback
    today = date.today()
    calc_age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
    
    registry[new_code] = {
        "name": name,
        "phone": phone,
        "center": center,
        "age": max(0, calc_age),
        "birth_date": bdate.isoformat()
    }
    
    st.session_state["patients_registry"] = registry
    sync_input_to_db("patients_registry")
    
    # Flush fields to baseline defaults
    st.session_state["new_pat_name"] = ""
    st.session_state["new_pat_phone"] = ""
    sync_input_to_db("new_pat_name")
    sync_input_to_db("new_pat_phone")
    st.sidebar.success(f"Successfully registered patient {name} under {new_code}!")

def cb_update_treatment_price():
    """Updates the master tariff dictionary based on user adjustments."""
    cat = st.session_state.get("edit_cat_select")
    treat = st.session_state.get("edit_treat_select")
    new_price = st.session_state.get("edit_price_val", 0.0)
    
    catalog = st.session_state.get("treatment_catalog_db", {})
    if cat in catalog and treat in catalog[cat]:
        catalog[cat][treat] = float(new_price)
        st.session_state["treatment_catalog_db"] = catalog
        sync_input_to_db("treatment_catalog_db")
        st.sidebar.success(f"Updated price for '{treat}' to ${new_price:,.2f}")

def cb_sync_editor_fields():
    """Pre-fills current database rate inside the manual selection fields."""
    cat = st.session_state.get("edit_cat_select")
    treat = st.session_state.get("edit_treat_select")
    catalog = st.session_state.get("treatment_catalog_db", {})
    st.session_state["edit_price_val"] = catalog.get(cat, {}).get(treat, 0.0)

def cb_toggle_tooth_cell(tooth_str):
    """Processes real mouse vector state selections cleanly."""
    current_list = list(st.session_state.get("session_selected_teeth", []))
    if tooth_str in current_list:
        current_list.remove(tooth_str)
    else:
        current_list.append(tooth_str)
    st.session_state["session_selected_teeth"] = current_list
    sync_input_to_db("session_selected_teeth")

def cb_save_session_log():
    """Commits clinical operational entries straight into the persistent history matrix."""
    pid = st.session_state.get("session_patient_id")
    cat = st.session_state.get("session_category")
    treat = st.session_state.get("session_treatment")
    teeth = st.session_state.get("session_selected_teeth", [])
    notes = st.session_state.get("session_notes", "")
    
    if not teeth:
        st.sidebar.error("Operation Denied: Choose target teeth with your mouse grid.")
        return
        
    patients = st.session_state.get("patients_registry", {})
    center = patients.get(pid, {}).get("center", "Unassigned Center")
    history = st.session_state.get("tooth_history_ledger", {})
    
    if pid not in history:
        history[pid] = {}
        
    for t in teeth:
        if t not in history[pid]:
            history[pid][t] = []
        history[pid][t].append({
            "date": date.today().isoformat(),
            "treatment": f"[{cat}] {treat}",
            "center": center,
            "notes": notes
        })
        
    st.session_state["tooth_history_ledger"] = history
    sync_input_to_db("tooth_history_ledger")
    
    # Clean working parameters
    st.session_state["session_selected_teeth"] = []
    st.session_state["session_notes"] = ""
    sync_input_to_db("session_selected_teeth")
    sync_input_to_db("session_notes")

# ==============================================================================
# RULE 2: COMPUTATION VS UI (PRE-EVALUATE PIPELINES BEFORE THE RENDERING PASS)
# ==============================================================================
patients_db = st.session_state.get("patients_registry", {})
catalog_db = st.session_state.get("treatment_catalog_db", {})
history_db = st.session_state.get("tooth_history_ledger", {})

active_pid = st.session_state.get("session_patient_id", "P0001")
active_cat = st.session_state.get("session_category", "Adult Dentistry")
active_treat = st.session_state.get("session_treatment", "")
active_teeth = st.session_state.get("session_selected_teeth", [])

# Financial computations boundary check
unit_price = catalog_db.get(active_cat, {}).get(active_treat, 0.0)
teeth_multiplier = len(active_teeth) if len(active_teeth) > 0 else 1
computed_gross_cost = unit_price * teeth_multiplier

# Formulate display formats
patient_selectors_map = {k: f"{v['name']} [{k}] - {v['center']}" for k, v in patients_db.items()}

# ==============================================================================
# RULE 3: HTML PRINT AND MOBILE PDF ENGINE FOR PASSPORTS
# ==============================================================================
def compile_passport_report(p_id, meta, full_logs):
    rows = ""
    if p_id in full_logs:
        for tooth, actions in full_logs[p_id].items():
            for a in actions:
                rows += f"<tr><td><b>Tooth {tooth}</b></td><td>{a['date']}</td><td>{a['treatment']}</td><td>{a['center']}</td><td>{a['notes']}</td></tr>"
    if not rows:
        rows = "<tr><td colspan='5' style='text-align:center; color:#777;'>No matching chart files saved.</td></tr>"
        
    return f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, sans-serif; margin: 20px; }}
        .head {{ display: flex; justify-content: space-between; border-bottom: 2px solid #047857; padding-bottom: 10px; }}
        table {{ width:100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f3f4f6; }}
        .btn {{ background:#047857; color:white; border:none; padding:8px 16px; border-radius:4px; font-weight:bold; cursor:pointer; }}
        @media print {{ .btn {{ display:none; }} }}
    </style></head><body>
    <div class="head">
        <div><h2>Dental Medical Record Passport</h2><p>Patient: {meta.get('name')} | Base: {meta.get('center')}</p></div>
        <button class="btn" onclick="window.print()">Print Report / PDF</button>
    </div>
    <table><thead><tr><th>Location</th><th>Date</th><th>Treatment Implemented</th><th>Clinic Center Location</th><th>Clinical Session Notes</th></tr></thead>
    <tbody>{rows}</tbody></table></body></html>
    """

passport_html = compile_passport_report(active_pid, patients_db.get(active_pid, {}), history_db)

# ==============================================================================
# UI VISUAL PRESENTATION LAYOUT LAYER
# ==============================================================================
st.set_page_config(page_title="Havence Professional Dental Matrix", layout="wide")

# Inject responsive style patches so button rows resemble a mouse dental grid grid canvas mapping
st.markdown("""
<style>
    div.stButton > button { width: 100% !important; padding: 4px 2px !important; font-size: 11px !important; margin: 0px !important; }
    .tooth-header { text-align: center; font-weight: bold; font-size: 13px; color: #4b5563; margin-top: 8px; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

st.title("🦷 Havence Clinical Dental Workspace")
st.markdown("---")

tab_sessions, tab_patients, tab_prices = st.tabs([
    "🩺 Interactive Session Planner",
    "👥 Patient Admissions Database",
    "💰 Fee & Treatment Price Editor"
])

# ------------------------------------------------------------------------------
# TAB 1: INTERACTIVE WORKSPACE & TARGET MOUSE GRID
# ------------------------------------------------------------------------------
with tab_sessions:
    l_box, r_box = st.columns([2, 3])
    
    with l_box:
        st.subheader("Clinical Parameters")
        st.selectbox("Select Patient Target File", options=list(patient_selectors_map.keys()), format_func=lambda x: patient_selectors_map[x], key="session_patient_id", on_change=sync_input_to_db, args=("session_patient_id",))
        
        st.selectbox("Dentistry Classification Group", options=list(catalog_db.keys()), key="session_category", on_change=sync_input_to_db, args=("session_category",))
        
        selectable_treatments = list(catalog_db.get(st.session_state.get("session_category"), {}).keys())
        st.selectbox("Target Care Treatment Protocol", options=selectable_treatments, key="session_treatment", on_change=sync_input_to_db, args=("session_treatment",))
        
        st.text_area("Clinical Session Operations Log Entries", key="session_notes", on_change=sync_input_to_db, args=("session_notes",))
        
        st.markdown("### Transaction Matrix")
        m1, m2 = st.columns(2)
        m1.metric("Catalog Base Price", f"${unit_price:,.2f}")
        m2.metric("Calculated Accumulated Cost", f"${computed_gross_cost:,.2f}")
        
        st.button("💾 Commit Operations Plan to History File", on_click=cb_save_session_log, type="primary")

    with r_box:
        st.subheader("Mouse-Driven Graphical Odontogram Chart Layout")
        st.caption("Click on individual blocks below using your mouse cursor to toggle dental quadrants.")
        
        u_arch_1 = ["18", "17", "16", "15", "14", "13", "12", "11"]
        u_arch_2 = ["21", "22", "23", "24", "25", "26", "27", "28"]
        l_arch_1 = ["48", "47", "46", "45", "44", "43", "42", "41"]
        l_arch_2 = ["31", "32", "33", "34", "35", "36", "37", "38"]

        st.markdown("<div class='tooth-header'>Upper Maxillary Jaw Arch Quadrants</div>", unsafe_allow_html=True)
        cols_u1 = st.columns(8)
        for idx, t in enumerate(u_arch_1):
            lbl = f"🟢\n{t}" if t in active_teeth else f"⬜\n{t}"
            cols_u1[idx].button(lbl, key=f"m_u1_{t}", on_click=cb_toggle_tooth_cell, args=(t,))
            
        cols_u2 = st.columns(8)
        for idx, t in enumerate(u_arch_2):
            lbl = f"🟢\n{t}" if t in active_teeth else f"⬜\n{t}"
            cols_u2[idx].button(lbl, key=f"m_u2_{t}", on_click=cb_toggle_tooth_cell, args=(t,))
            
        st.markdown("<div class='tooth-header'>Lower Mandibular Jaw Arch Quadrants</div>", unsafe_allow_html=True)
        cols_l1 = st.columns(8)
        for idx, t in enumerate(l_arch_1):
            lbl = f"🟢\n{t}" if t in active_teeth else f"⬜\n{t}"
            cols_l1[idx].button(lbl, key=f"m_l1_{t}", on_click=cb_toggle_tooth_cell, args=(t,))
            
        cols_l2 = st.columns(8)
        for idx, t in enumerate(l_arch_2):
            lbl = f"🟢\n{t}" if t in active_teeth else f"⬜\n{t}"
            cols_l2[idx].button(lbl, key=f"m_l2_{t}", on_click=cb_toggle_tooth_cell, args=(t,))

# ------------------------------------------------------------------------------
# TAB 2: PATIENT ADMISSIONS & CHRONOLOGICAL HISTORY MATRIX
# ------------------------------------------------------------------------------
with tab_patients:
    st.subheader("Manage Medical Profiles")
    
    col_adm_1, col_adm_2 = st.columns([1, 2])
    
    with col_adm_1:
        st.info("#### ➕ Patient Registry Intake Form")
        st.text_input("Patient Full Name", key="new_pat_name", on_change=sync_input_to_db, args=("new_pat_name",))
        st.text_input("Active Mobile Phone Number", key="new_pat_phone", on_change=sync_input_to_db, args=("new_pat_phone",))
        st.date_input("Patient Birth Date", key="new_pat_birth", on_change=sync_input_to_db, args=("new_pat_birth",))
        st.selectbox("Primary Medical Center Location Facility", options=CENTERS, key="new_pat_center", on_change=sync_input_to_db, args=("new_pat_center",))
        st.button("🚀 Complete Registration Intake Run", on_click=cb_add_new_patient, use_container_width=True)
        
        st.markdown("---")
        st.download_button("📱 Export Complete File Passport", data=passport_html, file_name=f"passport_{active_pid}.html", mime="text/html", use_container_width=True)

    with col_adm_2:
        st.write("#### 🔍 Timeline Audit Logs Per Tooth Row")
        all_ordered_teeth = u_arch_1 + u_arch_2 + l_arch_1 + l_arch_2
        target_view_tooth = st.selectbox("Isolate Tooth Target Location Code for Inspection", options=all_ordered_teeth, index=2)
        
        active_patient_logs = history_db.get(active_pid, {}).get(target_view_tooth, [])
        
        if active_patient_logs:
            df_display = pd.DataFrame(active_patient_logs)[["date", "treatment", "center", "notes"]]
            df_display.columns = ["Date Performed", "Surgical Action Plan Implemented", "Clinic Core Center Base", "Notes Logged"]
            st.table(df_display)
        else:
            st.warning(f"No previous clinical records or treatment sessions registered for Tooth {target_view_tooth} on this file ID.")

# ------------------------------------------------------------------------------
# TAB 3: MASTER PRICE CATALOG REGISTRY EDITOR
# ------------------------------------------------------------------------------
with tab_prices:
    st.subheader("Master Dentistry Rate Matrix Configurations")
    
    p_ed_col1, p_ed_col2 = st.columns([1, 2])
    
    with p_ed_col1:
        st.info("#### ✏️ Tariff Management Panel")
        st.selectbox("Select Classification Sector", options=list(catalog_db.keys()), key="edit_cat_select", on_change=cb_sync_editor_fields)
        
        sub_treats = list(catalog_db.get(st.session_state.get("edit_cat_select"), {}).keys())
        st.selectbox("Target Operation Protocol", options=sub_treats, key="edit_treat_select", on_change=cb_sync_editor_fields)
        
        st.number_input("Standard Fee Base Rate Value ($)", step=10.0, key="edit_price_val", on_change=sync_input_to_db, args=("edit_price_val",))
        st.button("💾 Apply Updated Price Configuration", on_click=cb_update_treatment_price, use_container_width=True, type="primary")
        
    with p_ed_col2:
        st.write("#### 📋 Real-Time Core Catalog Fee Schedule Rows")
        flat_records = []
        for category, item_map in catalog_db.items():
            for item, rate in item_map.items():
                flat_records.append({"Classification Category": category, "Medical Treatment Specification": item, "Configured Base Fee Schedule": f"${rate:,.2f}"})
        st.dataframe(pd.DataFrame(flat_records), use_container_width=True, hide_index=True)
