# app.py
import streamlit as st
import pandas as pd
import csv
from io import StringIO

# --- Configuration ---
DATA_FILE = "Gantt Chart - KLIA (26 Mar 2025)(Project schedule).csv"
APP_TITLE = "WBS Progress Tracker - KLIA District Cooling System"

# --- Helper Functions ---

def parse_csv_to_wbs(csv_content):
    """Parses the specific CSV structure into a WBS list."""
    wbs = []
    current_parent = None
    parent_index = -1

    # Use StringIO to treat the string content like a file
    f = StringIO(csv_content)
    reader = csv.reader(f)

    try:
        # Skip header rows until we find the task data structure
        for _ in range(7): # Skip first 7 rows based on observed format
             next(reader)

        row_num = 8 # Start counting after skipped rows
        for row in reader:
            row_num += 1
            if not any(field.strip() for field in row):
                continue # Skip fully blank rows

            task_name = row[1].strip() if len(row) > 1 else ""
            task_id_indicator = row[0].strip() if len(row) > 0 else ""

            # Identify Parent Task (Phase row)
            if not task_id_indicator and task_name.lower().startswith("phase"):
                parent_index += 1
                current_parent = {
                    "id": f"p_{parent_index}",
                    "name": task_name,
                    "level": 0,
                    "completed": False,
                    "expanded": True, # Start expanded
                    "children": []
                }
                wbs.append(current_parent)

            # Identify Child Task
            elif current_parent and task_name and not task_name.lower().startswith("phase"):
                 if not (not task_id_indicator and task_name.lower().startswith("phase")):
                    child_index = len(current_parent["children"])
                    child_task = {
                        "id": f"p_{parent_index}_c_{child_index}",
                        "name": task_name,
                        "level": 1,
                        "completed": False,
                    }
                    current_parent["children"].append(child_task)

    except StopIteration:
        st.warning("Reached end of CSV data while parsing.")
    except Exception as e:
        st.error(f"Error parsing CSV on row {row_num}: {e}")
        st.error(f"Problematic row data: {row}")
        return []

    sync_parent_completion(wbs)
    return wbs

def sync_parent_completion(wbs_data):
    """Ensure parent completion status reflects children's status."""
    for parent in wbs_data:
        if parent.get("children"):
            all_children_complete = all(c.get("completed", False) for c in parent["children"])
            parent["completed"] = all_children_complete
        else:
             pass

def calculate_progress(wbs_data):
    """Calculates overall progress based on completed child tasks."""
    total_children = 0
    completed_children = 0
    for parent in wbs_data:
        for child in parent.get("children", []):
            total_children += 1
            if child.get("completed", False):
                completed_children += 1
    return (completed_children / total_children) if total_children > 0 else 0

def initialize_state():
    """Initializes session state if not already done."""
    if "wbs_data" not in st.session_state:
        st.session_state.wbs_data = []
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                csv_content = f.read()
            st.session_state.wbs_data = parse_csv_to_wbs(csv_content)
            if not st.session_state.wbs_data:
                 st.error(f"Could not load or parse data from {DATA_FILE}. Please check the file format.")

        except FileNotFoundError:
            st.error(f"Error: {DATA_FILE} not found. Please make sure it's in the same directory as the app.")
        except Exception as e:
            st.error(f"An unexpected error occurred loading the data: {e}")

    if "show_add_task_form" not in st.session_state:
        st.session_state.show_add_task_form = False

# --- Main App Logic ---
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# Initialize state (loads data on first run)
initialize_state()

if not isinstance(st.session_state.get("wbs_data"), list):
    st.error("WBS data is not loaded correctly. Cannot proceed.")
    st.stop()

# --- Progress Overview ---
if st.session_state.wbs_data:
    progress_value = calculate_progress(st.session_state.wbs_data)
    st.progress(progress_value)
    st.metric("Overall Progress", f"{progress_value:.1%}")
else:
    st.info("No WBS data loaded to display progress.")

st.markdown("---")

# --- Add Task Section ---
if st.button("➕ Add New Task"):
    st.session_state.show_add_task_form = not st.session_state.show_add_task_form

if st.session_state.show_add_task_form:
    with st.form("add_task_form"):
        st.subheader("Add New Task")
        new_task_name = st.text_input("Task Name", key="new_task_name_input")
        new_task_type = st.radio("Task Type", ["Parent (Phase)", "Child"], key="new_task_type_radio")

        parent_options = {p["id"]: p["name"] for p in st.session_state.wbs_data} # Use ID as key
        selected_parent_id = None
        if new_task_type == "Child":
            if not parent_options:
                 st.warning("Cannot add a child task as no parent tasks exist yet.")
                 target_parent_display = ""
            else:
                # Ensure parent_options keys are used consistently
                selected_parent_id = st.selectbox(
                    "Add Child To Parent:",
                    options=list(parent_options.keys()),
                    format_func=lambda x: parent_options[x],
                    key="target_parent_select"
                )

        if new_task_type == "Parent":
            st.info("New Parent tasks will be added at the end of the list.")
        elif new_task_type == "Child" and selected_parent_id:
             st.info(f"New Child task will be added at the end of '{parent_options[selected_parent_id]}'.")


        submitted = st.form_submit_button("Add Task")

        if submitted:
            if not new_task_name:
                st.warning("Please enter a task name.")
            else:
                if new_task_type == "Parent":
                    parent_index = len(st.session_state.wbs_data)
                    new_parent = {
                        "id": f"p_{parent_index}", # Ensure new ID logic is consistent
                        "name": new_task_name,
                        "level": 0,
                        "completed": False,
                        "expanded": True,
                        "children": []
                    }
                    st.session_state.wbs_data.append(new_parent)
                    st.success(f"Added Parent: {new_task_name}")
                    st.session_state.show_add_task_form = False
                    st.rerun() # USE st.rerun()

                elif new_task_type == "Child":
                    if selected_parent_id:
                        parent_found = False
                        # Find parent using the selected ID
                        for i, p in enumerate(st.session_state.wbs_data):
                             if p["id"] == selected_parent_id:
                                parent_internal_index = i # Keep track of list index
                                child_index = len(p["children"])
                                new_child = {
                                    # Use the parent's actual list index for child ID generation
                                    "id": f"{p['id']}_c_{child_index}",
                                    "name": new_task_name,
                                    "level": 1,
                                    "completed": False,
                                }
                                # Modify the list directly using the found index
                                st.session_state.wbs_data[parent_internal_index]["children"].append(new_child)
                                st.session_state.wbs_data[parent_internal_index]["completed"] = False
                                st.success(f"Added Child '{new_task_name}' to Parent '{p['name']}'")
                                parent_found = True
                                break
                        if not parent_found:
                             st.error("Selected parent ID not found. Cannot add child.") # Error if ID mismatch

                        st.session_state.show_add_task_form = False
                        st.rerun() # USE st.rerun()
                    else:
                        st.warning("Please select a Parent to add the Child task to.")


    st.markdown("---")

# --- WBS Display and Interaction ---
if not st.session_state.wbs_data:
    st.info("Upload or parse a CSV file to see the WBS.")
else:
    # No need for wbs_changed flag if we use st.rerun() immediately on change
    current_wbs = st.session_state.wbs_data

    for parent_idx, parent_task in enumerate(current_wbs):
        parent_id = parent_task['id']
        parent_key_base = f"task_{parent_id}"

        # Retrieve expanded state from session state, default to True if not found
        is_expanded = st.session_state.get(f"{parent_key_base}_expanded", parent_task.get("expanded", True))

        # Use a callback to store the expander state
        def expander_changed(key, value):
            st.session_state[key] = value

        # Note: Streamlit expander doesn't have a direct on_change for expand/collapse state easily accessible without complex workarounds.
        # We will manage state more manually. Let's assume we want to store the *last known* state.
        # A simpler approach: Store state only when *interacting* with checkboxes inside.

        with st.expander(f"{parent_task['name']}", expanded=is_expanded):
             # When it's rendered expanded, ensure the state reflects this
             st.session_state[f"{parent_key_base}_expanded"] = True

             # --- Parent Checkbox ---
             parent_completed_value = parent_task.get("completed", False)
             parent_completed_interaction = st.checkbox(
                 f"Complete Phase",
                 value=parent_completed_value,
                 key=f"{parent_key_base}_cb",
                 help=f"Mark '{parent_task['name']}' and all sub-tasks as complete."
             )

             if parent_completed_interaction != parent_completed_value:
                 parent_task["completed"] = parent_completed_interaction
                 for child_task in parent_task.get("children", []):
                     child_task["completed"] = parent_completed_interaction
                 # Store expanded state on interaction
                 st.session_state[f"{parent_key_base}_expanded"] = True
                 st.rerun() # USE st.rerun()

             # --- Child Task Checkboxes ---
             st.markdown("---")
             children_changed_in_loop = False
             all_children_now_complete_in_loop = True if parent_task.get("children") else False

             for child_idx, child_task in enumerate(parent_task.get("children", [])):
                 child_id = child_task['id']
                 child_key = f"task_{child_id}_cb"
                 child_completed_value = child_task.get("completed", False)

                 child_completed_interaction = st.checkbox(
                     child_task['name'],
                     value=child_completed_value,
                     key=child_key
                 )

                 if child_completed_interaction != child_completed_value:
                     child_task["completed"] = child_completed_interaction
                     children_changed_in_loop = True

                 if not child_task["completed"]:
                     all_children_now_complete_in_loop = False

             # --- Sync Parent state based on Children AFTER looping through all children ---
             if children_changed_in_loop:
                 new_parent_state = all_children_now_complete_in_loop
                 if parent_task.get("completed") != new_parent_state:
                     parent_task["completed"] = new_parent_state
                 # Store expanded state on interaction
                 st.session_state[f"{parent_key_base}_expanded"] = True
                 st.rerun() # USE st.rerun() - Rerun if any child change occurred

        # Heuristic to try and capture collapsed state: If the key exists but wasn't set to True during render, assume it was collapsed.
        # This is imperfect. A better way might involve JS hacks or structuring differently.
        # Let's remove this complexity for now and let expanders reopen if state isn't actively managed on collapse.
        # if f"{parent_key_base}_expanded" in st.session_state and not st.session_state[f"{parent_key_base}_expanded"]:
        #     # If state exists and wasn't marked True this run, it must have been collapsed by user
        #      parent_task["expanded"] = False
        # else:
        #      # Otherwise assume expanded or keep previous state if available
        #      parent_task["expanded"] = True
        # # Reset the transient flag for the next run
        # if f"{parent_key_base}_expanded" in st.session_state:
        #      st.session_state[f"{parent_key_base}_expanded"] = parent_task["expanded"]


    # Persist potentially modified WBS data back (though direct dict modification often updates session_state)
    # st.session_state.wbs_data = current_wbs # Redundant if modifying dicts within list directly


# --- Display Raw Data (Optional Debugging) ---
# with st.expander("Show Raw WBS Data"):
#    st.json(st.session_state.wbs_data)