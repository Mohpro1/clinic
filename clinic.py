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
        "16": [{"date": "2026-02-15", "treatment": "Composite Filling", "center": "Istanbul Tower", "notes": "Mesial decay managed."}]
    }
})

finance_db = get_state_val("finance_ledger", {
    "P0001": [
        {"date": "2026-02-15", "procedure": "Composite Filling (Teeth: 16)", "total_due": 300.0, "amount_paid": 300.0, "method": "Cash", "balance": 0.0}
    ],
    "P0002": []
})

# Persistent Form State Management Hooks
get_state_val("session_patient_id", "P0001")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "Composite Filling")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")
get_state_val("session_amount_paid", 0.0)
get_state_val("session_payment_method", "Cash")

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
    
    if not name or not phone: 
        st.error("Name and Phone fields cannot be empty!")
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
    
    finances = st.session_state.get("finance_ledger", {})
    finances[new_code] = []
    st.session_state["finance_ledger"] = finances
    sync_input_to_db("finance_ledger")
    
    st.session_state["new_pat_name"] = ""
    st.session_state["new_pat_phone"] = ""
    st.success(f"Registered {name} successfully as {new_code}!")

def cb_update_treatment_price():
    catalog = st.session_state.get("treatment_catalog_db", {})
    cat = st.session_state["edit_cat_select"]
    treat = st.session_state["edit_treat_select"]
    
    if cat in catalog and treat in catalog[cat]:
        catalog[cat][treat] = float(st.session_state["edit_price_val"])
        st.session_state["treatment_catalog_db"] = catalog
        sync_input_to_db("treatment_catalog_db")
        st.success(f"Fee updated for {treat} to ${st.session_state['edit_price_val']:.2f}")

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
    
    if not teeth: 
        st.error("Please pick active target teeth on the layout matrix before committing.")
        return
        
    center = st.session_state["patients_registry"][pid]["center"]
    unit_rate = st.session_state["treatment_catalog_db"][cat].get(treat, 0.0)
    total_cost = unit_rate * len(teeth)
    remaining_balance = total_cost - paid
    
    # 1. Save to Tooth Logs
    history = st.session_state.get("tooth_history_ledger", {})
    if pid not in history: history[pid] = {}
    for t in teeth:
        if t not in history[pid]: history[pid][t] = []
        history[pid][t].append({
            "date": date.today().isoformat(), "treatment": f"[{cat}] {treat}", 
            "center": center, "notes": st.session_state["session_notes"]
        })
    st.session_state["tooth_history_ledger"] = history
    sync_input_to_db("tooth_history_ledger")
    
    # 2. Save Financial Record
    finances = st.session_state.get("finance_ledger", {})
    if pid not in finances: finances[pid] = []
    finances[pid].append({
        "date": date.today().isoformat(),
        "procedure": f"{treat} (Teeth: {', '.join(sorted(teeth))})",
        "total_due": total_cost,
        "amount_paid": paid,
        "method": method if paid > 0 else "N/A",
        "balance": remaining_balance
    })
    st.session_state["finance_ledger"] = finances
    sync_input_to_db("finance_ledger")
    
    st.session_state["session_selected_teeth"] = []
    st.session_state["session_notes"] = ""
    st.session_state["session_amount_paid"] = 0.0
    st.success("Session and payment logs successfully finalized!")

# ==============================================================================
# DATA COMPUTATION PRE-EXECUTION
# ==============================================================================
active_teeth = st.session_state.get("session_selected_teeth", [])
patient_selectors = {k: f"{v['name']} [{k}]" for k, v in st.session_state["patients_registry"].items()}

u_quad1 = ["18", "17", "16", "15", "14", "13", "12", "11"]
u_quad2 = ["21", "22", "23", "24", "25", "26", "27", "28"]
l_quad1 = ["48", "47", "46", "45", "44", "43", "42", "41"]
l_quad2 = ["31", "32", "33", "34", "35", "36", "37", "38"]
all_teeth_options = u_quad1 + u_quad2 + l_quad1 + l_quad2

# ==============================================================================
# UI RENDERING & SIDEBAR NAVIGATION
# ==============================================================================
st.set_page_config(page_title="Havence Clinical Manager", layout="wide")

st.markdown("""
<style>
    div.stButton > button { width: 100% !important; padding: 4px 0px !important; font-size: 13px !important; font-weight: bold !important; }
    .jaw-title { text-align: center; font-weight: bold; background-color: #1f2937; color: white; padding: 5px; border-radius: 4px; margin: 12px 0 6px 0; }
</style>
""", unsafe_allow_html=True)

# Main Navigation Sidebar Menu
st.sidebar.title("🦷 Havence Clinical Menu")
page = st.sidebar.radio("Navigate Workspace:", [
    "🩺 Active Session Desk", 
    "🔍 Patient History Lookup",
    "👥 Patient Registration Manager", 
    "💰 Accounts & Finance Center",
    "📋 Fee Catalog Database"
])

st.title(f" Havence Dental Clinic Management System")
st.markdown("---")

# ------------------------------------------------------------------------------
# PAGE 1: ACTIVE SESSION DESK
# ------------------------------------------------------------------------------
if page == "🩺 Active Session Desk":
    l_box, r_box = st.columns([2, 3])
    
    active_cat = st.session_state.get("session_category", "Adult Dentistry")
    available_procedures = list(st.session_state["treatment_catalog_db"].get(active_cat, {}).keys())

    if st.session_state["session_treatment"] not in available_procedures and available_procedures:
        st.session_state["session_treatment"] = available_procedures[0]

    unit_price = st.session_state["treatment_catalog_db"][active_cat].get(st.session_state["session_treatment"], 0.0)
    gross_cost = unit_price * len(active_teeth)

    with l_box:
        st.subheader("Treatment Setup")
        st.selectbox("Patient Selection File", options=list(patient_selectors.keys()), format_func=lambda x: patient_selectors[x], key="session_patient_id", on_change=sync_input_to_db, args=("session_patient_id",))
        st.selectbox("Age Bracket Group", options=list(st.session_state["treatment_catalog_db"].keys()), key="session_category", on_change=sync_input_to_db, args=("session_category",))
        st.selectbox("Procedure Plan", options=available_procedures, key="session_treatment", on_change=sync_input_to_db, args=("session_treatment",))
        st.text_area("Clinical Case Notes", key="session_notes", on_change=sync_input_to_db, args=("session_notes",))
        
        st.markdown("### Transaction Invoicing")
        m1, m2 = st.columns(2)
        m1.metric("Procedure Unit Cost", f"${unit_price:,.2f}")
        m2.metric("Total Calculated Due", f"${gross_cost:,.2f}")
        
        st.markdown("#### Processing Settlement Payment")
        f1, f2 = st.columns(2)
        f1.number_input("Amount Paid Right Now ($)", min_value=0.0, max_value=max(gross_cost, 100000.0), step=10.0, key="session_amount_paid")
        f2.selectbox("Payment Method Type", options=PAYMENT_METHODS, key="session_payment_method")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("💾 Commit Treatment Session & Payment", on_click=cb_save_session_log, type="primary")

    with r_box:
        st.subheader("Interactive Anatomical Grid (16-Teeth Rows)")
        st.caption("Map target teeth directly. Patient's upper/lower teeth are aligned horizontally.")
        
        st.markdown("<div class='jaw-title'>Upper Maxillary Jaw Arch</div>", unsafe_allow_html=True)
        upper_row = u_quad1 + u_quad2
        cols_u = st.columns(16)
        for idx, t in enumerate(upper_row):
            lbl = f"🟢\n{t}" if t in active_teeth else f"⬜\n{t}"
            cols_u[idx].button(lbl, key=f"btn_u_{t}", on_click=cb_toggle_grid_tooth, args=(t,))
            
        st.markdown("<div class='jaw-title'>Lower Mandibular Jaw Arch</div>", unsafe_allow_html=True)
        lower_row = l_quad1 + l_quad2
        cols_l = st.columns(16)
        for idx, t in enumerate(lower_row):
            lbl = f"🟢\n{t}" if t in active_teeth else f"⬜\n{t}"
            cols_l[idx].button(lbl, key=f"btn_l_{t}", on_click=cb_toggle_grid_tooth, args=(t,))

        if active_teeth:
            st.info(f"Target Teeth Selection: **{', '.join(sorted(active_teeth))}**")

# ------------------------------------------------------------------------------
# PAGE 2: LOOKUP PATIENT HISTORY SECTION (NEW!)
# ------------------------------------------------------------------------------
elif page == "🔍 Patient History Lookup":
    st.subheader("🔍 Centralized Patient History Section")
    
    # 1. Dropdown to choose patient name
    lookup_pid = st.selectbox("Select Patient to Generate Complete Clinical File", 
                              options=list(patient_selectors.keys()), 
                              format_func=lambda x: patient_selectors[x])
    
    p_profile = st.session_state["patients_registry"][lookup_pid]
    
    # Render Patient Profile Summary Card
    st.markdown("### 📋 Basic Profile Data")
    k1, k2, k3, k4 = st.columns(4)
    k1.write(f"**Full Name:** {p_profile['name']}")
    k2.write(f"**Phone Line:** {p_profile['phone']}")
    k3.write(f"**Age:** {p_profile['age']} years old")
    k4.write(f"**Registered Clinic Center:** {p_profile['center']}")
    
    st.markdown("---")
    
    # Split lookup view into structural tabs (Treatment Record Ledger vs. Isolated Tooth Check)
    hist_tab1, hist_tab2 = st.tabs(["📊 Consolidated Billing & Treatment History", "🦷 Tooth-by-Tooth Isolation History"])
    
    with hist_tab1:
        st.markdown("### 💳 Patient Financial Balance Summary")
        p_tx_history = st.session_state["finance_ledger"].get(lookup_pid, [])
        
        if p_tx_history:
            df_fin = pd.DataFrame(p_tx_history)
            tot_inv = df_fin["total_due"].sum()
            tot_col = df_fin["amount_paid"].sum()
            tot_bal = df_fin["balance"].sum()
            
            f_col1, f_col2, f_col3 = st.columns(3)
            f_col1.metric("Total Billings Invoiced", f"${tot_inv:,.2f}")
            f_col2.metric("Total Received Collections", f"${tot_col:,.2f}")
            f_col3.metric("Current Balance Due", f"${tot_bal:,.2f}", delta=f"-${tot_bal:,.2f}" if tot_bal > 0 else "Account Clear", delta_color="inverse")
            
            st.markdown("#### Complete Historical Operational Records Log")
            df_display_fin = df_fin.copy()
            df_display_fin.columns = ["Tx Date", "Procedure / Target Summary", "Gross Charged ($)", "Amount Paid ($)", "Method", "Remaining Debt ($)"]
            st.dataframe(df_display_fin.style.format({
                "Gross Charged ($)": "${:,.2f}", "Amount Paid ($)": "${:,.2f}", "Remaining Debt ($)": "${:,.2f}"
            }), use_container_width=True, hide_index=True)
        else:
            st.info("No invoice transactions or financial payment actions found for this patient.")

    with hist_tab2:
        st.markdown("### 🔍 Filter Individual Tooth History Logs")
        selected_tooth = st.selectbox("Select Target Tooth Number to Isolate Timeline Logs", options=all_teeth_options)
        
        tooth_history_records = st.session_state["tooth_history_ledger"].get(lookup_pid, {}).get(selected_tooth, [])
        if tooth_history_records:
            df_tooth = pd.DataFrame(tooth_history_records)[["date", "treatment", "center", "notes"]]
            df_tooth.columns = ["Treatment Date", "Procedure Implemented", "Clinic Center", "Clinical Notes"]
            st.table(df_tooth)
        else:
            st.warning(f"No clinical procedure entries or treatment records recorded on Tooth {selected_tooth} for this patient.")

# ------------------------------------------------------------------------------
# PAGE 3: PATIENT REGISTRATION MANAGER
# ------------------------------------------------------------------------------
elif page == "👥 Patient Registration Manager":
    col_adm_1, col_adm_2 = st.columns([1, 2])
    with col_adm_1:
        st.info("#### ➕ New Patient Registration")
        st.text_input("Full Patient Name", key="new_pat_name")
        st.text_input("Mobile Contact Phone", key="new_pat_phone")
        st.date_input("Date of Birth", key="new_pat_birth")
        st.selectbox("Assigned Medical Facility", options=CENTERS, key="new_pat_center")
        st.button("🚀 Register Patient File", on_click=cb_add_new_patient, use_container_width=True)
    
    with col_adm_2:
        st.write("#### 📋 Currently Registered Patients Master List")
        raw_patients = []
        for pid, d in st.session_state["patients_registry"].items():
            raw_patients.append({"ID Code": pid, "Full Name": d["name"], "Contact Phone": d["phone"], "Age": d["age"], "Clinic Center": d["center"]})
        st.dataframe(pd.DataFrame(raw_patients), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# PAGE 4: ACCOUNTS & FINANCE CENTER
# ------------------------------------------------------------------------------
elif page == "💰 Accounts & Finance Center":
    st.subheader("💰 Global Invoicing Ledger Summary")
    
    all_txs = []
    for pid, tx_list in st.session_state["finance_ledger"].items():
        p_name = st.session_state["patients_registry"].get(pid, {}).get("name", "Unknown")
        for tx in tx_list:
            all_txs.append({
                "Date": tx["date"], "Patient ID": pid, "Patient Name": p_name,
                "Procedure": tx["procedure"], "Charged": tx["total_due"],
                "Paid": tx["amount_paid"], "Method": tx["method"], "Balance": tx["balance"]
            })
            
    if all_txs:
        df_global = pd.DataFrame(all_txs)
        st.metric("Total Clinical Clinic Income (All Time)", f"${df_global['Paid'].sum():,.2f}")
        st.markdown("#### Master Historical Financial Stream")
        st.dataframe(df_global.style.format({"Charged": "${:,.2f}", "Paid": "${:,.2f}", "Balance": "${:,.2f}"}), use_container_width=True, hide_index=True)
    else:
        st.info("The central accounting ledger ledger has no past transactions on record.")

# ------------------------------------------------------------------------------
# PAGE 5: FEE CATALOG DATABASE
# ------------------------------------------------------------------------------
elif page == "📋 Fee Catalog Database":
    p_ed_col1, p_ed_col2 = st.columns([1, 2])
    
    edit_cat = st.session_state.get("edit_cat_select", "Adult Dentistry")
    edit_procedures = list(st.session_state["treatment_catalog_db"].get(edit_cat, {}).keys())
    
    if st.session_state["edit_treat_select"] not in edit_procedures and edit_procedures:
        st.session_state["edit_treat_select"] = edit_procedures[0]

    with p_ed_col1:
        st.info("#### ✏️ Tariff Price Customization Panel")
        st.selectbox("Select Core Domain Category", options=list(st.session_state["treatment_catalog_db"].keys()), key="edit_cat_select")
        st.selectbox("Select Target Procedure", options=edit_procedures, key="edit_treat_select")
        st.number_input("Modify Fee Schedule Base Rate ($)", step=10.0, key="edit_price_val")
        st.button("💾 Apply Updated Price", on_click=cb_update_treatment_price, use_container_width=True, type="primary")
        
    with p_ed_col2:
        st.write("#### 📋 Current Treatment Pricing Catalog Database View")
        flat_records = []
        for category, item_map in st.session_state["treatment_catalog_db"].items():
            for item, rate in item_map.items():
                flat_records.append({"Category": category, "Procedure Name": item, "Configured Fee Rate": f"${rate:,.2f}"})
        st.dataframe(pd.DataFrame(flat_records), use_container_width=True, hide_index=True)
