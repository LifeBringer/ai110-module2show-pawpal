from __future__ import annotations

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def build_demo_owner() -> Owner:
    owner = Owner(name="Jordan")

    mochi = Pet(name="Mochi", species="dog", age=3)
    luna = Pet(name="Luna", species="cat", age=2)

    mochi.add_task(Task(description="Breakfast", time="07:30", duration=10, priority="medium", frequency="daily"))
    mochi.add_task(Task(description="Morning walk", time="08:00", duration=30, priority="high", frequency="daily"))
    mochi.add_task(Task(description="Vet check-in", time="09:00", duration=60, priority="high"))
    luna.add_task(Task(description="Grooming", time="09:30", duration=30, priority="medium"))
    luna.add_task(Task(description="Playtime", time="18:00", duration=20, priority="low"))

    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner


def describe(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def main() -> None:
    owner = build_demo_owner()
    scheduler = Scheduler(owner)

    describe("Today's schedule")
    for task in scheduler.get_daily_schedule():
        print(f"{task.time} | {task.description:<16} | {task.priority:<6} | {task.frequency}")

    describe("Priority order")
    for task in scheduler.sort_by_priority():
        print(f"{task.priority.title():<6} -> {task.description}")

    describe("Pending tasks")
    for task in scheduler.filter_tasks(is_complete=False):
        print(f"{task.description} ({task.time})")

    describe("Conflicts")
    for warning in scheduler.detect_conflicts() or ["No overlaps detected."]:
        print(warning)

    describe("Recurring follow-up")
    recurring = owner.find_pet("Mochi").tasks[1]
    recurring.mark_complete()
    for pet, task in scheduler.handle_recurring_tasks(anchor=date(2026, 3, 31)) or []:
        print(f"{pet.name} gets another '{task.description}' due {task.due_date}")

    describe("Next available 30-minute slot")
    print(scheduler.find_next_available_slot(30) or "No gap available")

    describe("Weighted sort")
    for task in scheduler.weighted_sort():
        print(f"{task.description} -> {task.priority}/{task.time}")

    describe("Persistence demo")
    owner.save_to_json("data.json")
    reloaded = Owner.load_from_json("data.json")
    print(f"Reloaded owner: {reloaded.name}; pets: {', '.join(p.name for p in reloaded.pets)}")


if __name__ == "__main__":
    main()
