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
# DATABASE SEEDING & INITIALIZATION
# ==============================================================================
CENTERS = ["Istanbul Tower", "Elsifa Medical Center"]
PAYMENT_METHODS = ["Cash", "Bank Transfer"]

catalog_db = get_state_val("treatment_catalog_db", {
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

patients_db = get_state_val("patients_registry", {
    "P0001": {"name": "Yusuf Demir", "phone": "+90 532 123 4567", "center": "Istanbul Tower", "age": 28, "birth_date": "1998-05-12"},
    "P0002": {"name": "Amina El-Amin", "phone": "+90 555 987 6543", "center": "Elsifa Medical Center", "age": 9, "birth_date": "2017-08-20"}
})

history_db = get_state_val("tooth_history_ledger", {
    "P0001": {
        "16": [{"date": "2026-02-15", "treatment": "Composite Filling", "center": "Istanbul Tower", "notes": "Mesial decay managed.", "status": "Finished", "priority": "Normal"}]
    }
})

finance_db = get_state_val("finance_ledger", {
    "P0001": [{"date": "2026-02-15", "procedure": "Composite Filling (Teeth: 16)", "total_due": 300.0, "amount_paid": 300.0, "method": "Cash", "balance": 0.0}],
    "P0002": []
})

schedule_db = get_state_val("clinic_schedule_ledger", [])

# Persistent Form State Hooks
get_state_val("session_patient_id", "P0001")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "Composite Filling")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")
get_state_val("session_amount_paid", 0.0)
get_state_val("session_payment_method", "Cash")
get_state_val("session_case_type", "New Case")
get_state_val("session_work_status", "Open")
get_state_val("session_high_priority", False)

get_state_val("new_pat_name", "")
get_state_val("new_pat_phone", "")
get_state_val("new_pat_birth", date(2000, 1, 1))
get_state_val("new_pat_center", CENTERS[0])

# ==============================================================================
# STATE CALLBACK OPERATIONS
# ==============================================================================
def cb_toggle_grid_tooth(tooth_id):
    current = list(st.session_state.get("session_selected_teeth", []))
    if tooth_id in current:
        current.remove(tooth_id)
    else:
        current.append(tooth_id)
    st.session_state["session_selected_teeth"] = current
    sync_input_to_db("session_selected_teeth")

def cb_save_session_log():
    pid = st.session_state["session_patient_id"]
    cat = st.session_state["session_category"]
    treat = st.session_state["session_treatment"]
    teeth = st.session_state["session_selected_teeth"]
    paid = float(st.session_state["session_amount_paid"])
    method = st.session_state["session_payment_method"]
    case_type = st.session_state["session_case_type"]
    work_status = st.session_state["session_work_status"]
    high_priority = "High Priority (Next Week)" if st.session_state["session_high_priority"] else "Normal"
    
    if not teeth: 
        st.error("Please pick active target teeth from the mobile layout matrix.")
        return
        
    center = st.session_state["patients_registry"][pid]["center"]
    unit_rate = st.session_state["treatment_catalog_db"][cat].get(treat, 0.0)
    total_cost = unit_rate * len(teeth)
    remaining_balance = total_cost - paid
    
    history = st.session_state.get("tooth_history_ledger", {})
    if pid not in history: history[pid] = {}
    for t in teeth:
        if t not in history[pid]: history[pid][t] = []
        history[pid][t].append({
            "date": date.today().isoformat(), "treatment": f"[{case_type}][{cat}] {treat}", 
            "center": center, "notes": st.session_state["notes"], "status": work_status, "priority": high_priority
        })
    st.session_state["tooth_history_ledger"] = history
    sync_input_to_db("tooth_history_ledger")
    
    finances = st.session_state.get("finance_ledger", {})
    if pid not in finances: finances[pid] = []
    finances[pid].append({
        "date": date.today().isoformat(),
        "procedure": f"[{case_type}] {treat} (Teeth: {', '.join(sorted(teeth))})",
        "total_due": total_cost, "amount_paid": paid, "method": method if paid > 0 else "N/A", "balance": remaining_balance
    })
    st.session_state["finance_ledger"] = finances
    sync_input_to_db("finance_ledger")
    
    st.session_state["session_selected_teeth"] = []
    st.session_state["session_notes"] = ""
    st.session_state["session_amount_paid"] = 0.0
    st.success("Session saved successfully!")

# ==============================================================================
# MOBILE TOOTH MAP DEFINITIONS (FDI World Dental Federation Notation)
# ==============================================================================
quad_u1 = ["18", "17", "16", "15", "14", "13", "12", "11"]  # Upper Right
quad_u2 = ["21", "22", "23", "24", "25", "26", "27", "28"]  # Upper Left
quad_l2 = ["31", "32", "33", "34", "35", "36", "37", "38"]  # Lower Left
quad_l1 = ["48", "47", "46", "45", "44", "43", "42", "41"]  # Lower Right
all_teeth_options = quad_u1 + quad_u2 + quad_l2 + quad_l1

patient_selectors = {k: f"{v['name']} [{k}]" for k, v in st.session_state["patients_registry"].items()}

# ==============================================================================
# UI RENDERING
# ==============================================================================
st.set_page_config(page_title="Havence Mobile Desk", layout="wide")

# Enhanced high-contrast mobile layout styles
st.markdown("""
<style>
    .stButton > button {
        width: 100% !important;
        padding: 12px 0px !important;
        font-size: 16px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        margin-bottom: 4px;
    }
    .mobile-header {
        text-align: center;
        font-weight: bold;
        background-color: #2563eb;
        color: white;
        padding: 8px;
        border-radius: 6px;
        margin: 15px 0 8px 0;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("メニュー Menu")
page = st.sidebar.radio("Go to:", [
    "🩺 Active Session Desk", 
    "📅 Shift Scheduler & Booking Desk",
    "🔍 Patient History Lookup",
    "👥 Patient Registration Manager"
])

# ------------------------------------------------------------------------------
# PAGE 1: ACTIVE SESSION DESK (MOBILE-OPTIMIZED INTERFACE)
# ------------------------------------------------------------------------------
if page == "🩺 Active Session Desk":
    st.subheader("🩺 Touch-Friendly Clinical Input")
    
    active_teeth = st.session_state.get("session_selected_teeth", [])
    active_cat = st.session_state.get("session_category", "Adult Dentistry")
    available_procedures = list(st.session_state["treatment_catalog_db"].get(active_cat, {}).keys())
    unit_price = st.session_state["treatment_catalog_db"][active_cat].get(st.session_state["session_treatment"], 0.0)
    gross_cost = unit_price * len(active_teeth)

    # Top Block: Diagnostics & Selection
    st.selectbox("Select Patient", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="session_patient_id")
    
    c1, c2 = st.columns(2)
    c1.selectbox("Intake", options=["New Case", "Open Case"], key="session_case_type")
    c2.selectbox("Status", options=["Open", "Finished"], key="session_work_status")
    
    st.selectbox("Category", options=list(st.session_state["treatment_catalog_db"].keys()), key="session_category")
    st.selectbox("Procedure", options=available_procedures, key="session_treatment")
    
    st.markdown("---")
    st.subheader("📱 Mobile-Friendly Tooth Selector")
    st.caption("Tap to select/deselect. Sorted cleanly into vertical scrolling blocks for small screens.")
    
    # 2x2 Grid Layout for Mobile Viewport Compatibility
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    
    with row1_col1:
        st.markdown("<div class='mobile-header'>🦷 Upper Right (18-11)</div>", unsafe_allow_html=True)
        for t in quad_u1:
            is_sel = t in active_teeth
            lbl = f"⭐ Tooth {t} (Selected)" if is_sel else f"🦷 Tooth {t}"
            type_btn = "primary" if is_sel else "secondary"
            st.button(lbl, key=f"mob_u1_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type=type_btn)
            
    with row1_col2:
        st.markdown("<div class='mobile-header'>🦷 Upper Left (21-28)</div>", unsafe_allow_html=True)
        for t in quad_u2:
            is_sel = t in active_teeth
            lbl = f"⭐ Tooth {t} (Selected)" if is_sel else f"🦷 Tooth {t}"
            type_btn = "primary" if is_sel else "secondary"
            st.button(lbl, key=f"mob_u2_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type=type_btn)

    with row2_col1:
        st.markdown("<div class='mobile-header'>🦷 Lower Right (48-41)</div>", unsafe_allow_html=True)
        for t in quad_l1:
            is_sel = t in active_teeth
            lbl = f"⭐ Tooth {t} (Selected)" if is_sel else f"🦷 Tooth {t}"
            type_btn = "primary" if is_sel else "secondary"
            st.button(lbl, key=f"mob_l1_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type=type_btn)

    with row2_col2:
        st.markdown("<div class='mobile-header'>🦷 Lower Left (31-38)</div>", unsafe_allow_html=True)
        for t in quad_l2:
            is_sel = t in active_teeth
            lbl = f"⭐ Tooth {t} (Selected)" if is_sel else f"🦷 Tooth {t}"
            type_btn = "primary" if is_sel else "secondary"
            st.button(lbl, key=f"mob_l2_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type=type_btn)

    st.markdown("---")
    
    # Bottom Block: Notes & Invoicing
    if active_teeth:
        st.warning(f"Selected Teeth: {', '.join(sorted(active_teeth))}")
        
    st.text_area("Clinical Notes", key="notes")
    st.checkbox("⚠️ Mark as HIGH PRIORITY for Next Week", key="session_high_priority")
    
    st.metric("Total Due", f"${gross_cost:,.2f}")
    st.number_input("Amount Paid Right Now ($)", min_value=0.0, step=10.0, key="session_amount_paid")
    st.selectbox("Payment Method", options=PAYMENT_METHODS, key="session_payment_method")
    
    st.button("💾 Save & Commit Session Log", on_click=cb_save_session_log, type="primary")

# ------------------------------------------------------------------------------
# RETAINED REMAINING COMPATIBLE BACKEND ROUTINES
# ------------------------------------------------------------------------------
elif page == "📅 Shift Scheduler & Booking Desk":
    st.subheader("📅 Monday & Thursday Scheduler")
    start_hour = st.number_input("Start Hour (24h)", min_value=0, max_value=23, value=9)
    end_hour = st.number_input("End Hour (24h)", min_value=start_hour+1, max_value=24, value=17)
    target_date = st.date_input("Choose Date", value=date.today())
    
    if target_date.weekday() not in [0, 3]:
        st.error("Select a Monday or Thursday")
    else:
        st.success(f"Valid Workday: {target_date.strftime('%A')}")
        time_slots = [f"{h:02d}:00 - {h+1:02d}:00" for h in range(start_hour, end_hour)]
        selected_slot = st.selectbox("Time Slot", options=time_slots)
        sch_pid = st.selectbox("Patient", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x])
        sch_case_type = st.radio("Classification", options=["New Case", "Open Case"], horizontal=True)
        sch_priority = st.checkbox("High Priority")
        
        if st.button("📝 Book Slot", type="primary"):
            sched_list = st.session_state.get("clinic_schedule_ledger", [])
            sched_list.append({
                "Date": target_date.isoformat(), "Day": target_date.strftime('%A'), "Time Slot": selected_slot,
                "Patient Name": st.session_state["patients_registry"][sch_pid]["name"], "Classification": sch_case_type,
                "Priority Status": "High Priority (Next Week)" if sch_priority else "Normal"
            })
            st.session_state["clinic_schedule_ledger"] = sched_list
            sync_input_to_db("clinic_schedule_ledger")
            st.success("Booked!")
            
    appointments = st.session_state.get("clinic_schedule_ledger", [])
    if appointments:
        st.dataframe(pd.DataFrame(appointments), use_container_width=True, hide_index=True)

elif page == "🔍 Patient History Lookup":
    st.subheader("🔍 Centralized Patient History")
    lookup_pid = st.selectbox("Select Patient", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x])
    p_profile = st.session_state["patients_registry"][lookup_pid]
    
    st.markdown(f"**Name:** {p_profile['name']} | **Phone:** {p_profile['phone']} | **Center:** {p_profile['center']}")
    p_tx_history = st.session_state["finance_ledger"].get(lookup_pid, [])
    if p_tx_history:
        st.dataframe(pd.DataFrame(p_tx_history), use_container_width=True, hide_index=True)

elif page == "👥 Patient Registration Manager":
    st.subheader("👥 Register Patient")
    st.text_input("Name", key="new_pat_name")
    st.text_input("Phone", key="new_pat_phone")
    st.date_input("Birth Date", key="new_pat_birth")
    st.selectbox("Facility Center", options=CENTERS, key="new_pat_center")
    st.button("🚀 Register", on_click=cb_add_new_patient)
