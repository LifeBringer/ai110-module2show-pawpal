from __future__ import annotations

from pathlib import Path
import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

DATA_FILE = Path("data.json")


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #fff7fb 0%, #fff1f6 100%);
    }
    .panel {
        background: rgba(255,255,255,0.85);
        border: 1px solid #f2d7e6;
        border-radius: 18px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .task-chip {
        padding: 0.8rem 1rem;
        border-radius: 14px;
        border: 1px solid #efd5e3;
        background: white;
        margin-bottom: 0.6rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def default_owner() -> Owner:
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(Task(description="Morning walk", time="08:00", duration=20, priority="high"))
    owner.add_pet(pet)
    return owner


def load_owner() -> Owner:
    if DATA_FILE.exists():
        return Owner.load_from_json(DATA_FILE)
    return default_owner()


def persist() -> None:
    st.session_state.owner.save_to_json(DATA_FILE)


if "owner" not in st.session_state:
    st.session_state.owner = load_owner()

owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)

st.title("🐾 PawPal+")
st.caption("A pet-care planner with scheduling helpers, recurring tasks, and friendly conflict warnings.")

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Owner and pets")
    with st.container(border=True):
        owner.name = st.text_input("Owner name", value=owner.name)
        pet_names = [pet.name for pet in owner.pets] or ["Mochi"]
        selected_pet_name = st.selectbox("Choose a pet", ["All pets", *pet_names], index=1 if pet_names else 0)

        with st.expander("Add another pet"):
            new_pet_name = st.text_input("Pet name", key="new_pet_name")
            new_pet_species = st.selectbox("Species", ["dog", "cat", "other"], key="new_pet_species")
            new_pet_age = st.number_input("Age", min_value=0, max_value=40, value=1, key="new_pet_age")
            if st.button("Add pet"):
                if new_pet_name.strip():
                    owner.add_pet(Pet(name=new_pet_name.strip(), species=new_pet_species, age=int(new_pet_age)))
                    persist()
                    st.success(f"Added {new_pet_name.strip()} to your household.")
                else:
                    st.warning("Pet name is required.")

    st.subheader("Create a task")
    with st.container(border=True):
        task_pet_name = st.selectbox("Assign to pet", pet_names, key="task_pet")
        col_a, col_b = st.columns(2)
        with col_a:
            task_title = st.text_input("Task title", value="Morning walk")
            task_time = st.text_input("Time (HH:MM)", value="08:00")
            task_frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
        with col_b:
            task_duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            task_priority = st.selectbox("Priority", ["high", "medium", "low"])
            due_date = st.date_input("Due date (optional)", value=None)

        if st.button("Add task", use_container_width=True):
            target_pet = owner.find_pet(task_pet_name)
            if not task_title.strip():
                st.warning("Please add a task title.")
            elif target_pet is None:
                st.warning("Choose a pet before adding a task.")
            else:
                try:
                    task = Task(
                        description=task_title.strip(),
                        time=task_time.strip(),
                        duration=int(task_duration),
                        priority=task_priority,
                        frequency=task_frequency,
                        due_date=due_date.isoformat() if due_date else None,
                    )
                    target_pet.add_task(task)
                    persist()
                    st.success(f"Saved {task.description} for {target_pet.name}.")
                except ValueError:
                    st.error("Time must use the HH:MM format, for example 08:30.")

with right:
    st.subheader("Planner tools")
    with st.container(border=True):
        view_mode = st.radio("Sort tasks", ["By time", "By priority", "Weighted"], horizontal=True)
        only_open = st.checkbox("Show pending tasks only")
        slot_length = st.number_input("Find next free slot", min_value=5, max_value=180, value=30)

        if st.button("Run recurring task check", use_container_width=True):
            created = scheduler.handle_recurring_tasks()
            persist()
            if created:
                st.success(f"Created {len(created)} follow-up recurring task(s).")
            else:
                st.info("No completed recurring tasks needed a new occurrence yet.")

        suggested_slot = scheduler.find_next_available_slot(int(slot_length))
        if suggested_slot:
            st.info(f"Next available {slot_length}-minute slot: {suggested_slot}")
        else:
            st.warning("No free slot fits that duration in the default 06:00–22:00 window.")

        conflicts = scheduler.detect_conflicts()
        if conflicts:
            for warning in conflicts:
                st.warning(warning)
        else:
            st.success("No overlapping tasks detected.")

st.divider()

st.subheader("Schedule")
current_tasks = scheduler.filter_tasks(None if selected_pet_name == "All pets" else selected_pet_name, is_complete=False if only_open else None)
if view_mode == "By priority":
    display_tasks = scheduler.sort_by_priority(current_tasks)
elif view_mode == "Weighted":
    display_tasks = scheduler.weighted_sort(current_tasks)
else:
    display_tasks = scheduler.sort_by_time(current_tasks)

if display_tasks:
    for task in display_tasks:
        pet_name = next((pet.name for pet, pet_task in owner.all_tasks() if pet_task.task_id == task.task_id), "Unknown")
        badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "🐾")
        status = "Complete" if task.is_complete else "Pending"
        due_text = f" | due {task.due_date}" if task.due_date else ""
        st.markdown(
            f"<div class='task-chip'><strong>{badge} {task.description}</strong> — {task.time} for {task.duration} min | {task.priority.title()} | {task.frequency.title()} | {pet_name} | {status}{due_text}</div>",
            unsafe_allow_html=True,
        )
else:
    st.info("No tasks match the current filters.")

st.divider()

st.subheader("Daily schedule preview")
for task in scheduler.get_daily_schedule():
    st.write(f"• {task.time} — {task.description} ({task.priority})")

persist()
