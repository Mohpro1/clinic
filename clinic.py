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
# 2. DATABASE SEEDING & INITIALIZATION
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

# Global Active Clinical Tracking Cases Engine
cases_db = get_state_val("patient_cases_tracker", {
    "P0001": [
        {"case_id": "C001", "tooth": "16", "treatment": "Composite Filling", "type": "New Session (New Query)", "status": "Finished", "est_sessions": 1}
    ],
    "P0002": []
})

history_db = get_state_val("tooth_history_ledger", {
    "P0001": {
        "16": [{"date": "2026-02-15", "treatment": "[New Session] Composite Filling", "center": "Istanbul Tower", "notes": "Initial setup completed.", "status": "Finished"}]
    }
})

finance_db = get_state_val("finance_ledger", {
    "P0001": [{"date": "2026-02-15", "procedure": "Composite Filling (Tooth: 16)", "total_due": 300.0, "amount_paid": 300.0, "method": "Cash", "balance": 0.0}],
    "P0002": []
})

schedule_db = get_state_val("clinic_schedule_ledger", [])

# Persistent App State Keys
get_state_val("session_patient_id", "P0001")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "Composite Filling")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")
get_state_val("session_amount_paid", 0.0)
get_state_val("session_payment_method", "Cash")
get_state_val("session_type_nature", "New Session (New Query)")
get_state_val("session_work_status", "Open")
get_state_val("session_est_count", 2)
get_state_val("session_high_priority", False)

get_state_val("new_pat_name", "")
get_state_val("new_pat_phone", "")
get_state_val("new_pat_birth", date(2000, 1, 1))
get_state_val("new_pat_center", CENTERS[0])

# ==============================================================================
# 3. GLOBAL STATE CALLBACK OPERATORS
# ==============================================================================
def cb_add_new_patient():
    name = st.session_state.get("new_pat_name", "").strip()
    phone = st.session_state.get("new_pat_phone", "").strip()
    bdate = st.session_state.get("new_pat_birth")
    center = st.session_state.get("new_pat_center")
    
    if not name or not phone: 
        st.error("Fields cannot be empty!")
        return
        
    registry = st.session_state.get("patients_registry", {})
    if registry:
        existing_ids = [int(k.replace("P", "")) for k in registry.keys() if k.replace("P", "").isdigit()]
        next_id = max(existing_ids) + 1 if existing_ids else 1
    else:
        next_id = 1
    new_code = f"P{next_id:04d}"
    
    registry[new_code] = {
        "name": name, "phone": phone, "center": center, 
        "age": date.today().year - bdate.year, "birth_date": bdate.isoformat()
    }
    st.session_state["patients_registry"] = registry
    sync_input_to_db("patients_registry")
    
    cases = st.session_state.get("patient_cases_tracker", {})
    cases[new_code] = []
    st.session_state["patient_cases_tracker"] = cases
    sync_input_to_db("patient_cases_tracker")
    
    finances = st.session_state.get("finance_ledger", {})
    finances[new_code] = []
    st.session_state["finance_ledger"] = finances
    sync_input_to_db("finance_ledger")
    
    st.session_state["new_pat_name"] = ""
    st.session_state["new_pat_phone"] = ""
    st.success(f"Registered {name} successfully as {new_code}!")

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
    nature = st.session_state["session_type_nature"]
    work_status = st.session_state["session_work_status"]
    est_sessions = int(st.session_state["session_est_count"])
    high_prio = "High Priority" if st.session_state["session_high_priority"] else "Normal"
    
    if not teeth: 
        st.error("Please pick active target teeth from the layout matrix.")
        return
        
    center = st.session_state["patients_registry"][pid]["center"]
    unit_rate = st.session_state["treatment_catalog_db"][cat].get(treat, 0.0)
    total_cost = unit_rate * len(teeth)
    remaining_balance = total_cost - paid
    
    # 1. Update Cases Tracker
    cases_list = st.session_state.get("patient_cases_tracker", {}).get(pid, [])
    for t in teeth:
        case_found = False
        if nature == "Repeated Session (Follow-up)":
            for c in cases_list:
                if c["tooth"] == t and c["status"] == "Open":
                    c["status"] = work_status
                    c["est_sessions"] = est_sessions
                    case_found = True
                    break
        if not case_found:
            cid = f"C{len(cases_list)+1:03d}"
            cases_list.append({
                "case_id": cid, "tooth": t, "treatment": treat,
                "type": nature, "status": work_status, "est_sessions": est_sessions
            })
    st.session_state["patient_cases_tracker"][pid] = cases_list
    sync_input_to_db("patient_cases_tracker")

    # 2. Update Tooth Clinical History logs
    history = st.session_state.get("tooth_history_ledger", {})
    if pid not in history: history[pid] = {}
    for t in teeth:
        if t not in history[pid]: history[pid][t] = []
        history[pid][t].append({
            "date": date.today().isoformat(), "treatment": f"[{nature}] {treat}", 
            "center": center, "notes": st.session_state["session_notes"], "status": work_status
        })
    st.session_state["tooth_history_ledger"] = history
    sync_input_to_db("tooth_history_ledger")
    
    # 3. Update Financial Ledger
    finances = st.session_state.get("finance_ledger", {})
    if pid not in finances: finances[pid] = []
    finances[pid].append({
        "date": date.today().isoformat(),
        "procedure": f"[{nature}] {treat} (Teeth: {', '.join(sorted(teeth))}) - {work_status}",
        "total_due": total_cost, "amount_paid": paid, "method": method if paid > 0 else "N/A", "balance": remaining_balance
    })
    st.session_state["finance_ledger"] = finances
    sync_input_to_db("finance_ledger")
    
    st.session_state["session_selected_teeth"] = []
    st.session_state["session_notes"] = ""
    st.session_state["session_amount_paid"] = 0.0
    st.session_state["session_high_priority"] = False
    st.success("Session entry logged successfully!")

# ==============================================================================
# 4. MOBILE TOOTH MAP GRID CONFIGURATION
# ==============================================================================
quad_u1 = ["18", "17", "16", "15", "14", "13", "12", "11"]  
quad_u2 = ["21", "22", "23", "24", "25", "26", "27", "28"]  
quad_l2 = ["31", "32", "33", "34", "35", "36", "37", "38"]  
quad_l1 = ["48", "47", "46", "45", "44", "43", "42", "41"]  
all_teeth_options = quad_u1 + quad_u2 + quad_l2 + quad_l1

patient_selectors = {k: f"{v['name']} [{k}]" for k, v in st.session_state["patients_registry"].items()}

# ==============================================================================
# 5. UI LAYOUT & SIDEBAR NAVIGATION ROUTING
# ==============================================================================
st.set_page_config(page_title="Havence Clinical Engine", layout="wide")

st.markdown("""
<style>
    .stButton > button { width: 100% !important; padding: 12px 0px !important; font-size: 15px !important; font-weight: bold !important; border-radius: 8px !important; margin-bottom: 4px; }
    .mobile-header { text-align: center; font-weight: bold; background-color: #1e293b; color: white; padding: 6px; border-radius: 6px; margin: 12px 0 6px 0; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🦷 Havence Menu")
page = st.sidebar.radio("Navigate Workspace:", [
    "🩺 Active Session Desk", 
    "📅 Shift Scheduler & Booking Desk",
    "🔍 Patient History Lookup",
    "👥 Patient Registration Manager"
])

st.title("Havence Dental Clinic System")
st.markdown("---")

# ------------------------------------------------------------------------------
# PAGE 1: ACTIVE SESSION DESK (WITH SESSIONS RUN COUNTER)
# ------------------------------------------------------------------------------
if page == "🩺 Active Session Desk":
    st.subheader("🩺 Clinical Session Intake Panel")
    
    active_teeth = st.session_state.get("session_selected_teeth", [])
    active_cat = st.session_state.get("session_category", "Adult Dentistry")
    available_procedures = list(st.session_state["treatment_catalog_db"].get(active_cat, {}).keys())
    
    if st.session_state["session_treatment"] not in available_procedures and available_procedures:
        st.session_state["session_treatment"] = available_procedures[0]
        
    unit_price = st.session_state["treatment_catalog_db"][active_cat].get(st.session_state["session_treatment"], 0.0)
    gross_cost = unit_price * len(active_teeth)

    st.selectbox("Select Target Patient Profile", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="session_patient_id")
    
    # Session Type Selection Rules
    nat_col, stat_col, est_col = st.columns(3)
    nat_col.selectbox("Session Type Classification", options=["New Session (New Query)", "Repeated Session (Follow-up)"], key="session_type_nature")
    stat_col.selectbox("Current Work Status", options=["Open", "Finished"], key="session_work_status")
    
    # How many total sessions will this take?
    if st.session_state["session_work_status"] == "Finished":
        est_col.markdown("<p style='padding: 30px 0 0 0; font-weight: bold; color: green;'>✓ Finished Case</p>", unsafe_allow_html=True)
        st.session_state["session_est_count"] = 1
    else:
        est_col.number_input("Estimated Total Sessions Needed", min_value=1, max_value=20, key="session_est_count")
    
    st.selectbox("Age Domain Group", options=list(st.session_state["treatment_catalog_db"].keys()), key="session_category")
    st.selectbox("Procedure Plan Line", options=available_procedures, key="session_treatment")
    
    st.markdown("---")
    st.subheader("📱 Mobile Touch Tooth Selection Matrix")
    
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    
    with row1_col1:
        st.markdown("<div class='mobile-header'>Upper Right (18-11)</div>", unsafe_allow_html=True)
        for t in quad_u1:
            is_sel = t in active_teeth
            st.button(f"{'⭐' if is_sel else '🦷'} Tooth {t}", key=f"mob_u1_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type="primary" if is_sel else "secondary")
            
    with row1_col2:
        st.markdown("<div class='mobile-header'>Upper Left (21-28)</div>", unsafe_allow_html=True)
        for t in quad_u2:
            is_sel = t in active_teeth
            st.button(f"{'⭐' if is_sel else '🦷'} Tooth {t}", key=f"mob_u2_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type="primary" if is_sel else "secondary")

    with row2_col1:
        st.markdown("<div class='mobile-header'>Lower Right (48-41)</div>", unsafe_allow_html=True)
        for t in quad_l1:
            is_sel = t in active_teeth
            st.button(f"{'⭐' if is_sel else '🦷'} Tooth {t}", key=f"mob_l1_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type="primary" if is_sel else "secondary")

    with row2_col2:
        st.markdown("<div class='mobile-header'>Lower Left (31-38)</div>", unsafe_allow_html=True)
        for t in quad_l2:
            is_sel = t in active_teeth
            st.button(f"{'⭐' if is_sel else '🦷'} Tooth {t}", key=f"mob_l2_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type="primary" if is_sel else "secondary")

    st.markdown("---")
    st.text_area("Clinical Case Notes", key="session_notes")
    st.checkbox("⚠️ Flag as HIGH PRIORITY for Next Week", key="session_high_priority")
    
    st.metric("Total Cost Due", f"${gross_cost:,.2f}")
    st.number_input("Amount Collected Right Now ($)", min_value=0.0, step=10.0, key="session_amount_paid")
    st.selectbox("Payment Method Type", options=PAYMENT_METHODS, key="session_payment_method")
    
    st.button("💾 Save Session Record", on_click=cb_save_session_log, type="primary")

# ------------------------------------------------------------------------------
# PAGE 2: SHIFT SCHEDULER & BOOKING DESK (WITH OPEN CASE DROPDOWN SELECTION)
# ------------------------------------------------------------------------------
elif page == "📅 Shift Scheduler & Booking Desk":
    st.subheader("📅 Monday & Thursday Shift Scheduler Desk")
    
    col_sch1, col_sch2 = st.columns([1, 1])
    with col_sch1:
        st.markdown("#### 🕒 Setup Booking Slots")
        start_hour = st.number_input("Start Hour (24h)", min_value=0, max_value=23, value=9)
        end_hour = st.number_input("End Hour (24h)", min_value=start_hour+1, max_value=24, value=17)
        target_date = st.date_input("Choose Target Appointment Date", value=date.today())
        
        if target_date.weekday() not in [0, 3]:
            st.error("❌ Out of Office Bounds! Please select a Monday or Thursday.")
            is_valid_day = False
        else:
            st.success(f"✅ Approved Workday Shift: {target_date.strftime('%A')}")
            is_valid_day = True
            
        time_slots = [f"{h:02d}:00 - {h+1:02d}:00" for h in range(start_hour, end_hour)]
        selected_slot = st.selectbox("Available 1-Hour Time Slots", options=time_slots)
        
        sch_pid = st.selectbox("Assign Patient Profile", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="scheduler_pid")
        sch_case_class = st.radio("Intake Case Stream Type", options=["New Case", "Open Case"], horizontal=True)
        
        # Pull Open Treatment Cases for Selected Patient
        selected_open_case_detail = "N/A (New Case Intake)"
        if sch_case_class == "Open Case":
            all_cases = st.session_state.get("patient_cases_tracker", {}).get(sch_pid, [])
            open_cases = [c for c in all_cases if c["status"] == "Open"]
            
            if open_cases:
                case_options = {f"{c['case_id']}": f"Tooth {c['tooth']} - {c['treatment']} ({c['est_sessions']} sessions left)" for c in open_cases}
                chosen_cid = st.selectbox("Select Which Open Session to Continue:", options=list(case_options.keys()), format_func=lambda x: case_options[x])
                selected_open_case_detail = case_options[chosen_cid]
            else:
                st.warning("⚠️ No active Open Cases found for this patient! Resetting to New Case.")
                sch_case_class = "New Case"
                
        sch_priority = st.checkbox("High Priority Allocation")
        
        if st.button("📝 Register Appointment Slot", disabled=not is_valid_day, type="primary"):
            sched_list = st.session_state.get("clinic_schedule_ledger", [])
            sched_list.append({
                "Date": target_date.isoformat(), "Day": target_date.strftime('%A'), "Time Slot": selected_slot,
                "Patient Name": st.session_state["patients_registry"][sch_pid]["name"], 
                "Case Type": sch_case_class, "Treatment Linked": selected_open_case_detail,
                "Priority": "High Priority" if sch_priority else "Normal"
            })
            st.session_state["clinic_schedule_ledger"] = sched_list
            sync_input_to_db("clinic_schedule_ledger")
            st.success("Appointment slot pinned successfully!")

    with col_sch2:
        st.markdown("#### 📋 Booked Appointments Timetable")
        appointments = st.session_state.get("clinic_schedule_ledger", [])
        if appointments:
            st.dataframe(pd.DataFrame(appointments), use_container_width=True, hide_index=True)
        else:
            st.info("No bookings recorded for this schedule layout block.")

# ------------------------------------------------------------------------------
# PAGE 3: PATIENT HISTORY LOOKUP (WITH COMPLETE CASES TRACKER ENGINE)
# ------------------------------------------------------------------------------
elif page == "🔍 Patient History Lookup":
    st.subheader("🔍 Patient Comprehensive Medical History File")
    lookup_pid = st.selectbox("Select Patient Profile", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x])
    p_profile = st.session_state["patients_registry"][lookup_pid]
    
    st.markdown(f"**Name:** {p_profile['name']} | **Contact:** {p_profile['phone']} | **Clinic Site:** {p_profile['center']}")
    
    h_tab1, h_tab2, h_tab3 = st.tabs(["📊 Case Lifecycle Tracker", "💰 Account Balance Statement", "🦷 Isolated Tooth Logs"])
    
    with h_tab1:
        st.markdown("### Active & Historic Case Tracking")
        pt_cases = st.session_state.get("patient_cases_tracker", {}).get(lookup_pid, [])
        if pt_cases:
            st.dataframe(pd.DataFrame(pt_cases), use_container_width=True, hide_index=True)
        else:
            st.info("No recorded open or finished sequential cases tracked for this patient profile.")
            
    with h_tab2:
        p_tx_history = st.session_state["finance_ledger"].get(lookup_pid, [])
        if p_tx_history:
            df_fin = pd.DataFrame(p_tx_history)
            st.metric("Total Account Balance Outstanding", f"${df_fin['balance'].sum():,.2f}")
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
        else:
            st.info("No financial transactions on file.")
            
    with h_tab3:
        selected_tooth = st.selectbox("Isolate Target Tooth", options=all_teeth_options)
        records = st.session_state["tooth_history_ledger"].get(lookup_pid, {}).get(selected_tooth, [])
        if records:
            st.table(pd.DataFrame(records))
        else:
            st.warning(f"No clinical records written for Tooth {selected_tooth}.")

# ------------------------------------------------------------------------------
# PAGE 4: PATIENT REGISTRATION MANAGER
# ------------------------------------------------------------------------------
elif page == "👥 Patient Registration Manager":
    st.subheader("👥 Patient Profile Creation Engine")
    
    c_adm1, c_adm2 = st.columns([1, 2])
    with c_adm1:
        st.text_input("Full Patient Name", key="new_pat_name")
        st.text_input("Mobile Contact Phone", key="new_pat_phone")
        st.date_input("Date of Birth", key="new_pat_birth")
        st.selectbox("Assigned Medical Facility", options=CENTERS, key="new_pat_center")
        st.button("🚀 Register Patient Profile", on_click=cb_add_new_patient, type="primary")
        
    with c_adm2:
        raw_patients = []
        for pid, d in st.session_state["patients_registry"].items():
            raw_patients.append({"ID Code": pid, "Full Name": d["name"], "Contact Phone": d["phone"], "Clinic Center": d["center"]})
        st.dataframe(pd.DataFrame(raw_patients), use_container_width=True, hide_index=True)
