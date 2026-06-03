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
# 2. DATABASE SEEDING & INITIALIZATION (TL NATIVE DEFAULTS)
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
    "P0001": {"name": "Yusuf Demir", "phone": "+90 532 123 4567", "center": "Istanbul Tower", "age": 28, "birth_date": "1998-05-12"},
    "P0002": {"name": "Amina El-Amin", "phone": "+90 555 987 6543", "center": "Elsifa Medical Center", "age": 9, "birth_date": "2017-08-20"}
})

cases_db = get_state_val("patient_cases_tracker", {
    "P0001": [{"case_id": "C001", "tooth": "16", "treatment": "Composite Filling", "type": "New Session (New Query)", "status": "Finished", "est_sessions": 1}],
    "P0002": []
})

history_db = get_state_val("tooth_history_ledger", {
    "P0001": {"16": [{"date": "2026-02-15", "treatment": "[New Session] Composite Filling", "center": "Istanbul Tower", "notes": "Initial setup completed.", "status": "Finished"}]}
})

finance_db = get_state_val("finance_ledger", {
    "P0001": [{"date": "2026-02-15", "procedure": "Composite Filling (Tooth: 16)", "total_due": 2500.0, "amount_paid": 2500.0, "method": "Cash", "balance": 0.0}],
    "P0002": []
})

schedule_db = get_state_val("clinic_schedule_ledger", [])

# Persistent Application Inputs State Hooks
get_state_val("session_patient_id", "P0001")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "Composite Filling")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")
get_state_val("session_amount_paid", 0.0)
get_state_val("session_discount_input", 0.0)
get_state_val("session_payment_method", "Cash")
get_state_val("session_type_nature", "New Session (New Query)")
get_state_val("session_work_status", "Open")
get_state_val("session_est_count", 2)
get_state_val("session_high_priority", False)

get_state_val("new_pat_name", "")
get_state_val("new_pat_phone", "")
get_state_val("new_pat_birth", date(2000, 1, 1))
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
    
    st.session_state["patient_cases_tracker"][new_code] = []
    sync_input_to_db("patient_cases_tracker")
    st.session_state["finance_ledger"][new_code] = []
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
    
    # Mathematical integration rules with dynamic session deductions
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
            "date": date.today().isoformat(), "treatment": f"[{nature}] {treat}", 
            "center": center, "notes": st.session_state["session_notes"], "status": work_status
        })
    st.session_state["tooth_history_ledger"] = history
    sync_input_to_db("tooth_history_ledger")
    
    finances = st.session_state.get("finance_ledger", {})
    if pid not in finances: finances[pid] = []
    finances[pid].append({
        "date": date.today().isoformat(),
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
    st.success("Session saved successfully inside transaction ledger data.")

# ==============================================================================
# 4. FIXED SYSTEM PROPERTIES DEFINITIONS
# ==============================================================================
quad_u1 = ["18", "17", "16", "15", "14", "13", "12", "11"]  
quad_u2 = ["21", "22", "23", "24", "25", "26", "27", "28"]  
quad_l2 = ["31", "32", "33", "34", "35", "36", "37", "38"]  
quad_l1 = ["48", "47", "46", "45", "44", "43", "42", "41"]  
all_teeth_options = quad_u1 + quad_u2 + quad_l2 + quad_l1

patient_selectors = {k: f"{v['name']} [{k}]" for k, v in st.session_state["patients_registry"].items()}

# ==============================================================================
# 5. UI LAYOUT ARCHITECTURE
# ==============================================================================
st.set_page_config(page_title="Havence System", layout="wide")

st.markdown("""
<style>
    .stButton > button { width: 100% !important; padding: 12px 0px !important; font-size: 15px !important; font-weight: bold !important; border-radius: 8px !important; }
    .mobile-header { text-align: center; font-weight: bold; background-color: #1e293b; color: white; padding: 6px; border-radius: 6px; margin: 12px 0 6px 0; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🦷 Havence Clinical Menu")
page = st.sidebar.radio("Workspace Navigation Layout Options:", [
    "🩺 Active Session Desk", 
    "📅 Shift Scheduler & Booking Desk",
    "📋 Treatment Price Database Panel",
    "🔍 Patient History Lookup",
    "👥 Patient Registration Manager"
])

st.title("Havence Dental Management System")
st.markdown("---")

# ------------------------------------------------------------------------------
# PAGE 1: ACTIVE SESSION DESK (WITH CURRENCY & DISCOUNT MECHANICS)
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
    st.subheader("📱 Mobile Touch Tooth Selection Grid System")
    
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
    st.text_area("Case Notes Data Lines", key="session_notes")
    st.checkbox("⚠️ Assign as HIGH PRIORITY for Next Week Schedule Layout", key="session_high_priority")
    
    st.markdown("### 💸 Checkout Calculation Space (Turkish Lira ₺)")
    calc1, calc2, calc3 = st.columns(3)
    calc1.metric("Gross Starting Sum Cost", f"{gross_cost:,.2f} TL")
    
    # Inline Discount Input Logic
    with calc2:
        discount_val = st.number_input("Apply Session Discount Amount (TL ₺)", min_value=0.0, step=50.0, key="session_discount_input")
    
    final_net_payable = max(0.0, gross_cost - discount_val)
    calc3.metric("Net Invoiced Payable Amount", f"{final_net_payable:,.2f} TL", delta=f"-{discount_val:,.2f} TL" if discount_val > 0 else None, delta_color="inverse")
    
    pay_col1, pay_col2 = st.columns(2)
    pay_col1.number_input("Collected Amount Settled Right Now (TL ₺)", min_value=0.0, max_value=max(final_net_payable, 500000.0), step=100.0, key="session_amount_paid")
    pay_col2.selectbox("Payment Gateway Type", options=PAYMENT_METHODS, key="session_payment_method")
    
    st.button("💾 Commit & File Complete Session Transaction", on_click=cb_save_session_log, type="primary")

# ------------------------------------------------------------------------------
# PAGE 2: SHIFT SCHEDULER & BOOKING DESK
# ------------------------------------------------------------------------------
elif page == "📅 Shift Scheduler & Booking Desk":
    st.subheader("📅 Monday & Thursday Shift Planner Matrix")
    
    col_sch1, col_sch2 = st.columns([1, 1])
    with col_sch1:
        st.markdown("#### 🕒 Booking Blocks")
        start_hour = st.number_input("Start Hour Window (24h)", min_value=0, max_value=23, value=9)
        end_hour = st.number_input("End Hour Window (24h)", min_value=start_hour+1, max_value=24, value=17)
        target_date = st.date_input("Select Plan Date Target", value=date.today())
        
        if target_date.weekday() not in [0, 3]:
            st.error("❌ Invalid Shift Selection! Please book onto a Monday or Thursday calendar path.")
            is_valid_day = False
        else:
            st.success(f"✅ Approved Working Shift: {target_date.strftime('%A')}")
            is_valid_day = True
            
        time_slots = [f"{h:02d}:00 - {h+1:02d}:00" for h in range(start_hour, end_hour)]
        selected_slot = st.selectbox("1-Hour Scheduled Slots", options=time_slots)
        
        sch_pid = st.selectbox("Assign Patient ID", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x])
        sch_case_class = st.radio("Intake Case Classification Group", options=["New Case", "Open Case"], horizontal=True)
        
        selected_open_case_detail = "N/A (New Case Intake)"
        if sch_case_class == "Open Case":
            open_cases = [c for c in st.session_state.get("patient_cases_tracker", {}).get(sch_pid, []) if c["status"] == "Open"]
            if open_cases:
                case_options = {f"{c['case_id']}": f"Tooth {c['tooth']} - {c['treatment']} ({c['est_sessions']} left)" for c in open_cases}
                chosen_cid = st.selectbox("Select Active Open Treatment Case to Continue:", options=list(case_options.keys()), format_func=lambda x: case_options[x])
                selected_open_case_detail = case_options[chosen_cid]
            else:
                st.warning("No active Open Cases located for this profile! Resetting entry path to New Case.")
                sch_case_class = "New Case"
                
        sch_priority = st.checkbox("High Priority Allocation Status Flag")
        
        if st.button("📝 Book Appointment Slot Entry Line", disabled=not is_valid_day, type="primary"):
            sched_list = st.session_state.get("clinic_schedule_ledger", [])
            sched_list.append({
                "Date": target_date.isoformat(), "Day": target_date.strftime('%A'), "Time Slot": selected_slot,
                "Patient Name": st.session_state["patients_registry"][sch_pid]["name"], 
                "Case Stream Type": sch_case_class, "Linked Target Treatment": selected_open_case_detail,
                "Priority Status": "High Priority" if sch_priority else "Normal"
            })
            st.session_state["clinic_schedule_ledger"] = sched_list
            sync_input_to_db("clinic_schedule_ledger")
            st.success("Slot verified and successfully written down!")

    with col_sch2:
        st.markdown("#### 📋 Existing Appointments Ledger Timeline Matrix")
        appointments = st.session_state.get("clinic_schedule_ledger", [])
        if appointments:
            st.dataframe(pd.DataFrame(appointments), use_container_width=True, hide_index=True)
        else:
            st.info("Calendar matrix tracking records are completely clear.")

# ------------------------------------------------------------------------------
# PAGE 3: TREATMENT PRICE DATABASE PANEL (REACTIVATED & EXPANDED AS REQUESTED)
# ------------------------------------------------------------------------------
elif page == "📋 Treatment Price Database Panel":
    st.subheader("📋 Core Treatment Matrix & Pricing Fee Tariffs (TL ₺)")
    
    adm_t1, adm_t2 = st.tabs(["➕ Introduce New Treatment Type", "✏️ Update Existing Base Prices"])
    
    with adm_t1:
        st.markdown("#### Add Brand New Treatment Entry Option to Catalog")
        st.selectbox("Select Domain Structure Category Block", options=list(st.session_state["treatment_catalog_db"].keys()), key="adm_add_cat")
        st.text_input("New Treatment Procedure Label Name", key="adm_add_name")
        st.number_input("Base Global Rate Cost Fee (TL ₺)", min_value=0.0, step=100.0, key="adm_add_price")
        
        if st.button("🚀 Insert New Treatment Type Option", type="primary"):
            a_cat = st.session_state["adm_add_cat"]
            a_name = st.session_state["adm_add_name"].strip()
            a_prc = float(st.session_state["adm_add_price"])
            
            if a_name:
                st.session_state["treatment_catalog_db"][a_cat][a_name] = a_prc
                sync_input_to_db("treatment_catalog_db")
                st.success(f"Successfully appended '{a_name}' under {a_cat} with base rate {a_prc:,.2f} TL!")
                st.session_state["adm_add_name"] = ""
            else:
                st.error("Procedure label value cannot be blank!")

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
    
    st.markdown(f"**Name:** {p_profile['name']} | **Contact Line:** {p_profile['phone']} | **Default Registered Center:** {p_profile['center']}")
    
    h_tab1, h_tab2, h_tab3 = st.tabs(["📊 Case Tracking Lifecycles", "💰 Account Transaction Statement Logs", "🦷 Isolated Tooth History Charts"])
    
    with h_tab1:
        pt_cases = st.session_state.get("patient_cases_tracker", {}).get(lookup_pid, [])
        if pt_cases:
            st.dataframe(pd.DataFrame(pt_cases), use_container_width=True, hide_index=True)
        else:
            st.info("No recorded running or historical medical sequential treatment lines verified for this patient profile.")
            
    with h_tab2:
        p_tx_history = st.session_state["finance_ledger"].get(lookup_pid, [])
        if p_tx_history:
            df_fin = pd.DataFrame(p_tx_history)
            st.metric("Total Net Balance Outstanding Debt (TL ₺)", f"{df_fin['balance'].sum():,.2f} TL")
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
        else:
            st.info("Financial account ledgers contain zero invoicing movements.")
            
    with h_tab3:
        selected_tooth = st.selectbox("Choose Target Tooth Space Profile to Track", options=all_teeth_options)
        records = st.session_state["tooth_history_ledger"].get(lookup_pid, {}).get(selected_tooth, [])
        if records:
            st.table(pd.DataFrame(records))
        else:
            st.warning(f"No clinical procedure history details logged on Tooth {selected_tooth}.")

# ------------------------------------------------------------------------------
# PAGE 5: PATIENT REGISTRATION MANAGER
# ------------------------------------------------------------------------------
elif page == "👥 Patient Registration Manager":
    st.subheader("👥 Patient Master Profile Intake Desk")
    
    c_adm1, c_adm2 = st.columns([1, 2])
    with c_adm1:
        st.text_input("Full Patient Registration Name", key="new_pat_name")
        st.text_input("Mobile Contact Phone Line", key="new_pat_phone")
        st.date_input("Date of Birth", key="new_pat_birth")
        st.selectbox("Default Assigned Medical Center Site", options=CENTERS, key="new_pat_center")
        st.button("🚀 File Complete Patient Profile Intake", on_click=cb_add_new_patient, type="primary")
        
    with c_adm2:
        raw_patients = []
        for pid, d in st.session_state["patients_registry"].items():
            raw_patients.append({"ID Profile Code": pid, "Full Name": d["name"], "Contact Line Mobile": d["phone"], "Clinic Facility Location": d["center"]})
        st.dataframe(pd.DataFrame(raw_patients), use_container_width=True, hide_index=True)
