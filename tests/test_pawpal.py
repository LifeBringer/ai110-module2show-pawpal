from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def make_scheduler() -> tuple[Owner, Pet, Scheduler]:
    pet = Pet(name="Buddy", species="dog", age=4)
    owner = Owner(name="Avery", pets=[pet])
    return owner, pet, Scheduler(owner)


def test_mark_complete_flips_status_flag():
    task = Task(description="Medication", time="09:00", duration=5, priority="high")
    assert task.is_complete is False
    task.mark_complete()
    assert task.is_complete is True


def test_pet_add_task_changes_collection_size():
    _, pet, _ = make_scheduler()
    original_size = len(pet.tasks)
    pet.add_task(Task(description="Breakfast", time="08:00", duration=10, priority="medium"))
    assert len(pet.tasks) == original_size + 1


def test_schedule_sorting_orders_tasks_by_clock_time():
    _, pet, scheduler = make_scheduler()
    pet.add_task(Task(description="Dinner", time="18:00", duration=10, priority="high"))
    pet.add_task(Task(description="Walk", time="07:30", duration=20, priority="medium"))
    pet.add_task(Task(description="Breakfast", time="08:00", duration=10, priority="low"))

    assert [task.description for task in scheduler.sort_by_time()] == ["Walk", "Breakfast", "Dinner"]


def test_recurring_completion_creates_new_occurrence_for_next_day():
    _, pet, scheduler = make_scheduler()
    task = Task(
        description="Feed",
        time="08:00",
        duration=5,
        priority="medium",
        frequency="daily",
        is_complete=True,
        due_date="2026-03-31",
    )
    pet.add_task(task)

    created = scheduler.handle_recurring_tasks(anchor=date(2026, 3, 31))

    assert len(created) == 1
    _, follow_up = created[0]
    assert follow_up.due_date == "2026-04-01"
    assert follow_up.is_complete is False
    assert follow_up.description == "Feed"


def test_conflict_detection_reports_overlapping_work():
    _, pet, scheduler = make_scheduler()
    pet.add_task(Task(description="Feed", time="09:00", duration=30, priority="high"))
    pet.add_task(Task(description="Walk", time="09:15", duration=20, priority="medium"))

    warnings = scheduler.detect_conflicts()

    assert warnings
    assert "Feed" in warnings[0]
    assert "Walk" in warnings[0]
