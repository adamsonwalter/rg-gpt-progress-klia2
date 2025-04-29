import streamlit as st
import csv
from io import StringIO

# --- Configuration ---
APP_TITLE = "WBS Progress Tracker - KLIA District Cooling System"

# --- Helper Functions ---

def parse_csv_to_wbs(csv_content):
    """Parses the specific CSV structure into a WBS list."""
    wbs = []
    current_parent = None
    parent_index = -1

    f = StringIO(csv_content)
    reader = csv.reader(f)

    try:
        for _ in range(7):
            next(reader)
        for row in reader:
            if not any(field.strip() for field in row):
                continue
            task_name = row[1].strip() if len(row) > 1 else ""
            task_id_indicator = row[0].strip() if len(row) > 0 else ""
            if not task_id_indicator and task_name.lower().startswith("phase"):
                parent_index += 1
                current_parent = {
                    "id": f"p_{parent_index}",
                    "name": task_name,
                    "completed": False,
                    "expanded": True,
                    "children": []
                }
                wbs.append(current_parent)
            elif current_parent and task_name and not task_name.lower().startswith("phase"):
                child_index = len(current_parent["children"])
                child_task = {
                    "id": f"p_{parent_index}_c_{child_index}",
                    "name": task_name,
                    "completed": False,
                }
                current_parent["children"].append(child_task)
    except Exception:
        st.error("Error parsing CSV. Please ensure it follows the expected format.")
        return []
    # Sync parent completion
    for parent in wbs:
        parent["completed"] = all(c["completed"] for c in parent.get("children", []))
    return wbs

# --- Main App Logic ---
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# Upload CSV
if "wbs_data" not in st.session_state:
    st.session_state.wbs_data = None

if st.session_state.wbs_data is None:
    uploaded_file = st.file_uploader(
        "Upload WBS CSV file (no Gantt data needed)", type=["csv"]
    )
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8")
        st.session_state.wbs_data = parse_csv_to_wbs(content)
    else:
        st.info("Please upload a CSV file to initialize the WBS.")
        st.stop()

wbs_data = st.session_state.wbs_data

# --- Progress Overview ---
if wbs_data:
    total = sum(len(p["children"]) for p in wbs_data)
    done = sum(
        child["completed"]
        for parent in wbs_data
        for child in parent.get("children", [])
    )
    progress = done / total if total else 0
    st.progress(progress)
    st.metric("Overall Progress", f"{progress:.1%}")
else:
    st.warning("No tasks loaded.")

st.markdown("---")

# --- Add Task Button ---
if st.button("➕ Add New Task"):
    st.session_state.show_add_task_form = True

# --- Add Task Form ---
if st.session_state.get("show_add_task_form", False):
    with st.form("add_task_form"):
        st.subheader("Add New Task")
        name = st.text_input("Task Name")
        typ = st.radio("Task Type", ["Parent", "Child"])
        parent_map = {p["id"]: p["name"] for p in wbs_data}
        parent_sel = None
        if typ == "Child":
            parent_sel = st.selectbox(
                "Select Parent", list(parent_map.keys()),
                format_func=lambda x: parent_map[x]
            )
        submitted = st.form_submit_button("Add")
        if submitted:
            if not name:
                st.warning("Enter a name.")
            else:
                if typ == "Parent":
                    idx = len(wbs_data)
                    wbs_data.append({
                        "id": f"p_{idx}",
                        "name": name,
                        "completed": False,
                        "expanded": True,
                        "children": []
                    })
                else:
                    for p in wbs_data:
                        if p["id"] == parent_sel:
                            ci = len(p["children"])
                            p["children"].append({
                                "id": f"{parent_sel}_c_{ci}",
                                "name": name,
                                "completed": False
                            })
                            p["completed"] = False
                            break
                st.session_state.show_add_task_form = False
                st.experimental_rerun()
    st.markdown("---")

# --- Display WBS ---
for parent in wbs_data:
    exp = st.session_state.get(f"exp_{parent['id']}", parent["expanded"])
    with st.expander(parent["name"], expanded=exp):
        st.session_state[f"exp_{parent['id']}"] = True
        # Parent checkbox
        parent_cb = st.checkbox(
            f"{parent['name']}",
            value=parent["completed"],
            key=f"cb_{parent['id']}",
            help="Check to mark phase and all children complete"
        )
        if parent_cb != parent["completed"]:
            parent["completed"] = parent_cb
            for ch in parent.get("children", []):
                ch["completed"] = parent_cb
            st.experimental_rerun()
        # Children
        all_done = True
        for ch in parent.get("children", []):
            chk = st.checkbox(
                ch["name"],
                value=ch["completed"],
                key=f"cb_{ch['id']}"
            )
            if chk != ch["completed"]:
                ch["completed"] = chk
                all_done = all(c["completed"] for c in parent.get("children", []))
                parent["completed"] = all_done
                st.experimental_rerun()
            if not ch["completed"]:
                all_done = False