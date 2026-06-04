import json
import os
from datetime import datetime, date, timedelta
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. CENTRAL DATA PERSISTENCE LAYER (STRICT STORAGE-FIRST)
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
            # Immediately commit default structure to file if it didn't exist
            db_data[key] = default_value
            save_db(db_data)
    return st.session_state[key]

def sync_input_to_db(key):
    if key in st.session_state:
        db_data = load_db()
        db_data[key] = st.session_state[key]
        save_db(db_data)

# ==============================================================================
# 2. STRICTLY CLEAN STRUCTURAL INITIALIZATION (NO FORCED DEFAULT RECORDS)
# ==============================================================================
CENTERS = ["Istanbul Tower", "Elsifa Medical Center"]
PAYMENT_METHODS = ["Cash", "Bank Transfer", "Credit Card"]

# Ensure structure is sound without adding fake text rows
catalog_db = get_state_val("treatment_catalog_db", {"Adult Dentistry": {}, "Children Dentistry": {}})
patients_db = get_state_val("patients_registry", {})
cases_db = get_state_val("patient_cases_tracker", {})
history_db = get_state_val("tooth_history_ledger", {})
finance_db = get_state_val("finance_ledger", {})
schedule_db = get_state_val("clinic_schedule_ledger", [])

# Core Session state variables
get_state_val("session_patient_id", "")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")
get_state_val("session_log_date", date.today())
get_state_val("session_amount_paid", 0.0)
get_state_val("session_discount_input", 0.0)
get_state_val("session_payment_method", "Cash")
get_state_val("session_type_nature", "New Session (New Query)")
get_state_val("session_work_status", "Open")
get_state_val("session_est_count", 1)
get_state_val("session_high_priority", False)

get_state_val("new_pat_name", "")
get_state_val("new_pat_phone", "")
get_state_val("new_pat_age", 30)
get_state_val("new_pat_center", CENTERS[0])

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
    
    registry[new_code] = {"name": name, "phone": phone, "center": center, "age": age}
    st.session_state["patients_registry"] = registry
    sync_input_to_db("patients_registry")
    
    if new_code not in st.session_state["patient_cases_tracker"]:
        st.session_state["patient_cases_tracker"][new_code] = []
        sync_input_to_db("patient_cases_tracker")
    if new_code not in st.session_state["finance_ledger"]:
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
    
    if not pid:
        st.error("Please pick or register a valid patient first.")
        return
    if not teeth: 
        st.error("Please pick active target teeth from the matrix layout.")
        return
        
    center = st.session_state["patients_registry"][pid]["center"]
    
    if nature == "Repeated Session (Follow-up)":
        unit_rate = 0.0
    else:
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
        "procedure": f"[{nature}] {treat} (Teeth: {', '.join(sorted(teeth))})",
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
    st.success("Session saved successfully!")

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

HALF_HOUR_OPTIONS = [f"{h:02d}:00" for h in range(24)] + [f"{h:02d}:30" for h in range(24)]
HALF_HOUR_OPTIONS.sort()

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
    st.subheader("🩺 Clinical Treatment Intake Engine")
    
    if not patient_selectors:
        st.warning("⚠️ No patients registered yet. Please go to the '👥 Patient Registration Manager' tab first.")
    else:
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
        
        active_cat = st.session_state["session_category"]
        available_procedures = list(st.session_state["treatment_catalog_db"].get(active_cat, {}).keys())
        
        if not available_procedures:
            st.info("No procedures found under this category. Please add prices in the Catalog menu.")
        else:
            st.selectbox("Procedure Operational Selection Line Plan", options=available_procedures, key="session_treatment")
            
            active_teeth = st.session_state.get("session_selected_teeth", [])
            
            if st.session_state["session_type_nature"] == "Repeated Session (Follow-up)":
                unit_price = 0.0
                st.info("🔄 Follow-up session detected. Base cost for selected teeth evaluated automatically at **0.00 TL**.")
            else:
                unit_price = st.session_state["treatment_catalog_db"][active_cat].get(st.session_state["session_treatment"], 0.0)
                
            gross_cost = unit_price * len(active_teeth)

            st.markdown("---")
            st.subheader("📱 Mobile Touch Palmer Mapping Grid System")
            
            if active_cat == "Children Dentistry":
                q_ur, q_ul, q_lr, q_ll = child_quad_ur, child_quad_ul, child_quad_lr, child_quad_ll
            else:
                q_ur, q_ul, q_lr, q_ll = adult_quad_ur, adult_quad_ul, adult_quad_lr, adult_quad_ll
                
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
            calc3.metric("Net Invoiced Payable Amount", f"{final_net_payable:,.2f} TL")
            
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

    with sch_tab1:
        if not patient_selectors:
            st.info("Please register patients to open booking calendars.")
        else:
            col_sch1, col_sch2 = st.columns([1, 1])
            with col_sch1:
                start_str = st.selectbox("Shift Start Time", options=HALF_HOUR_OPTIONS, index=HALF_HOUR_OPTIONS.index("09:00"), key="sch_shift_start")
                end_str = st.selectbox("Shift End Time", options=HALF_HOUR_OPTIONS, index=HALF_HOUR_OPTIONS.index("17:00"), key="sch_shift_end")
                target_date = st.date_input("Select Plan Date Target", value=date.today(), key="sch_target_date")
                duration_mode = st.radio("Appointment Step Duration", options=["30 Minutes", "1 Hour"], horizontal=True, key="sch_duration_mode")
                
                t_start = datetime.strptime(start_str, "%H:%M")
                t_end = datetime.strptime(end_str, "%H:%M")
                time_slots = []
                current_slot_time = t_start
                step_delta = timedelta(minutes=30) if duration_mode == "30 Minutes" else timedelta(hours=1)
                
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
                        chosen_unique_key = st.selectbox("Select Active Open Treatment Case:", options=list(case_map.keys()), format_func=lambda x: case_map[x], key="sch_global_open_case")
                        sch_pid = chosen_unique_key.split("||")[0]
                        selected_open_case_detail = case_map[chosen_unique_key]
                    else:
                        st.warning("No active running Open Cases found. Reverting to New Case.")
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
                    st.session_state["clinic_schedule_ledger"] = sorted(appointments, key=lambda x: (x.get("Date", ""), x.get("Time Slot", "")))
                    sync_input_to_db("clinic_schedule_ledger")
                    st.success("Slot verified and logged down!")
                    st.rerun()

            with col_sch2:
                if appointments:
                    df_all = pd.DataFrame(appointments)
                    for day_date in df_all["Date"].unique():
                        df_day = df_all[df_all["Date"] == day_date]
                        with st.expander(f"📅 {day_date} — Total: {len(df_day)} Bookings", expanded=True):
                            st.dataframe(df_day[["Time Slot", "Patient Name", "Patient ID", "Case Stream Type", "Priority Status"]], use_container_width=True, hide_index=True)

    with sch_tab2:
        if appointments:
            appt_labels = [f"Idx {idx} | {item['Date']} ({item['Time Slot']}) - {item['Patient Name']}" for idx, item in enumerate(appointments)]
            selected_appt_idx = st.selectbox("Select Scheduled Appointment Line to Edit", options=range(len(appointments)), format_func=lambda x: appt_labels[x])
            
            if st.button("❌ Delete/Cancel This Appointment Slot", type="secondary"):
                appointments.pop(selected_appt_idx)
                st.session_state["clinic_schedule_ledger"] = appointments
                sync_input_to_db("clinic_schedule_ledger")
                st.warning("Appointment slot cancelled.")
                st.rerun()

# ------------------------------------------------------------------------------
# PAGE 3: TREATMENT PRICE DATABASE PANEL
# ------------------------------------------------------------------------------
elif page == "📋 Treatment Price Database Panel":
    st.subheader("📋 Catalog Pricing Panels")
    adm_t1, adm_t2 = st.tabs(["➕ Introduce New Treatment Type", "✏️ Update Existing Base Prices"])
    
    with adm_t1:
        st.selectbox("Select Domain Block", options=list(st.session_state["treatment_catalog_db"].keys()), key="adm_add_cat")
        st.text_input("New Treatment Name", key="adm_add_name")
        st.number_input("Base Cost Rate (TL)", min_value=0.0, step=100.0, key="adm_add_price")
        if st.button("🚀 Insert Option", type="primary"):
            if st.session_state["adm_add_name"].strip():
                st.session_state["treatment_catalog_db"][st.session_state["adm_add_cat"]][st.session_state["adm_add_name"].strip()] = float(st.session_state["adm_add_price"])
                sync_input_to_db("treatment_catalog_db")
                st.success("Added successfully!")

    with adm_t2:
        st.selectbox("Choose Target Category", options=list(st.session_state["treatment_catalog_db"].keys()), key="adm_edit_cat")
        sub_procedures = list(st.session_state["treatment_catalog_db"].get(st.session_state["adm_edit_cat"], {}).keys())
        if sub_procedures:
            st.selectbox("Choose Treatment to Modify", options=sub_procedures, key="adm_edit_treat")
            st.number_input("Enter New Value (TL)", min_value=0.0, step=100.0, key="adm_edit_price")
            if st.button("💾 Apply Price Changes", type="primary"):
                st.session_state["treatment_catalog_db"][st.session_state["adm_edit_cat"]][st.session_state["adm_edit_treat"]] = float(st.session_state["adm_edit_price"])
                sync_input_to_db("treatment_catalog_db")
                st.success("Price updated!")

    st.markdown("---")
    flat_records = []
    for category, item_map in st.session_state["treatment_catalog_db"].items():
        for item, rate in item_map.items():
            flat_records.append({"Category Group": category, "Procedure Operational Name": item, "Configured Standard Base Fee": f"{rate:,.2f} TL"})
    if flat_records:
        st.dataframe(pd.DataFrame(flat_records), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# PAGE 4: PATIENT HISTORY LOOKUP
# ------------------------------------------------------------------------------
elif page == "🔍 Patient History Lookup":
    st.subheader("🔍 Patient Comprehensive File Tracking Room")
    if not patient_selectors:
        st.info("No records found. Complete a registration first.")
    else:
        lookup_pid = st.selectbox("Select Patient Target Index File", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x])
        p_profile = st.session_state["patients_registry"][lookup_pid]
        
        st.markdown(f"**Name:** {p_profile['name']} | **Contact:** {p_profile['phone']} | **Default Site:** {p_profile['center']}")
        
        h_tab1, h_tab2, h_tab3 = st.tabs(["📊 Case Lifecycles", "💰 Account Transaction Statement Logs", "🦷 Tooth Charts"])
        
        with h_tab1:
            pt_cases = st.session_state.get("patient_cases_tracker", {}).get(lookup_pid, [])
            if pt_cases: st.dataframe(pd.DataFrame(pt_cases), use_container_width=True, hide_index=True)
            else: st.info("No recorded cases found.")
                
        with h_tab2:
            p_tx_history = st.session_state["finance_ledger"].get(lookup_pid, [])
            df_fin = pd.DataFrame(p_tx_history) if p_tx_history else pd.DataFrame()
            
            current_debt = df_fin['balance'].sum() if not df_fin.empty else 0.0
            st.metric("Total Outstanding Debt Balance (TL ₺)", f"{current_debt:,.2f} TL")
            
            st.markdown("---")
            st.markdown("#### 💳 Collect Direct Debt Payment (Without Clinical Session)")
            
            pay_col1, pay_col2, pay_col3 = st.columns(3)
            direct_amt = pay_col1.number_input("Amount Paid to Clear Debt (TL ₺)", min_value=0.0, max_value=max(current_debt, 500000.0), step=50.0, key="dir_pay_amt")
            direct_method = pay_col2.selectbox("Payment Gateway Type", options=PAYMENT_METHODS, key="dir_pay_method")
            direct_date = pay_col3.date_input("Payment Collection Date", value=date.today(), key="dir_pay_date")
            
            if st.button("🤝 Log Direct Debt Payment", type="primary"):
                if direct_amt <= 0:
                    st.error("Please insert a payment collection amount greater than 0.")
                else:
                    finances = st.session_state.get("finance_ledger", {})
                    if lookup_pid not in finances: finances[lookup_pid] = []
                    
                    finances[lookup_pid].append({
                        "date": direct_date.isoformat(),
                        "procedure": f"💳 Direct Balance Payment [No Session Logged] - Clarified Debt Settled",
                        "gross_calculated": 0.0,
                        "discount_applied": 0.0,
                        "total_due": 0.0, 
                        "amount_paid": direct_amt, 
                        "method": direct_method, 
                        "balance": -direct_amt
                    })
                    st.session_state["finance_ledger"] = finances
                    sync_input_to_db("finance_ledger")
                    st.success(f"Successfully tracked direct payment of {direct_amt:,.2f} TL down into finance ledger indices!")
                    st.rerun()

            st.markdown("---")
            st.markdown("#### Transaction Ledger Log View")
            if not df_fin.empty: st.dataframe(df_fin, use_container_width=True, hide_index=True)
            else: st.info("Financial account ledgers contain zero invoicing movements.")
                
        with h_tab3:
            selected_tooth = st.selectbox("Choose Target Tooth Space Profile to Track", options=all_adult_palmer + all_child_palmer)
            records = st.session_state["tooth_history_ledger"].get(lookup_pid, {}).get(selected_tooth, [])
            if records: st.table(pd.DataFrame(records))
            else: st.warning(f"No clinical history logged on Tooth {selected_tooth}.")

# ------------------------------------------------------------------------------
# PAGE 5: PATIENT REGISTRATION MANAGER
# ------------------------------------------------------------------------------
elif page == "👥 Patient Registration Manager":
    st.subheader("👥 Patient Profile Desk")
    reg_tab1, reg_tab2 = st.tabs(["➕ Introduce New Patient Profile", "✏️ Edit Existing Patient Registry Files"])
    
    with reg_tab1:
        c_adm1, c_adm2 = st.columns([1, 2])
        with c_adm1:
            st.text_input("Full Patient Name", key="new_pat_name")
            st.text_input("Mobile Contact Phone Line", key="new_pat_phone")
            st.number_input("Patient Age", min_value=0, max_value=120, key="new_pat_age", step=1)
            st.selectbox("Medical Center Site", options=CENTERS, key="new_pat_center")
            st.button("🚀 File Patient Profile Intake", on_click=cb_add_new_patient, type="primary")
        with c_adm2:
            if st.session_state["patients_registry"]:
                raw_pats = [{"ID Code": k, "Name": v["name"], "Phone": v["phone"], "Location": v.get("center","")} for k, v in st.session_state["patients_registry"].items()]
                st.dataframe(pd.DataFrame(raw_pats), use_container_width=True, hide_index=True)

    with reg_tab2:
        if not patient_selectors:
            st.info("Registry is empty.")
        else:
            edit_pid = st.selectbox("Select Patient to Edit", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x])
            if edit_pid:
                cur_prof = st.session_state["patients_registry"][edit_pid]
                en = st.text_input("Modify Full Name", value=cur_prof["name"])
                ep = st.text_input("Modify Phone", value=cur_prof["phone"])
                if st.button("💾 Apply Profile Changes", type="primary"):
                    st.session_state["patients_registry"][edit_pid].update({"name": en.strip(), "phone": ep.strip()})
                    sync_input_to_db("patients_registry")
                    st.success("Updated profile layout successfully!")
                    st.rerun()

# ------------------------------------------------------------------------------
# PAGE 6: FINANCIAL ANALYTICS MATRIX
# ------------------------------------------------------------------------------
elif page == "💰 Financial Analytics Matrix":
    st.subheader("💰 Financial Performance Matrix")
    fin_tab1, fin_tab2, fin_tab3 = st.tabs(["📋 Outstanding Receivables", "📈 Daily Income Split (60%/40%)", "📅 Monthly Summary"])
    
    master_tx_list = []
    for pid, tx_records in st.session_state.get("finance_ledger", {}).items():
        p_name = st.session_state.get("patients_registry", {}).get(pid, {}).get("name", f"Unknown ({pid})")
        for record in tx_records:
            master_tx_list.append({
                "Patient ID": pid, "Patient Name": p_name, "Date": record.get("date", ""),
                "Procedure": record.get("procedure", ""), "Amount Paid (Income)": float(record.get("amount_paid", 0.0)),
                "Unpaid Balance": float(record.get("balance", 0.0))
            })
    df_master = pd.DataFrame(master_tx_list) if master_tx_list else pd.DataFrame()

    with fin_tab1:
        if not df_master.empty:
            df_receivables = df_master.groupby(["Patient ID", "Patient Name"])["Unpaid Balance"].sum().reset_index()
            df_receivables = df_receivables[df_receivables["Unpaid Balance"] > 0]
            if not df_receivables.empty:
                st.dataframe(df_receivables, use_container_width=True, hide_index=True)
            else:
                st.success("All balances completely cleared!")
        else: st.info("No balances found.")

    with fin_tab2:
        if not df_master.empty:
            df_daily = df_master.groupby("Date")["Amount Paid (Income)"].sum().reset_index()
            df_daily["Center Share (60%)"] = df_daily["Amount Paid (Income)"] * 0.60
            df_daily["My Share (40%)"] = df_daily["Amount Paid (Income)"] * 0.40
            st.dataframe(df_daily, use_container_width=True, hide_index=True)

    with fin_tab3:
        if not df_master.empty:
            df_master["Month"] = df_master["Date"].apply(lambda x: x[:7] if isinstance(x, str) else date.today().strftime('%Y-%m'))
            df_month = df_master.groupby("Month")["Amount Paid (Income)"].sum().reset_index()
            df_month["Center Share (60%)"] = df_month["Amount Paid (Income)"] * 0.60
            df_month["My Share (40%)"] = df_month["Amount Paid (Income)"] * 0.40
            st.dataframe(df_month, use_container_width=True, hide_index=True)
