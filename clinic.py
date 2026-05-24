import json
import os
from datetime import datetime, date
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. CENTRAL DATA PERSISTENCE LAYER
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
        st.error(f"Data Save Failure: {e}")

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
# DATABASE SEEDING
# ==============================================================================
CENTERS = ["Istanbul Tower", "Elsifa Medical Center"]

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

get_state_val("patients_registry", {
    "P0001": {"name": "Yusuf Demir", "phone": "+90 532 123 4567", "center": "Istanbul Tower", "age": 28, "birth_date": "1998-05-12"},
    "P0002": {"name": "Amina El-Amin", "phone": "+90 555 987 6543", "center": "Elsifa Medical Center", "age": 9, "birth_date": "2017-08-20"}
})

get_state_val("tooth_history_ledger", {
    "P0001": {
        "16": [{"date": "2026-02-15", "treatment": "Composite Filling", "center": "Istanbul Tower", "notes": "Mesial decay managed."}]
    }
})

# Form Input Memory Hooks
get_state_val("session_patient_id", "P0001")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "Composite Filling")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")

get_state_val("new_pat_name", "")
get_state_val("new_pat_phone", "")
get_state_val("new_pat_birth", date(2000, 1, 1))
get_state_val("new_pat_center", CENTERS[0])

get_state_val("edit_cat_select", "Adult Dentistry")
get_state_val("edit_treat_select", "Composite Filling")
get_state_val("edit_price_val", 300.0)

# ==============================================================================
# STATE CALLBACK OPERATIONS
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
    st.session_state["new_pat_name"] = ""
    st.session_state["new_pat_phone"] = ""

def cb_update_treatment_price():
    catalog = st.session_state.get("treatment_catalog_db", {})
    catalog[st.session_state["edit_cat_select"]][st.session_state["edit_treat_select"]] = float(st.session_state["edit_price_val"])
    st.session_state["treatment_catalog_db"] = catalog
    sync_input_to_db("treatment_catalog_db")

def cb_toggle_grid_tooth(tooth_id):
    current = list(st.session_state.get("session_selected_teeth", []))
    if tooth_id in current:
        current.remove(tooth_id)
    else:
        current.append(tooth_id)
    st.session_state["session_selected_teeth"] = current
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
# DATA COMPUTATION PRE-EXECUTION
# ==============================================================================
patients_db = st.session_state.get("patients_registry", {})
catalog_db = st.session_state.get("treatment_catalog_db", {})
history_db = st.session_state.get("tooth_history_ledger", {})
active_teeth = st.session_state.get("session_selected_teeth", [])

unit_price = catalog_db[st.session_state["session_category"]].get(st.session_state["session_treatment"], 0.0)
gross_cost = unit_price * max(len(active_teeth), 1)

patient_selectors = {k: f"{v['name']} [{k}]" for k, v in patients_db.items()}

# ==============================================================================
# UI RENDERING & INLINE STYLING
# ==============================================================================
st.set_page_config(page_title="Havence Dental Manager", layout="wide")

# CSS to optimize the dental mapping grid layout
st.markdown("""
<style>
    div.stButton > button { width: 100% !important; padding: 6px 0px !important; font-size: 13px !important; font-weight: bold !important; }
    .jaw-title { text-align: center; font-weight: bold; background-color: #1f2937; color: white; padding: 4px; border-radius: 4px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

st.title("🦷 Havence Clinical Dental Management System")
st.markdown("---")

tab_sessions, tab_patients, tab_prices = st.tabs([
    "🩺 Active Session Desk", 
    "👥 Patient Records Registry", 
    "💰 Fee Catalog Database"
])

# ------------------------------------------------------------------------------
# TAB 1: OPERATIONAL WORKSPACE
# ------------------------------------------------------------------------------
with tab_sessions:
    l_box, r_box = st.columns([2, 3])
    
    with l_box:
        st.subheader("Treatment Setup")
        st.selectbox("Patient Selection File", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="session_patient_id", on_change=sync_input_to_db, args=("session_patient_id",))
        st.selectbox("Age Bracket Group", options=list(catalog_db.keys()), key="session_category", on_change=sync_input_to_db, args=("session_category",))
        st.selectbox("Procedure Plan", options=list(catalog_db[st.session_state.get("session_category", "Adult Dentistry")].keys()), key="session_treatment", on_change=sync_input_to_db, args=("session_treatment",))
        st.text_area("Clinical Case Notes", key="session_notes", on_change=sync_input_to_db, args=("session_notes",))
        
        st.markdown("### Transaction Invoicing")
        m1, m2 = st.columns(2)
        m1.metric("Procedure Unit Cost", f"${unit_price:,.2f}")
        m2.metric("Total Calculated Due", f"${gross_cost:,.2f}")
        st.button("💾 Commit Treatment Session to File", on_click=cb_save_session_log, type="primary")

    with r_box:
        st.subheader("Interactive Mouse Mapping Grid")
        st.caption("Click on individual blocks to match the active treatment target regions.")
        
        # Display the visual diagram as a guide directly above the tracking grid
        if os.path.exists("tooth_grid.png"):
            st.image("tooth_grid.png", use_column_width=True)
            
        u_quad1 = ["18", "17", "16", "15", "14", "13", "12", "11"]
        u_quad2 = ["21", "22", "23", "24", "25", "26", "27", "28"]
        l_quad1 = ["48", "47", "46", "45", "44", "43", "42", "41"]
        l_quad2 = ["31", "32", "33", "34", "35", "36", "37", "38"]

        st.markdown("<div class='jaw-title'>Upper Maxillary Jaw Arch</div>", unsafe_allow_html=True)
        cols_u1 = st.columns(8)
        for idx, t in enumerate(u_quad1):
            lbl = f"🟢 {t}" if t in active_teeth else f"⬜ {t}"
            cols_u1[idx].button(lbl, key=f"btn_u1_{t}", on_click=cb_toggle_grid_tooth, args=(t,))
            
        cols_u2 = st.columns(8)
        for idx, t in enumerate(u_quad2):
            lbl = f"🟢 {t}" if t in active_teeth else f"⬜ {t}"
            cols_u2[idx].button(lbl, key=f"btn_u2_{t}", on_click=cb_toggle_grid_tooth, args=(t,))
            
        st.markdown("<div class='jaw-title'>Lower Mandibular Jaw Arch</div>", unsafe_allow_html=True)
        cols_l1 = st.columns(8)
        for idx, t in enumerate(l_quad1):
            lbl = f"🟢 {t}" if t in active_teeth else f"⬜ {t}"
            cols_l1[idx].button(lbl, key=f"btn_l1_{t}", on_click=cb_toggle_grid_tooth, args=(t,))
            
        cols_l2 = st.columns(8)
        for idx, t in enumerate(l_quad2):
            lbl = f"🟢 {t}" if t in active_teeth else f"⬜ {t}"
            cols_l2[idx].button(lbl, key=f"btn_l2_{t}", on_click=cb_toggle_grid_tooth, args=(t,))

        if active_teeth:
            st.info(f"Currently Target Teeth Elements: **{', '.join(sorted(active_teeth))}**")

# ------------------------------------------------------------------------------
# TAB 2: PATIENT REGISTRY & LOOKUP HISTORY
# ------------------------------------------------------------------------------
with tab_patients:
    col_adm_1, col_adm_2 = st.columns([1, 2])
    with col_adm_1:
        st.info("#### ➕ New Patient Registration")
        st.text_input("Full Patient Name", key="new_pat_name")
        st.text_input("Mobile Contact Phone", key="new_pat_phone")
        st.date_input("Date of Birth", key="new_pat_birth")
        st.selectbox("Assigned Medical Facility", options=CENTERS, key="new_pat_center")
        st.button("🚀 Register Patient File", on_click=cb_add_new_patient, use_container_width=True)
    
    with col_adm_2:
        st.write("#### 🔍 Patient Tooth History Breakdown")
        target_tooth = st.selectbox("Select Target Tooth to Isolate History Logs", options=u_quad1+u_quad2+l_quad1+l_quad2)
        
        active_patient_logs = history_db.get(st.session_state["session_patient_id"], {}).get(target_tooth, [])
        if active_patient_logs:
            df_display = pd.DataFrame(active_patient_logs)[["date", "treatment", "center", "notes"]]
            df_display.columns = ["Treatment Date", "Procedure Implemented", "Clinic Center", "Clinical Notes"]
            st.table(df_display)
        else:
            st.warning(f"No entry or treatment actions registered on Tooth {target_tooth} for this patient.")

# ------------------------------------------------------------------------------
# TAB 3: PRICE CATALOG EDIT MATRIX
# ------------------------------------------------------------------------------
with tab_prices:
    p_ed_col1, p_ed_col2 = st.columns([1, 2])
    with p_ed_col1:
        st.info("#### ✏️ Tariff Price Customization Panel")
        st.selectbox("Select Core Domain Category", options=list(catalog_db.keys()), key="edit_cat_select")
        st.selectbox("Select Target Procedure", options=list(catalog_db.get(st.session_state.get("edit_cat_select", "Adult Dentistry"), {}).keys()), key="edit_treat_select")
        st.number_input("Modify Fee Schedule Base Rate ($)", step=10.0, key="edit_price_val")
        st.button("💾 Apply Updated Price", on_click=cb_update_treatment_price, use_container_width=True, type="primary")
        
    with p_ed_col2:
        st.write("#### 📋 Current Treatment Pricing Catalog Database View")
        flat_records = []
        for category, item_map in catalog_db.items():
            for item, rate in item_map.items():
                flat_records.append({"Category": category, "Procedure Name": item, "Configured Fee Rate": f"${rate:,.2f}"})
        st.dataframe(pd.DataFrame(flat_records), use_container_width=True, hide_index=True)
