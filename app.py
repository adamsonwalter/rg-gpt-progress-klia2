import streamlit as st
import csv
from io import StringIO

# --- Configuration ---
APP_TITLE = "WBS Progress Tracker - KLIA District Cooling System"

# --- Helper Functions ---
def parse_csv_to_wbs(csv_content):
    wbs = []
    current_parent = None
    parent_index = -1
    f = StringIO(csv_content)
    reader = csv.reader(f)
    # Skip potential header lines
    for _ in range(7):
        next(reader, None)
    for row in reader:
        if not any(field.strip() for field in row):
            continue
        task_name = row[1].strip() if len(row) > 1 else ""
        id_ind = row[0].strip() if len(row) > 0 else ""
        if not id_ind and task_name.lower().startswith("phase"):
            parent_index += 1
            current_parent = {
                "id": f"p_{parent_index}",
                "name": task_name,
                "completed": False,
                "expanded": True,
                "children": []
            }
            wbs.append(current_parent)
        elif current_parent and task_name:
            ci = len(current_parent["children"])
            current_parent["children"].append({
                "id": f"{current_parent['id']}_c_{ci}",
                "name": task_name,
                "completed": False
            })
    # Sync parent flags
    for p in wbs:
        p["completed"] = all(c["completed"] for c in p["children"])
    return wbs

# --- App Start ---
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# CSV uploader
if "wbs_data" not in st.session_state or st.session_state.wbs_data is None:
    up = st.file_uploader("Upload WBS CSV (phases + tasks)", type="csv")
    if up:
        txt = up.read().decode("utf-8")
        st.session_state.wbs_data = parse_csv_to_wbs(txt)
    else:
        st.info("Upload a CSV to load the WBS.")
        st.stop()

wbs = st.session_state.wbs_data

# Progress bar + metric
total = sum(len(p["children"]) for p in wbs)
completed = sum(c["completed"] for p in wbs for c in p["children"] )
prog = completed/total if total else 0
st.progress(prog)
st.metric("Overall Progress", f"{prog:.1%}")
st.markdown("---")

# Add-task toggle
show = st.session_state.get("show_add_task_form", False)
if st.button("➕ Add New Task"):
    st.session_state.show_add_task_form = not show
    show = not show

# Add-task form
if show:
    with st.form("add_form"):
        nm = st.text_input("Task Name")
        tp = st.radio("Type", ["Parent","Child"])
        pid = None
        if tp == "Child":
            pid = st.selectbox("Parent", [p["id"] for p in wbs], format_func=lambda x: next(p["name"] for p in wbs if p["id"]==x))
        go = st.form_submit_button("Add")
        if go and nm:
            if tp == "Parent":
                idx = len(wbs)
                wbs.append({"id":f"p_{idx}","name":nm,"completed":False,"expanded":True,"children":[]})
            else:
                par = next(p for p in wbs if p["id"]==pid)
                ci = len(par["children"])
                par["children"].append({"id":f"{pid}_c_{ci}","name":nm,"completed":False})
                par["completed"] = False
            st.session_state.show_add_task_form = False
    st.markdown("---")

# Display WBS
for p in wbs:
    exp = st.session_state.get(f"exp_{p['id']}", p["expanded"])
    with st.expander(p["name"], expanded=exp):
        st.session_state[f"exp_{p['id']}"] = True
        val = st.checkbox(p["name"], value=p["completed"], key=f"cb_{p['id']}")
        if val != p["completed"]:
            p["completed"] = val
            for c in p["children"]:
                c["completed"] = val
        # children
        for c in p["children"]:
            cv = st.checkbox(c["name"], value=c["completed"], key=f"cb_{c['id']}")
            if cv != c["completed"]:
                c["completed"] = cv
        # sync parent
        p["completed"] = all(c["completed"] for c in p["children"])