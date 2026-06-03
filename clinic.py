import json
import os
from datetime import datetime, date, timedelta
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
PAYMENT_METHODS = ["Cash", "Bank Transfer", "Credit Card"]

catalog_db = get_state_val("treatment_catalog_db", {
    "Children Dentistry": {
        "Fluoride Application": 1250.0,
        "Fissure Sealant": 1500.0,
        "Pediatric Extraction": 2000.0,
        "Pulpotomy": 3500.0
    },
    "Adult Dentistry": {
        "Composite Filling": 2500.0,
        "Root Canal Treatment (RCT)": 6500.0,
        "Porcelain Crown": 9500.0,
        "Deep Scaling & Polishing": 2800.0,
        "Surgical Tooth Extraction": 5000.0
    }
})

patients_db = get_state_val("patients_registry", {
    "P0001": {"name": "Yusuf Demir", "phone": "+90 532 123 4567", "center": "Istanbul Tower", "age": 28},
    "P0002": {"name": "Amina El-Amin", "phone": "+90 555 987 6543", "center": "Elsifa Medical Center", "age": 9}
})

cases_db = get_state_val("patient_cases_tracker", {
    "P0001": [{"case_id": "C001", "tooth": "UR6", "treatment": "Composite Filling", "type": "New Session (New Query)", "status": "Open", "est_sessions": 2}],
    "P0002": [{"case_id": "C002", "tooth": "LLA", "treatment": "Fluoride Application", "type": "New Session (New Query)", "status": "Open", "est_sessions": 1}]
})

history_db = get_state_val("tooth_history_ledger", {
    "P0001": {"UR6": [{"date": "2026-02-15", "treatment": "[New Session] Composite Filling", "center": "Istanbul Tower", "notes": "Initial setup completed.", "status": "Open"}]}
})

finance_db = get_state_val("finance_ledger", {
    "P0001": [{"date": "2026-02-15", "procedure": "Composite Filling (Tooth: UR6)", "gross_calculated": 2500.0, "discount_applied": 0.0, "total_due": 2500.0, "amount_paid": 2000.0, "method": "Cash", "balance": 500.0}],
    "P0002": [{"date": "2026-02-16", "procedure": "Fluoride Treatment (Tooth: LLA)", "gross_calculated": 1250.0, "discount_applied": 50.0, "total_due": 1200.0, "amount_paid": 400.0, "method": "Credit Card", "balance": 800.0}]
})

schedule_db = get_state_val("clinic_schedule_ledger", [])

# Persistent Application Inputs State Hooks
get_state_val("session_patient_id", "P0001")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "Composite Filling")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")
get_state_val("session_log_date", date.today())
get_state_val("session_amount_paid", 0.0)
get_state_val("session_discount_input", 0.0)
get_state_val("session_payment_method", "Cash")
get_state_val("session_type_nature", "New Session (New Query)")
get_state_val("session_work_status", "Open")
get_state_val("session_est_count", 2)
get_state_val("session_high_priority", False)

get_state_val("new_pat_name", "")
get_state_val("new_pat_phone", "")
get_state_val("new_pat_age", 30)
get_state_val("new_pat_center", CENTERS[0])

# Catalog management fields
get_state_val("adm_add_cat", "Adult Dentistry")
get_state_val("adm_add_name", "")
get_state_val("adm_add_price", 1000.0)
get_state_val("adm_edit_cat", "Adult Dentistry")
get_state_val("adm_edit_treat", "Composite Filling")
get_state_val("adm_edit_price", 2500.0)

# ==============================================================================
# 3. GLOBAL STATE CALLBACK OPERATORS
# ==============================================================================
def cb_add_new_patient():
    name = st.session_state.get("new_pat_name", "").strip()
    phone = st.session_state.get("new_pat_phone", "").strip()
    age = int(st.session_state.get("new_pat_age", 30))
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
        "name": name, "phone": phone, "center": center, "age": age
    }
    st.session_state["patients_registry"] = registry
    sync_input_to_db("patients_registry")
    
    st.session_state["patient_cases_tracker"][new_code] = []
    sync_input_to_db("patient_cases_tracker")
    st.session_state["finance_ledger"][new_code] = []
    sync_input_to_db("finance_ledger")
    
    st.session_state["new_pat_name"] = ""
    st.session_state["new_pat_phone"] = ""
    st.session_state["new_pat_age"] = 30
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
    s_date = st.session_state["session_log_date"]
    paid = float(st.session_state["session_amount_paid"])
    discount = float(st.session_state["session_discount_input"])
    method = st.session_state["session_payment_method"]
    nature = st.session_state["session_type_nature"]
    work_status = st.session_state["session_work_status"]
    est_sessions = int(st.session_state["session_est_count"])
    
    if not teeth: 
        st.error("Please pick active target teeth from the matrix layout.")
        return
        
    center = st.session_state["patients_registry"][pid]["center"]
    unit_rate = st.session_state["treatment_catalog_db"][cat].get(treat, 0.0)
    gross_cost = unit_rate * len(teeth)
    
    net_cost = max(0.0, gross_cost - discount)
    remaining_balance = net_cost - paid
    
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

    history = st.session_state.get("tooth_history_ledger", {})
    if pid not in history: history[pid] = {}
    for t in teeth:
        if t not in history[pid]: history[pid][t] = []
        history[pid][t].append({
            "date": s_date.isoformat(), "treatment": f"[{nature}] {treat}", 
            "center": center, "notes": st.session_state["session_notes"], "status": work_status
        })
    st.session_state["tooth_history_ledger"] = history
    sync_input_to_db("tooth_history_ledger")
    
    finances = st.session_state.get("finance_ledger", {})
    if pid not in finances: finances[pid] = []
    finances[pid].append({
        "date": s_date.isoformat(),
        "procedure": f"[{nature}] {treat} (Teeth: {', '.join(sorted(teeth))}) - Status: {work_status}",
        "gross_calculated": gross_cost,
        "discount_applied": discount,
        "total_due": net_cost, 
        "amount_paid": paid, 
        "method": method if paid > 0 else "N/A", 
        "balance": remaining_balance
    })
    st.session_state["finance_ledger"] = finances
    sync_input_to_db("finance_ledger")
    
    st.session_state["session_selected_teeth"] = []
    st.session_state["session_notes"] = ""
    st.session_state["session_amount_paid"] = 0.0
    st.session_state["session_discount_input"] = 0.0
    st.session_state["session_log_date"] = date.today()
    st.success("Session saved successfully inside transaction ledger data.")

def cb_add_catalog_procedure():
    a_cat = st.session_state["adm_add_cat"]
    a_name = st.session_state["adm_add_name"].strip()
    a_prc = float(st.session_state["adm_add_price"])
    
    if a_name:
        st.session_state["treatment_catalog_db"][a_cat][a_name] = a_prc
        save_db(st.session_state["treatment_catalog_db"])
        st.session_state["adm_add_name"] = "" 
        st.toast(f"Appended '{a_name}' successfully!", icon="🚀")
    else:
        st.error("Procedure label value cannot be blank!")

# ==============================================================================
# 4. PALMER NOTATION SYSTEM CONFIGURATION
# ==============================================================================
adult_quad_ur = [f"UR{i}" for i in range(8, 0, -1)]  
adult_quad_ul = [f"UL{i}" for i in range(1, 9)]       
adult_quad_lr = [f"LR{i}" for i in range(8, 0, -1)]  
adult_quad_ll = [f"LL{i}" for i in range(1, 9)]       
all_adult_palmer = adult_quad_ur + adult_quad_ul + adult_quad_lr + adult_quad_ll

child_labels = ["E", "D", "C", "B", "A"]
child_quad_ur = [f"UR{ch}" for ch in child_labels]      
child_quad_ul = [f"UL{ch}" for ch in reversed(child_labels)] 
child_quad_lr = [f"LR{ch}" for ch in child_labels]      
child_quad_ll = [f"LL{ch}" for ch in reversed(child_labels)] 
all_child_palmer = child_quad_ur + child_quad_ul + child_quad_lr + child_quad_ll

patient_selectors = {k: f"{v['name']} [{k}]" for k, v in st.session_state["patients_registry"].items()}

HALF_HOUR_OPTIONS = []
for hour in range(0, 24):
    HALF_HOUR_OPTIONS.append(f"{hour:02d}:00")
    HALF_HOUR_OPTIONS.append(f"{hour:02d}:30")

# Helper to look up all open cases globally across all patient IDs
def get_global_open_cases():
    global_cases = []
    tracker = st.session_state.get("patient_cases_tracker", {})
    registry = st.session_state.get("patients_registry", {})
    
    for pid, cases in tracker.items():
        p_name = registry.get(pid, {}).get("name", "Unknown Patient")
        for c in cases:
            if c.get("status") == "Open":
                global_cases.append({
                    "unique_key": f"{pid}||{c['case_id']}",
                    "display_label": f"📄 {p_name} ({pid}) — Case {c['case_id']}: Tooth {c['tooth']} [{c['treatment']}]"
                })
    return global_cases

# ==============================================================================
# 5. UI LAYOUT ARCHITECTURE
# ==============================================================================
st.set_page_config(page_title="Havence System", layout="wide")

st.markdown("""
<style>
    .stButton > button { width: 100% !important; padding: 12px 0px !important; font-size: 15px !important; font-weight: bold !important; border-radius: 8px !important; }
    .mobile-header { text-align: center; font-weight: bold; background-color: #1e293b; color: white; padding: 6px; border-radius: 6px; margin: 12px 0 6px 0; }
    .date-header { font-size: 18px; font-weight: bold; color: #0284c7; margin-top: 15px; margin-bottom: 5px; border-bottom: 2px solid #e2e8f0; padding-bottom: 3px;}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🦷 Havence Clinical Menu")
page = st.sidebar.radio("Workspace Navigation Layout Options:", [
    "🩺 Active Session Desk", 
    "📅 Shift Scheduler & Booking Desk",
    "📋 Treatment Price Database Panel",
    "🔍 Patient History Lookup",
    "👥 Patient Registration Manager",
    "💰 Financial Analytics Matrix"
])

st.title("Havence Dental Management System")
st.markdown("---")

# ------------------------------------------------------------------------------
# PAGE 1: ACTIVE SESSION DESK
# ------------------------------------------------------------------------------
if page == "🩺 Active Session Desk":
    st.subheader("🩺 Clinical Treatment Intake & Discount Engine")
    
    active_teeth = st.session_state.get("session_selected_teeth", [])
    active_cat = st.session_state.get("session_category", "Adult Dentistry")
    available_procedures = list(st.session_state["treatment_catalog_db"].get(active_cat, {}).keys())
    
    if st.session_state["session_treatment"] not in available_procedures and available_procedures:
        st.session_state["session_treatment"] = available_procedures[0]
        
    unit_price = st.session_state["treatment_catalog_db"][active_cat].get(st.session_state["session_treatment"], 0.0)
    gross_cost = unit_price * len(active_teeth)

    st.selectbox("Select Patient Profile", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="session_patient_id")
    
    nat_col, stat_col, est_col = st.columns(3)
    nat_col.selectbox("Session Entry Classification Type", options=["New Session (New Query)", "Repeated Session (Follow-up)"], key="session_type_nature")
    stat_col.selectbox("Current Clinical Work Status", options=["Open", "Finished"], key="session_work_status")
    
    if st.session_state["session_work_status"] == "Finished":
        est_col.markdown("<p style='padding: 34px 0 0 0; font-weight: bold; color: green;'>✓ Job Declared Finished</p>", unsafe_allow_html=True)
        st.session_state["session_est_count"] = 1
    else:
        est_col.number_input("Estimated Total Running Sessions Needed", min_value=1, max_value=20, key="session_est_count")
    
    st.selectbox("Age Domain Target Categorization Group", options=list(st.session_state["treatment_catalog_db"].keys()), key="session_category")
    st.selectbox("Procedure Operational Selection Line Plan", options=available_procedures, key="session_treatment")
    
    st.markdown("---")
    st.subheader("📱 Mobile Touch Palmer Mapping Grid System")
    
    if active_cat == "Children Dentistry":
        q_ur, q_ul, q_lr, q_ll = child_quad_ur, child_quad_ul, child_quad_lr, child_quad_ll
        system_label = "Palmer Alphabetical (A-E)"
    else:
        q_ur, q_ul, q_lr, q_ll = adult_quad_ur, adult_quad_ul, adult_quad_lr, adult_quad_ll
        system_label = "Palmer Numeric (1-8)"
        
    st.caption(f"Active Dentition Architecture Style: **{system_label}**")
    
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    
    with row1_col1:
        st.markdown("<div class='mobile-header'>Upper Right Quadrant ┘</div>", unsafe_allow_html=True)
        for t in q_ur:
            is_sel = t in active_teeth
            st.button(f"{'⭐' if is_sel else '🦷'} {t}", key=f"mob_palmer_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type="primary" if is_sel else "secondary")
            
    with row1_col2:
        st.markdown("<div class='mobile-header'>└ Upper Left Quadrant</div>", unsafe_allow_html=True)
        for t in q_ul:
            is_sel = t in active_teeth
            st.button(f"{'⭐' if is_sel else '🦷'} {t}", key=f"mob_palmer_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type="primary" if is_sel else "secondary")

    with row2_col1:
        st.markdown("<div class='mobile-header'>Lower Right Quadrant ┐</div>", unsafe_allow_html=True)
        for t in q_lr:
            is_sel = t in active_teeth
            st.button(f"{'⭐' if is_sel else '🦷'} {t}", key=f"mob_palmer_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type="primary" if is_sel else "secondary")

    with row2_col2:
        st.markdown("<div class='mobile-header'>┌ Lower Left Quadrant</div>", unsafe_allow_html=True)
        for t in q_ll:
            is_sel = t in active_teeth
            st.button(f"{'⭐' if is_sel else '🦷'} {t}", key=f"mob_palmer_{t}", on_click=cb_toggle_grid_tooth, args=(t,), type="primary" if is_sel else "secondary")

    st.markdown("---")
    st.text_area("Case Notes Data Lines", key="session_notes")
    st.checkbox("⚠️ Assign as HIGH PRIORITY for Next Week Schedule Layout", key="session_high_priority")
    
    st.markdown("### 💸 Checkout Calculation Space (Turkish Lira ₺)")
    calc1, calc2, calc3 = st.columns(3)
    calc1.metric("Gross Starting Sum Cost", f"{gross_cost:,.2f} TL")
    
    with calc2:
        discount_val = st.number_input("Apply Session Discount Amount (TL ₺)", min_value=0.0, step=50.0, key="session_discount_input")
    
    final_net_payable = max(0.0, gross_cost - discount_val)
    calc3.metric("Net Invoiced Payable Amount", f"{final_net_payable:,.2f} TL", delta=f"-{discount_val:,.2f} TL" if discount_val > 0 else None, delta_color="inverse")
    
    pay_col1, pay_col2, pay_col3 = st.columns(3)
    pay_col1.date_input("Session Operational Date", key="session_log_date")
    pay_col2.number_input("Collected Amount Settled Right Now (TL ₺)", min_value=0.0, max_value=max(final_net_payable, 500000.0), step=100.0, key="session_amount_paid")
    pay_col3.selectbox("Payment Gateway Type", options=PAYMENT_METHODS, key="session_payment_method")
    
    st.button("💾 Commit & File Complete Session Transaction", on_click=cb_save_session_log, type="primary")

# ------------------------------------------------------------------------------
# PAGE 2: SHIFT SCHEDULER & BOOKING DESK
# ------------------------------------------------------------------------------
elif page == "📅 Shift Scheduler & Booking Desk":
    st.subheader("📅 Live Weekly Shift Planner Matrix")
    
    sch_tab1, sch_tab2 = st.tabs(["➕ Book New Appointment Slot", "✏️ Edit & Correct Slotted Bookings"])
    appointments = st.session_state.get("clinic_schedule_ledger", [])
    
    if appointments:
        appointments = sorted(appointments, key=lambda x: (x.get("Date", ""), x.get("Time Slot", "")))
        st.session_state["clinic_schedule_ledger"] = appointments

    with sch_tab1:
        col_sch1, col_sch2 = st.columns([1, 1])
        with col_sch1:
            st.markdown("#### 🕒 Booking Blocks & Working Shifts")
            
            start_str = st.selectbox("Shift Start Time", options=HALF_HOUR_OPTIONS, index=HALF_HOUR_OPTIONS.index("09:00"), key="sch_shift_start")
            end_str = st.selectbox("Shift End Time", options=HALF_HOUR_OPTIONS, index=HALF_HOUR_OPTIONS.index("17:00"), key="sch_shift_end")
            
            target_date = st.date_input("Select Plan Date Target", value=date.today(), key="sch_target_date")
            st.success(f"✅ Approved Working Shift Calendar Day: {target_date.strftime('%A')}")
            
            duration_mode = st.radio("Appointment Step Duration", options=["30 Minutes", "1 Hour"], horizontal=True, key="sch_duration_mode")
            
            t_start = datetime.strptime(start_str, "%H:%M")
            t_end = datetime.strptime(end_str, "%H:%M")
            time_slots = []
            current_slot_time = t_start
            step_delta = timedelta(minutes=30) if duration_mode == "30 Minutes" else timedelta(hours=1)
            
            if t_start >= t_end:
                st.error("Error: Shift End Time must be later than the Start Time!")
            else:
                while current_slot_time + step_delta <= t_end:
                    time_slots.append(f"{current_slot_time.strftime('%H:%M')} - {(current_slot_time + step_delta).strftime('%H:%M')}")
                    current_slot_time += step_delta

            selected_slot = st.selectbox("Available Matrix Scheduled Slots", options=time_slots if time_slots else ["N/A"], key="sch_selected_slot")
            
            sch_case_class = st.radio("Booking Strategy Type Selection", options=["New Case", "Open Case"], horizontal=True, key="sch_class_select")
            
            sch_pid = ""
            selected_open_case_detail = "N/A (New Case Intake)"
            
            if sch_case_class == "New Case":
                sch_pid = st.selectbox("Assign Patient ID", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="sch_pid_select_new")
            else:
                all_open_cases_list = get_global_open_cases()
                if all_open_cases_list:
                    case_map = {c["unique_key"]: c["display_label"] for c in all_open_cases_list}
                    chosen_unique_key = st.selectbox("Select Active Open Treatment Case from Master Directory:", options=list(case_map.keys()), format_func=lambda x: case_map[x], key="sch_global_open_case")
                    sch_pid = chosen_unique_key.split("||")[0]
                    selected_open_case_detail = case_map[chosen_unique_key]
                else:
                    st.warning("No active running Open Cases found anywhere inside the records. Reverting to New Case strategy layout.")
                    sch_case_class = "New Case"
                    sch_pid = st.selectbox("Assign Patient ID", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="sch_pid_select_fallback")

            sch_priority = st.checkbox("High Priority Allocation Status Flag", key="sch_priority_flag")
            
            if st.button("📝 Book Appointment Slot Entry Line", type="primary") and time_slots:
                appointments.append({
                    "Date": target_date.isoformat(), "Day": target_date.strftime('%A'), "Time Slot": selected_slot,
                    "Patient ID": sch_pid, "Patient Name": st.session_state["patients_registry"][sch_pid]["name"], 
                    "Case Stream Type": sch_case_class, "Linked Target Treatment": selected_open_case_detail,
                    "Priority Status": "High Priority" if sch_priority else "Normal"
                })
                appointments = sorted(appointments, key=lambda x: (x.get("Date", ""), x.get("Time Slot", "")))
                st.session_state["clinic_schedule_ledger"] = appointments
                sync_input_to_db("clinic_schedule_ledger")
                st.success(f"Slot verified and successfully logged down for {st.session_state['patients_registry'][sch_pid]['name']}!")
                st.rerun()

        with col_sch2:
            st.markdown("#### 📋 Existing Appointments Ledger Timeline Matrix")
            if appointments:
                df_all = pd.DataFrame(appointments)
                unique_dates = df_all["Date"].unique()
                
                for day_date in unique_dates:
                    df_day = df_all[df_all["Date"] == day_date]
                    day_name = df_day["Day"].iloc[0]
                    
                    with st.expander(f"📅 {day_date} ({day_name}) — Total: {len(df_day)} Bookings", expanded=True):
                        st.dataframe(df_day[["Time Slot", "Patient Name", "Patient ID", "Case Stream Type", "Linked Target Treatment", "Priority Status"]], 
                                     use_container_width=True, hide_index=True)
            else:
                st.info("Calendar matrix tracking records are completely clear.")

    with sch_tab2:
        st.markdown("#### ✏️ Live Appointment Data Editing Desk")
        if appointments:
            appt_labels = [f"Idx {idx} | {item['Date']} ({item['Time Slot']}) - {item['Patient Name']}" for idx, item in enumerate(appointments)]
            selected_appt_idx = st.selectbox("Select Scheduled Appointment Line to Edit", options=range(len(appointments)), format_func=lambda x: appt_labels[x])
            
            target_appt = appointments[selected_appt_idx]
            
            try:
                curr_appt_date = datetime.fromisoformat(target_appt["Date"]).date()
            except Exception:
                curr_appt_date = date.today()
                
            ed_col1, ed_col2 = st.columns(2)
            with ed_col1:
                edit_date = st.date_input("Edit Appointment Date", value=curr_appt_date, key="edit_appt_date")
                edit_start_str = st.selectbox("Edit Shift Start Time", options=HALF_HOUR_OPTIONS, index=HALF_HOUR_OPTIONS.index("09:00"), key="edit_shift_start")
                edit_end_str = st.selectbox("Edit Shift End Time", options=HALF_HOUR_OPTIONS, index=HALF_HOUR_OPTIONS.index("17:00"), key="edit_shift_end")
                edit_duration_mode = st.radio("Edit Slot Slicing Steps", options=["30 Minutes", "1 Hour"], horizontal=True, key="edit_duration_mode")
                
                et_start = datetime.strptime(edit_start_str, "%H:%M")
                et_end = datetime.strptime(edit_end_str, "%H:%M")
                edit_slots = []
                es_current = et_start
                es_delta = timedelta(minutes=30) if edit_duration_mode == "30 Minutes" else timedelta(hours=1)
                
                while es_current + es_delta <= et_end:
                    edit_slots.append(f"{es_current.strftime('%H:%M')} - {(es_current + es_delta).strftime('%H:%M')}")
                    es_current += es_delta
                
                try:
                    slot_index = edit_slots.index(target_appt["Time Slot"])
                except ValueError:
                    slot_index = 0
                    
                edit_slot = st.selectbox("Edit Time Slot Window", options=edit_slots if edit_slots else ["N/A"], index=slot_index if edit_slots else 0)
                
            with ed_col2:
                try:
                    class_index = ["New Case", "Open Case"].index(target_appt["Case Stream Type"])
                except ValueError:
                    class_index = 0
                    
                edit_class = st.radio("Modify Booking Strategy Type", options=["New Case", "Open Case"], index=class_index, key="edit_class_choice")
                
                edit_pid = ""
                edit_open_case_detail = "N/A (New Case Intake)"
                
                if edit_class == "New Case":
                    try:
                        pat_keys = list(patient_selectors.keys())
                        pat_index = pat_keys.index(target_appt.get("Patient ID", ""))
                    except ValueError:
                        pat_index = 0
                    edit_pid = st.selectbox("Change Patient Profile", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], index=pat_index, key="edit_pid_select_new")
                else:
                    all_edit_open_cases = get_global_open_cases()
                    if all_edit_open_cases:
                        edit_case_map = {c["unique_key"]: c["display_label"] for c in all_edit_open_cases}
                        current_key_target = f"{target_appt.get('Patient ID')}||{target_appt.get('Linked Target Treatment','').split('Case ')[-1].split(' ')[0]}"
                        try:
                            edit_options_list = list(edit_case_map.keys())
                            default_edit_idx = edit_options_list.index(current_key_target)
                        except ValueError:
                            default_edit_idx = 0
                            
                        edit_chosen_unique_key = st.selectbox("Select Active Open Treatment Case from Master Directory:", options=list(edit_case_map.keys()), format_func=lambda x: edit_case_map[x], index=default_edit_idx, key="edit_global_open_case")
                        edit_pid = edit_chosen_unique_key.split("||")[0]
                        edit_open_case_detail = edit_case_map[edit_chosen_unique_key]
                    else:
                        st.warning("No running Open Cases found anywhere. Forcing edit strategy to New Case mode.")
                        edit_class = "New Case"
                        edit_pid = st.selectbox("Change Patient Profile", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="edit_pid_select_fallback")

                edit_priority = st.checkbox("High Priority Flag", value=(target_appt["Priority Status"] == "High Priority"))
                
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("💾 Apply Appointment Re-scheduling Corrections", type="primary"):
                    appointments[selected_appt_idx] = {
                        "Date": edit_date.isoformat(), "Day": edit_date.strftime('%A'), "Time Slot": edit_slot,
                        "Patient ID": edit_pid, "Patient Name": st.session_state["patients_registry"][edit_pid]["name"],
                        "Case Stream Type": edit_class, "Linked Target Treatment": edit_open_case_detail,
                        "Priority Status": "High Priority" if edit_priority else "Normal"
                    }
                    appointments = sorted(appointments, key=lambda x: (x.get("Date", ""), x.get("Time Slot", "")))
                    st.session_state["clinic_schedule_ledger"] = appointments
                    sync_input_to_db("clinic_schedule_ledger")
                    st.success("Appointment parameters updated and sorted successfully!")
                    st.rerun()
            with btn_col2:
                if st.button("❌ Delete/Cancel This Appointment Slot", type="secondary"):
                    appointments.pop(selected_appt_idx)
                    appointments = sorted(appointments, key=lambda x: (x.get("Date", ""), x.get("Time Slot", "")))
                    st.session_state["clinic_schedule_ledger"] = appointments
                    sync_input_to_db("clinic_schedule_ledger")
                    st.warning("Appointment slot was purged from calendar logs.")
                    st.rerun()
        else:
            st.info("No bookings recorded inside the timeline register.")

# ------------------------------------------------------------------------------
# PAGE 3: TREATMENT PRICE DATABASE PANEL
# ------------------------------------------------------------------------------
elif page == "📋 Treatment Price Database Panel":
    st.subheader("📋 Core Treatment Matrix & Pricing Fee Tariffs (TL ₺)")
    
    adm_t1, adm_t2 = st.tabs(["➕ Introduce New Treatment Type", "✏️ Update Existing Base Prices"])
    
    with adm_t1:
        st.markdown("#### Add Brand New Treatment Entry Option to Catalog")
        st.selectbox("Select Domain Structure Category Block", options=list(st.session_state["treatment_catalog_db"].keys()), key="adm_add_cat")
        st.text_input("New Treatment Procedure Label Name", key="adm_add_name")
        st.number_input("Base Global Rate Cost Fee (TL ₺)", min_value=0.0, step=100.0, key="adm_add_price")
        st.button("🚀 Insert New Treatment Type Option", on_click=cb_add_catalog_procedure, type="primary")

    with adm_t2:
        st.markdown("#### Modify Configured Tariff Fee Base Scale Parameters")
        st.selectbox("Choose Target Category Group Block", options=list(st.session_state["treatment_catalog_db"].keys()), key="adm_edit_cat")
        
        sub_procedures = list(st.session_state["treatment_catalog_db"].get(st.session_state["adm_edit_cat"], {}).keys())
        if sub_procedures:
            st.selectbox("Choose Target Treatment Option to Modify", options=sub_procedures, key="adm_edit_treat")
            st.number_input("Enter New Standard Cost Level Value (TL ₺)", min_value=0.0, step=100.0, key="adm_edit_price")
            
            if st.button("💾 Apply Updated Price Changes", type="primary"):
                e_cat = st.session_state["adm_edit_cat"]
                e_trt = st.session_state["adm_edit_treat"]
                e_prc = float(st.session_state["adm_edit_price"])
                
                st.session_state["treatment_catalog_db"][e_cat][e_trt] = e_prc
                sync_input_to_db("treatment_catalog_db")
                st.success(f"Modified base pricing parameter for '{e_trt}' to {e_prc:,.2f} TL!")
        else:
            st.info("No records are found inside this category block.")

    st.markdown("---")
    st.markdown("#### 📋 Current Treatment Pricing Master Directory Log View")
    flat_records = []
    for category, item_map in st.session_state["treatment_catalog_db"].items():
        for item, rate in item_map.items():
            flat_records.append({"Category Group": category, "Procedure Operational Name": item, "Configured Standard Base Fee": f"{rate:,.2f} TL"})
    st.dataframe(pd.DataFrame(flat_records), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# PAGE 4: PATIENT HISTORY LOOKUP
# ------------------------------------------------------------------------------
elif page == "🔍 Patient History Lookup":
    st.subheader("🔍 Patient Comprehensive File Tracking Room")
    lookup_pid = st.selectbox("Select Patient Target Index File", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x])
    p_profile = st.session_state["patients_registry"][lookup_pid]
    
    st.markdown(f"**Name:** {p_profile['name']} | **Contact Line:** {p_profile['phone']} | **Age:** {p_profile['age']} | **Default Registered Center:** {p_profile['center']}")
    
    h_tab1, h_tab2, h_tab3 = st.tabs(["📊 Case Tracking Lifecycles", "💰 Account Transaction Statement Logs & Editing", "🦷 Isolated Tooth History Charts"])
    
    with h_tab1:
        pt_cases = st.session_state.get("patient_cases_tracker", {}).get(lookup_pid, [])
        if pt_cases:
            st.dataframe(pd.DataFrame(pt_cases), use_container_width=True, hide_index=True)
        else:
            st.info("No recorded running or historical sequential treatment lines verified for this patient profile.")
            
    with h_tab2:
        p_tx_history = st.session_state["finance_ledger"].get(lookup_pid, [])
        if p_tx_history:
            df_fin = pd.DataFrame(p_tx_history)
            st.metric("Total Net Balance Outstanding Debt (TL ₺)", f"{df_fin['balance'].sum():,.2f} TL")
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("#### ✏️ Live Session Data Revision Desk")
            
            tx_labels = [f"Idx {idx} | {item['date']} - {item['procedure'][:40]}..." for idx, item in enumerate(p_tx_history)]
            selected_tx_idx = st.selectbox("Select Exact Transaction Entry Line to Edit", options=range(len(p_tx_history)), format_func=lambda x: tx_labels[x])
            
            target_tx = p_tx_history[selected_tx_idx]
            
            edit_col1, edit_col2, edit_col3 = st.columns(3)
            with edit_col1:
                updated_procedure_text = st.text_input("Edit Logged Procedure Description", value=target_tx.get("procedure", ""))
                updated_gross = st.number_input("Corrected Gross Total (TL)", min_value=0.0, value=float(target_tx.get("gross_calculated", target_tx.get("total_due", 0.0))))
            with edit_col2:
                updated_discount = st.number_input("Corrected Discount (TL)", min_value=0.0, value=float(target_tx.get("discount_applied", 0.0)))
                updated_paid = st.number_input("Corrected Collected Cash Amount (TL)", min_value=0.0, value=float(target_tx.get("amount_paid", 0.0)))
            with edit_col3:
                updated_method = st.selectbox("Corrected Payment Gateway", options=PAYMENT_METHODS, index=PAYMENT_METHODS.index(target_tx["method"]) if target_tx["method"] in PAYMENT_METHODS else 0)
                
            if st.button("💾 Apply Session Data Corrections", type="primary"):
                new_total_due = max(0.0, updated_gross - updated_discount)
                new_balance = new_total_due - updated_paid
                
                p_tx_history[selected_tx_idx] = {
                    "date": target_tx["date"], "procedure": updated_procedure_text, "gross_calculated": updated_gross,
                    "discount_applied": updated_discount, "total_due": new_total_due, "amount_paid": updated_paid,
                    "method": updated_method if updated_paid > 0 else "N/A", "balance": new_balance
                }
                st.session_state["finance_ledger"][lookup_pid] = p_tx_history
                sync_input_to_db("finance_ledger")
                st.success("Session ledger log updated successfully!")
                st.rerun()
        else:
            st.info("Financial account ledgers contain zero invoicing movements.")
            
    with h_tab3:
        all_possible_teeth = all_adult_palmer + all_child_palmer
        selected_tooth = st.selectbox("Choose Target Tooth Space Profile to Track", options=all_possible_teeth)
        records = st.session_state["tooth_history_ledger"].get(lookup_pid, {}).get(selected_tooth, [])
        if records:
            st.table(pd.DataFrame(records))
        else:
            st.warning(f"No clinical procedure history details logged on Tooth {selected_tooth}.")

# ------------------------------------------------------------------------------
# PAGE 5: PATIENT REGISTRATION MANAGER
# ------------------------------------------------------------------------------
elif page == "👥 Patient Registration Manager":
    st.subheader("👥 Patient Master Profile Intake & Modification Desk")
    
    reg_tab1, reg_tab2 = st.tabs(["➕ Introduce New Patient Profile", "✏️ Edit Existing Patient Registry Files"])
    
    with reg_tab1:
        c_adm1, c_adm2 = st.columns([1, 2])
        with c_adm1:
            st.text_input("Full Patient Registration Name", key="new_pat_name")
            st.text_input("Mobile Contact Phone Line", key="new_pat_phone")
            st.number_input("Patient Age", min_value=0, max_value=120, key="new_pat_age", step=1)
            st.selectbox("Default Assigned Medical Center Site", options=CENTERS, key="new_pat_center")
            st.button("🚀 File Complete Patient Profile Intake", on_click=cb_add_new_patient, type="primary")
            
        with c_adm2:
            raw_patients = []
            for pid, d in st.session_state["patients_registry"].items():
                raw_patients.append({"ID Profile Code": pid, "Full Name": d["name"], "Contact Line Mobile": d["phone"], "Age": d["age"]})
            st.dataframe(pd.DataFrame(raw_patients), use_container_width=True, hide_index=True)

    with reg_tab2:
        st.markdown("#### Modify Configured Patient Registry Information Data Fields")
        edit_pid = st.selectbox("Select Patient Target File to Edit", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="pat_edit_selector")
        
        if edit_pid:
            current_profile = st.session_state["patients_registry"][edit_pid]
            edit_name = st.text_input("Modify Full Name", value=current_profile["name"])
            edit_phone = st.text_input("Modify Mobile Contact Phone Line", value=current_profile["phone"])
            edit_age = st.number_input("Modify Patient Age", value=int(current_profile.get("age", 30)), min_value=0, max_value=120, step=1)
            
            curr_center_idx = CENTERS.index(current_profile["center"]) if current_profile["center"] in CENTERS else 0
            edit_center = st.selectbox("Modify Assigned Medical Center Site", options=CENTERS, index=curr_center_idx)
            
            if st.button("💾 Apply Profile Update Changes", type="primary"):
                st.session_state["patients_registry"][edit_pid] = {"name": edit_name.strip(), "phone": edit_phone.strip(), "center": edit_center, "age": int(edit_age)}
                sync_input_to_db("patients_registry")
                st.success(f"Profile {edit_pid} successfully overwritten inside registry file matrix.")
                st.rerun()

# ------------------------------------------------------------------------------
# PAGE 6: FINANCIAL ANALYTICS MATRIX (NEW PAGE)
# ------------------------------------------------------------------------------
elif page == "💰 Financial Analytics Matrix":
    st.subheader("💰 Financial Performance & Fee Splitting Engine")
    
    fin_tab1, fin_tab2, fin_tab3 = st.tabs([
        "📋 Outstanding Receivables (Money Owed)", 
        "📈 Daily Income Split (60% / 40%)", 
        "📅 Monthly Financial Summary Ledger"
    ])
    
    # Compilation Step: Extract all individual transactions from all patients into a single flat list
    master_tx_list = []
    ledger_data = st.session_state.get("finance_ledger", {})
    registry_data = st.session_state.get("patients_registry", {})
    
    for pid, tx_records in ledger_data.items():
        p_name = registry_data.get(pid, {}).get("name", f"Unknown ({pid})")
        for record in tx_records:
            master_tx_list.append({
                "Patient ID": pid,
                "Patient Name": p_name,
                "Date": record.get("date", ""),
                "Procedure": record.get("procedure", ""),
                "Gross Total": float(record.get("gross_calculated", 0.0)),
                "Discount": float(record.get("discount_applied", 0.0)),
                "Net Invoiced Due": float(record.get("total_due", 0.0)),
                "Amount Paid (Income)": float(record.get("amount_paid", 0.0)),
                "Unpaid Balance": float(record.get("balance", 0.0))
            })
            
    df_master = pd.DataFrame(master_tx_list) if master_tx_list else pd.DataFrame(
        columns=["Patient ID", "Patient Name", "Date", "Procedure", "Gross Total", "Discount", "Net Invoiced Due", "Amount Paid (Income)", "Unpaid Balance"]
    )
    
    with fin_tab1:
        st.markdown("#### 📋 Money Owed to Clinic by Patient Profile")
        
        if not df_master.empty:
            # Group by patient to find cumulative unpaid debt balances
            df_receivables = df_master.groupby(["Patient ID", "Patient Name"])["Unpaid Balance"].sum().reset_index()
            # Filter to show only patients who actually owe money
            df_receivables = df_receivables[df_receivables["Unpaid Balance"] > 0].sort_values(by="Unpaid Balance", ascending=False)
            
            if not df_receivables.empty:
                total_outstanding = df_receivables["Unpaid Balance"].sum()
                st.metric("Total Clinic Outstanding Receivables", f"{total_outstanding:,.2f} TL")
                
                # Format for clean display
                df_receivables_display = df_receivables.copy()
                df_receivables_display["Unpaid Balance"] = df_receivables_display["Unpaid Balance"].map(lambda x: f"{x:,.2f} TL")
                st.dataframe(df_receivables_display, use_container_width=True, hide_index=True)
            else:
                st.success("🎉 Perfect balance sheet! No patient has any outstanding debt lines.")
        else:
            st.info("No transaction tracking records found in database.")
            
    with fin_tab2:
        st.markdown("#### 📈 Daily Income Aggregation & Revenue Splits")
        
        if not df_master.empty:
            # Group by clean transaction date string
            df_daily = df_master.groupby("Date")["Amount Paid (Income)"].sum().reset_index()
            df_daily = df_daily.rename(columns={"Amount Paid (Income)": "Total Revenue (Collected)"})
            
            # Mathematical 60/40 Commission Splits Strategy
            df_daily["Medical Center Share (60%)"] = df_daily["Total Revenue (Collected)"] * 0.60
            df_daily["My Share (40%)"] = df_daily["Total Revenue (Collected)"] * 0.40
            
            # Chronological presentation
            df_daily = df_daily.sort_values(by="Date", ascending=False)
            
            # Format numbers for professional display look
            df_daily_display = df_daily.copy()
            for col in ["Total Revenue (Collected)", "Medical Center Share (60%)", "My Share (40%)"]:
                df_daily_display[col] = df_daily_display[col].map(lambda x: f"{x:,.2f} TL")
                
            st.dataframe(df_daily_display, use_container_width=True, hide_index=True)
        else:
            st.info("No income collections recorded yet.")
            
    with fin_tab3:
        st.markdown("#### 📅 Cumulative Monthly Performance Summary")
        
        if not df_master.empty:
            df_monthly_calc = df_master.copy()
            # Extract Year-Month string (YYYY-MM) from string date formats securely
            df_monthly_calc["Month"] = df_monthly_calc["Date"].apply(lambda x: x[:7] if isinstance(x, str) else date.today().strftime('%Y-%m'))
            
            df_month = df_monthly_calc.groupby("Month")["Amount Paid (Income)"].sum().reset_index()
            df_month = df_month.rename(columns={"Amount Paid (Income)": "Total Monthly Revenue"})
            
            # Monthly structural share distributions
            df_month["Medical Center Share (60%)"] = df_month["Total Monthly Revenue"] * 0.60
            df_month["My Share (40%)"] = df_month["Total Monthly Revenue"] * 0.40
            
            df_month = df_month.sort_values(by="Month", ascending=False)
            
            df_month_display = df_month.copy()
            for col in ["Total Monthly Revenue", "Medical Center Share (60%)", "My Share (40%)"]:
                df_month_display[col] = df_month_display[col].map(lambda x: f"{x:,.2f} TL")
                
            st.dataframe(df_month_display, use_container_width=True, hide_index=True)
        else:
            st.info("No transaction activity found to calculate monthly profiles.")
