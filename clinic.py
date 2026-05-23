import json
import os
from datetime import datetime, date
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. DATA PERSISTENCE: STATE MIRROR & LOCAL JSON STORAGE
# ==============================================================================
DB_FILE = "app_data.json"

def json_serial(obj):
    """Handles parsing native Date and Time structures cleanly into JSON."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def load_db():
    """Reads raw JSON records from disk."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    """Commits dictionary data safely to persistent disk storage."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, default=json_serial, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Critical Database Save Error: {e}")

def get_state_val(key, default_value):
    """Initializes session state memory with deep local data mirroring fallback."""
    db_data = load_db()
    if key not in st.session_state:
        if key in db_data:
            val = db_data[key]
            # Auto-reconstitute strings back into clean datetime objects
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
    """Instant callback worker attached to inputs to bypass memory loss risks."""
    if key in st.session_state:
        db_data = load_db()
        db_data[key] = st.session_state[key]
        save_db(db_data)

# ==============================================================================
# 4. CLEAN STATE CALLBACKS (Business Logic Rules)
# ==============================================================================
def cb_patient_birthdate_change():
    """Calculates patient age strictly on state mutation to preserve performance."""
    sync_input_to_db("patient_birth_date")
    b_date = st.session_state.get("patient_birth_date")
    if isinstance(b_date, date):
        today = date.today()
        calculated_age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
        st.session_state["patient_age"] = max(0, calculated_age)
    else:
        st.session_state["patient_age"] = 0
    sync_input_to_db("patient_age")

def cb_calculate_session_shares():
    """Forces state sync and evaluates specific financial sharing splits."""
    sync_input_to_db("session_total_price")
    sync_input_to_db("session_amount_paid")
    sync_input_to_db("session_rate_percentage")
    
    total = st.session_state.get("session_total_price", 0.0)
    paid = st.session_state.get("session_amount_paid", 0.0)
    rate = st.session_state.get("session_rate_percentage", 0.0) / 100.0
    
    # Financial allocation rule matrices
    st.session_state["session_remaining"] = max(0.0, total - paid)
    st.session_state["session_center_share"] = paid * rate
    st.session_state["session_doctor_share"] = max(0.0, paid - st.session_state["session_center_share"])
    
    sync_input_to_db("session_remaining")
    sync_input_to_db("session_center_share")
    sync_input_to_db("session_doctor_share")

# ==============================================================================
# CORE APP SEEDING & RECORD INITIALIZATION
# ==============================================================================
# Global Patient Registry Cache setup (Emulating your core.py structure)
get_state_val("global_patient_list", [
    {"code": "P0001", "name": "John Doe", "phone": "555-0192", "center": "C01"},
    {"code": "P0002", "name": "Jane Smith", "phone": "555-4831", "center": "C02"}
])

# Interactive state form items
get_state_val("patient_name", "")
get_state_val("patient_phone", "")
get_state_val("patient_birth_date", date(1990, 1, 1))
get_state_val("patient_age", 36)
get_state_val("patient_center_code", "C01")

get_state_val("session_total_price", 1200.0)
get_state_val("session_amount_paid", 800.0)
get_state_val("session_rate_percentage", 30.0) # 30% Center Rate cut
get_state_val("session_remaining", 400.0)
get_state_val("session_doctor_share", 560.0)
get_state_val("session_center_share", 240.0)

# ==============================================================================
# 2. COMPUTATION VS UI: DATA MATRICES PRE-CALCULATION
# ==============================================================================
# Isolate calculation datasets from user tracking memory
patient_registry = st.session_state.get("global_patient_list", [])
df_patients = pd.DataFrame(patient_registry)

# Aggregate global data statistics before layout generation
total_patients_tracked = len(df_patients)
calc_rem_balance = st.session_state.get("session_remaining", 0.0)
calc_doc_cut = st.session_state.get("session_doctor_share", 0.0)
calc_ctr_cut = st.session_state.get("session_center_share", 0.0)

# ==============================================================================
# 3. MOBILE-FRIENDLY PDF/HTML REPORT GENERATION
# ==============================================================================
def create_print_invoice_html(title, patient, amount, doc, center, balance):
    """Assembles beautiful, inline print-button sheets safe for mobile phones."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 20px; color: #222; }}
            .card {{ border: 1px solid #eaeaea; padding: 20px; border-radius: 8px; max-width: 500px; margin: auto; }}
            .flex-row {{ display: flex; justify-content: space-between; border-bottom: 1px dashed #eee; padding: 10px 0; }}
            .btn-green {{ background-color: #2e7d32; color: #fff; width: 100%; border: none; padding: 12px; font-weight: bold; border-radius: 5px; margin-top: 15px; cursor: pointer; }}
            @media print {{ .btn-green {{ display: none !important; }} }}
        </style>
    </head>
    <body>
        <div class="card">
            <h3>🦷 {title}</h3>
            <div class="flex-row"><strong>Patient:</strong> <span>{patient}</span></div>
            <div class="flex-row"><strong>Amount Paid:</strong> <span>${amount:,.2f}</span></div>
            <div class="flex-row"><strong>Remaining Debt:</strong> <span style="color:red;">${balance:,.2f}</span></div>
            <div class="flex-row"><strong>Doctor Share Allocation:</strong> <span>${doc:,.2f}</span></div>
            <div class="flex-row"><strong>Center Operational Cut:</strong> <span>${center:,.2f}</span></div>
            <button class="btn-green" onclick="window.print()">Print / Export PDF Invoice</button>
        </div>
    </body>
    </html>
    """

invoice_html = create_print_invoice_html(
    title="Dental Treatment Session Summary",
    patient=st.session_state.get("patient_name", "Not Specified"),
    amount=st.session_state.get("session_amount_paid", 0.0),
    doc=calc_doc_cut,
    center=calc_ctr_cut,
    balance=calc_rem_balance
)

# ==============================================================================
# UI RENDERING ZONE (Pure presentation)
# ==============================================================================
st.set_page_config(page_title="Dental Manager Engine", layout="wide")
st.title("🦷 Dental Manager Engine")

tab_patients, tab_sessions, tab_financials = st.tabs([
    "👥 Patient Operations", 
    "🩺 Active Session Desk", 
    "📈 Revenue Allocations"
])

# --- TAB 1: PATIENTS ---
with tab_patients:
    st.subheader("Register / View Patients")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.text_input("Patient Full Name", key="patient_name", on_change=sync_input_to_db, args=("patient_name",))
        st.text_input("Contact Phone", key="patient_phone", on_change=sync_input_to_db, args=("patient_phone",))
    with c2:
        st.date_input("Date of Birth", key="patient_birth_date", on_change=cb_patient_birthdate_change)
        st.selectbox("Assigned Medical Center Code", ["C01", "C02", "C03"], key="patient_center_code", on_change=sync_input_to_db, args=("patient_center_code",))
    with c3:
        st.metric("Auto-Evaluated Age", f"{st.session_state.get('patient_age')} Years Old")
        st.metric("System Registered Records Count", f"{total_patients_tracked} Patients")

    st.markdown("---")
    st.subheader("Active Cached Patients Database Row View")
    st.dataframe(df_patients, use_container_width=True)

# --- TAB 2: SESSIONS ---
with tab_sessions:
    st.subheader("Financial Ledger Invoicing & Logging")
    
    sc1, sc2 = st.columns(2)
    with sc1:
        st.number_input("Treatment Total Assessment ($)", key="session_total_price", step=50.0, on_change=cb_calculate_session_shares)
        st.number_input("Advance Amount Paid Upfront ($)", key="session_amount_paid", step=50.0, on_change=cb_calculate_session_shares)
        st.slider("Center Sharing Split Fee (%)", min_value=0.0, max_value=100.0, step=5.0, key="session_rate_percentage", on_change=cb_calculate_session_shares)
        
    with sc2:
        st.info("### Operational Output Fractions")
        st.metric("Patient Balance Due", f"${calc_rem_balance:,.2f}")
        st.metric("Doctor Payroll Take-Home", f"${calc_doc_cut:,.2f}")
        st.metric("Center Allocation Cut", f"${calc_ctr_cut:,.2f}")

# --- TAB 3: FINANCIALS & MOBILE PDF ---
with tab_financials:
    st.subheader("Mobile-Optimized Revenue Printing Matrix")
    
    inf_c1, inf_c2 = st.columns([2, 1])
    with inf_c1:
        st.success("Your structural reports and invoices have been pre-rendered into high-fidelity web blueprints.")
        st.write("Clicking the file generation payload below bypasses traditional iOS or Android print sizing failures by offering a pure localized instance window.")
        
    with inf_c2:
        st.download_button(
            label="📱 Download Clean Mobile Invoice",
            data=invoice_html,
            file_name=f"invoice_{st.session_state.get('patient_name', 'patient').lower().replace(' ', '_')}.html",
            mime="text/html",
            use_container_width=True
        )