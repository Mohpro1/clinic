import json
import os
from datetime import datetime, date
import pandas as pd
import streamlit as st

# ==============================================================================
# RULE 1: DATA PERSISTENCE & CENTRAL STORAGE
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
        st.error(f"Database Save Error: {e}")

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
# SEED DATA & PRICE CATALOG CONFIGURATIONS
# ==============================================================================
# Requested medical centers
CENTERS = ["Istanbul Tower", "Elsifa Medical Center"]

# Comprehensive Pediatric & Adult Treatment Price Catalog
TREATMENT_CATALOG = {
    "Children Dentistry": {
        "Fluoride Application": 150.0,
        "Fissure Sealant": 200.0,
        "Pediatric Extraction": 250.0,
        "Pulpotomy (Baby Tooth Root Canal)": 450.0,
        "Stainless Steel Crown": 600.0
    },
    "Adult Dentistry": {
        "Composite Filling": 300.0,
        "Root Canal Treatment (RCT)": 800.0,
        "Porcelain Crown": 1200.0,
        "Deep Scaling & Polishing": 350.0,
        "Surgical Tooth Extraction": 700.0,
        "Dental Implant Placement": 3500.0
    }
}

# Seed default mock data if not existing in database
get_state_val("patients_registry", {
    "P0001": {"name": "Yusuf Demir", "phone": "+90 532 123 4567", "center": "Istanbul Tower"},
    "P0002": {"name": "Amina El-Amin", "phone": "+90 555 987 6543", "center": "Elsifa Medical Center"}
})

# Complete tooth history records matrix: { patient_code: { tooth_number: [list of historical actions] } }
get_state_val("tooth_history_ledger", {
    "P0001": {
        "16": [{"date": "2026-02-15", "treatment": "Composite Filling", "center": "Istanbul Tower", "notes": "Mesial cavity filled."}],
        "11": [{"date": "2026-04-10", "treatment": "Porcelain Crown", "center": "Istanbul Tower", "notes": "Permanent placement done."}]
    }
})

# Temporary tracking vectors for current session inputs
get_state_val("session_patient_id", "P0001")
get_state_val("session_category", "Adult Dentistry")
get_state_val("session_treatment", "Composite Filling")
get_state_val("session_selected_teeth", [])
get_state_val("session_notes", "")

# ==============================================================================
# RULE 4: CLEAN STATE CALLBACKS (Business Logic Synchronization)
# ==============================================================================
def cb_on_treatment_category_change():
    """Sets the default treatment option safely when swapping categories."""
    sync_input_to_db("session_category")
    category = st.session_state.get("session_category")
    available_treatments = list(TREATMENT_CATALOG[category].keys())
    st.session_state["session_treatment"] = available_treatments[0]
    sync_input_to_db("session_treatment")

def cb_toggle_tooth_selection(tooth_str):
    """Adds or removes a target tooth number without UI layout disruption."""
    current_selection = list(st.session_state.get("session_selected_teeth", []))
    if tooth_str in current_selection:
        current_selection.remove(tooth_str)
    else:
        current_selection.append(tooth_str)
    st.session_state["session_selected_teeth"] = current_selection
    sync_input_to_db("session_selected_teeth")

def cb_commit_treatment_session():
    """Saves the completed clinical session log directly into the tooth history database."""
    pid = st.session_state.get("session_patient_id")
    category = st.session_state.get("session_category")
    treatment = st.session_state.get("session_treatment")
    selected_teeth = st.session_state.get("session_selected_teeth", [])
    notes = st.session_state.get("session_notes", "")
    
    patients = st.session_state.get("patients_registry", {})
    center = patients.get(pid, {}).get("center", "Unknown Center")
    
    if not selected_teeth:
        st.sidebar.error("Error: Please map out at least one specific target tooth via the diagram selection grid.")
        return

    history_ledger = st.session_state.get("tooth_history_ledger", {})
    if pid not in history_ledger:
        history_ledger[pid] = {}
        
    session_date_str = date.today().isoformat()
    
    # Append localized records per selected tooth code
    for tooth in selected_teeth:
        if tooth not in history_ledger[pid]:
            history_ledger[pid][tooth] = []
        history_ledger[pid][tooth].append({
            "date": session_date_str,
            "treatment": f"[{category}] {treatment}",
            "center": center,
            "notes": notes
        })
        
    st.session_state["tooth_history_ledger"] = history_ledger
    sync_input_to_db("tooth_history_ledger")
    
    # Reset tracking arrays for safe reuse
    st.session_state["session_selected_teeth"] = []
    st.session_state["session_notes"] = ""
    sync_input_to_db("session_selected_teeth")
    sync_input_to_db("session_notes")
    st.sidebar.success("Clinical Session saved to history successfully!")

# ==============================================================================
# RULE 2: COMPUTATION VS UI (Pre-compute statistics before rendering layout)
# ==============================================================================
patients_data = st.session_state.get("patients_registry", {})
history_data = st.session_state.get("tooth_history_ledger", {})

current_patient_id = st.session_state.get("session_patient_id")
selected_category = st.session_state.get("session_category")
selected_treatment = st.session_state.get("session_treatment")
active_teeth_selected = st.session_state.get("session_selected_teeth", [])

# Look up exact rate from the nested dictionary structure
treatment_unit_price = TREATMENT_CATALOG[selected_category].get(selected_treatment, 0.0)
multi_tooth_count = len(active_teeth_selected) if len(active_teeth_selected) > 0 else 1
calculated_total_cost = treatment_unit_price * multi_tooth_count

# Setup structured patient profiles dictionary list for visualization rendering
patient_options = {pid: f"{info['name']} ({pid}) — {info['center']}" for pid, info in patients_data.items()}

# ==============================================================================
# RULE 3: MOBILE-FRIENDLY HTML/PDF PRINT REPORT ENGINE
# ==============================================================================
def build_patient_dental_passport_html(patient_name, p_id, center, complete_history_dict):
    """Creates a comprehensive, high-contrast, clean dental passport output."""
    history_rows = ""
    if p_id in complete_history_dict and complete_history_dict[p_id]:
        for tooth, logs in complete_history_dict[p_id].items():
            for entry in logs:
                history_rows += f"""
                <tr>
                    <td class="tooth-badge">Tooth {tooth}</td>
                    <td>{entry['date']}</td>
                    <td>{entry['treatment']}</td>
                    <td>{entry['center']}</td>
                    <td>{entry['notes']}</td>
                </tr>
                """
    else:
        history_rows = "<tr><td colspan='5' style='text-align:center; color:#999;'>No history entries registered for this profile.</td></tr>"

    html_markup = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dental Chart History - {patient_name}</title>
        <style>
            body {{ font-family: system-ui, -apple-system, sans-serif; margin: 25px; color: #333; line-height: 1.5; }}
            .header-banner {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #10b981; padding-bottom: 15px; margin-bottom: 25px; }}
            h2 {{ margin: 0; color: #111; }}
            .print-action-btn {{ background-color: #10b981; color: white; border: none; padding: 10px 20px; font-weight: bold; border-radius: 6px; cursor: pointer; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
            th {{ background-color: #f9fafb; font-weight: 600; }}
            .tooth-badge {{ font-weight: bold; color: #059669; }}
            @media print {{ .print-action-btn {{ display: none !important; }} body {{ margin: 0; }} }}
        </style>
    </head>
    <body>
        <div class="header-banner">
            <div>
                <h2>Comprehensive Dental History Passport</h2>
                <p style="margin: 4px 0 0 0; color: #666;">Patient: <strong>{patient_name}</strong> ({p_id}) | Location Base: {center}</p>
            </div>
            <button class="print-action-btn" onclick="window.print()">Print / Save PDF</button>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Tooth Code</th>
                    <th>Treatment Date</th>
                    <th>Cure Plan Implemented</th>
                    <th>Clinic Center</th>
                    <th>Clinical Observations / Notes</th>
                </tr>
            </thead>
            <tbody>
                {history_rows}
            </tbody>
        </table>
    </body>
    </html>
    """
    return html_markup

active_patient_meta = patients_data.get(current_patient_id, {"name": "Unknown", "center": "None"})
passport_html_payload = build_patient_dental_passport_html(
    patient_name=active_patient_meta["name"],
    p_id=current_patient_id,
    center=active_patient_meta["center"],
    complete_history_dict=history_data
)

# ==============================================================================
# UI RENDERING ZONE (Pure presentation layout)
# ==============================================================================
st.set_page_config(page_title="Havence Dental Workspace", layout="wide")
st.title("🦷 Havence Clinical Dental Engine")

tab_session_desk, tab_patient_records, tab_price_catalog = st.tabs([
    "🩺 Active Treatment Session Desk", 
    "🗂️ Patient Clinical History Matrix", 
    "💰 Fee & Treatment Price Database"
])

# ------------------------------------------------------------------------------
# TAB 1: ACTIVE TREATMENT SESSION DESK
# ------------------------------------------------------------------------------
with tab_session_desk:
    st.subheader("Live Operational Charting Desk")
    
    layout_col_left, layout_col_right = st.columns([1, 1])
    
    with layout_col_left:
        st.markdown("### 1. Patient Profile & Center Selection")
        st.selectbox("Select Patient Profile Instance", options=list(patient_options.keys()), format_func=lambda x: patient_options[x], key="session_patient_id", on_change=sync_input_to_db, args=("session_patient_id",))
        
        st.markdown("### 2. Treatment Strategy Mapping")
        st.selectbox("Clinical Age Target Classification", options=list(TREATMENT_CATALOG.keys()), key="session_category", on_change=cb_on_treatment_category_change)
        
        selectable_treatments_list = list(TREATMENT_CATALOG[st.session_state.get("session_category")].keys())
        st.selectbox("Specific Cure Treatment", options=selectable_treatments_list, key="session_treatment", on_change=sync_input_to_db, args=("session_treatment",))
        
        st.text_area("Clinical Session Operations Notes", key="session_notes", on_change=sync_input_to_db, args=("session_notes",))

    with layout_col_right:
        st.markdown("### 3. Interactive Graphical Odontogram Chart")
        st.caption("Click on any tooth number to select it for this treatment plan. Click again to remove it from the list.")
        
        # Maxillary Upper Arch dental rows layout maps
        st.markdown("**Upper Jaw (Maxillary Arch)**")
        row_upper_1 = ["18", "17", "16", "15", "14", "13", "12", "11"]
        row_upper_2 = ["21", "22", "23", "24", "25", "26", "27", "28"]
        
        cols_u1 = st.columns(8)
        for i, tooth in enumerate(row_upper_1):
            is_active = tooth in active_teeth_selected
            label = f"🦷\n{tooth}" if not is_active else f"🟢\n{tooth}"
            cols_u1[i].button(label, key=f"btn_u1_{tooth}", on_click=cb_toggle_tooth_selection, args=(tooth,), use_container_width=True)
            
        cols_u2 = st.columns(8)
        for i, tooth in enumerate(row_upper_2):
            is_active = tooth in active_teeth_selected
            label = f"🦷\n{tooth}" if not is_active else f"🟢\n{tooth}"
            cols_u2[i].button(label, key=f"btn_u2_{tooth}", on_click=cb_toggle_tooth_selection, args=(tooth,), use_container_width=True)
            
        st.markdown("---")
        
        # Mandibular Lower Arch rows layout maps
        st.markdown("**Lower Jaw (Mandibular Arch)**")
        row_lower_1 = ["48", "47", "46", "45", "44", "43", "42", "41"]
        row_lower_2 = ["31", "32", "33", "34", "35", "36", "37", "38"]
        
        cols_l1 = st.columns(8)
        for i, tooth in enumerate(row_lower_1):
            is_active = tooth in active_teeth_selected
            label = f"🦷\n{tooth}" if not is_active else f"🟢\n{tooth}"
            cols_l1[i].button(label, key=f"btn_l1_{tooth}", on_click=cb_toggle_tooth_selection, args=(tooth,), use_container_width=True)
            
        cols_l2 = st.columns(8)
        for i, tooth in enumerate(row_lower_2):
            is_active = tooth in active_teeth_selected
            label = f"🦷\n{tooth}" if not is_active else f"🟢\n{tooth}"
            cols_l2[i].button(label, key=f"btn_l2_{tooth}", on_click=cb_toggle_tooth_selection, args=(tooth,), use_container_width=True)

        st.markdown("---")
        
        # Live Session Cost Summary calculations box display zone
        st.markdown("### 4. Billing Allocation Matrix")
        f1, f2, f3 = st.columns(3)
        f1.metric("Unit Base Cost", f"${treatment_unit_price:,.2f}")
        f2.metric("Teeth Target Units", f"{len(active_teeth_selected)} Units Specified")
        f3.metric("Calculated Total Fee", f"${calculated_total_cost:,.2f}")
        
        st.button("🚀 Commit Session Plan to Patient File", on_click=cb_commit_treatment_session, use_container_width=True, type="primary")

# ------------------------------------------------------------------------------
# TAB 2: PATIENT CLINICAL HISTORY MATRIX
# ------------------------------------------------------------------------------
with tab_patient_records:
    st.subheader("Patient Record Files & Individual Tooth Logs")
    
    hist_col_left, hist_col_right = st.columns([1, 2])
    
    with hist_col_left:
        st.write("#### Select Target Profile")
        target_hist_pid = st.selectbox("Inspect Patient File", options=list(patient_options.keys()), format_func=lambda x: patient_options[x], key="history_view_pid")
        
        p_name = patients_data[target_hist_pid]["name"]
        p_center = patients_data[target_hist_pid]["center"]
        
        st.info(f"**Patient Name:** {p_name}\n\n**Assigned Facility Base:** {p_center}")
        
        # Mobile report delivery portal layout setup
        st.download_button(
            label="📱 Download Clean Mobile Patient Passport",
            data=passport_html_payload,
            file_name=f"dental_passport_{target_hist_pid}.html",
            mime="text/html",
            use_container_width=True
        )

    with hist_col_right:
        st.write("#### 🦷 Clinical Tooth History Breakdown Lookup")
        st.caption("Select any individual tooth below to view the history and treatments performed on it by date.")
        
        all_teeth_numbers = [str(x) for x in sorted([int(t) for row in [row_upper_1, row_upper_2, row_lower_1, row_lower_2] for t in row])]
        
        # Interactive tooth history inspection buttons array
        history_target_tooth = st.selectbox("Choose a tooth to check its history:", options=all_teeth_numbers, index=7)
        
        patient_tooth_logs = history_data.get(target_hist_pid, {}).get(history_target_tooth, [])
        
        st.markdown(f"##### Historical Logs for **Tooth {history_target_tooth}**")
        if patient_tooth_logs:
            df_logs = pd.DataFrame(patient_tooth_logs)
            # Reorder columns for optimal professional grid layout display format mapping
            df_logs = df_logs[["date", "treatment", "center", "notes"]]
            df_logs.columns = ["Date Checked", "Cure Plan Implemented", "Clinic Center Base Location", "Clinical Operations Notes"]
            st.table(df_logs)
        else:
            st.warning(f"No clinical operations or treatments recorded on Tooth {history_target_tooth} for this patient.")

# ------------------------------------------------------------------------------
# TAB 3: FEE & TREATMENT PRICE DATABASE
# ------------------------------------------------------------------------------
with tab_price_catalog:
    st.subheader("Master Dentistry Treatment Catalog & Pricing Matrix")
    
    cat_col1, cat_col2 = st.columns(2)
    
    with cat_col1:
        st.markdown("### 🍼 Children Dentistry Protocol Rates")
        child_records = [{"Treatment Specification": k, "Standard Rate Fee": f"${v:,.2f}"} for k, v in TREATMENT_CATALOG["Children Dentistry"].items()]
        st.table(pd.DataFrame(child_records))
        
    with cat_col2:
        st.markdown("### 🧑 Adult Dentistry Protocol Rates")
        adult_records = [{"Treatment Specification": k, "Standard Rate Fee": f"${v:,.2f}"} for k, v in TREATMENT_CATALOG["Adult Dentistry"].items()]
        st.table(pd.DataFrame(adult_records))
