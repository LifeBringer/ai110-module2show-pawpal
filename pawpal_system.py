from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import Iterable, Optional
from uuid import uuid4

TIME_FMT = "%H:%M"
DATE_FMT = "%Y-%m-%d"
PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


def _minutes_from_clock(value: str) -> int:
    parsed = datetime.strptime(value, TIME_FMT)
    return parsed.hour * 60 + parsed.minute


def _clock_from_minutes(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


@dataclass(slots=True)
class Task:
    """A pet-care action that can be scheduled and optionally recur."""

    description: str
    time: str
    duration: int
    priority: str
    frequency: str = "once"
    task_id: str = field(default_factory=lambda: str(uuid4()))
    is_complete: bool = False
    due_date: Optional[str] = None

    def mark_complete(self) -> None:
        self.is_complete = True

    def reopen(self) -> None:
        self.is_complete = False

    def move_to(self, new_time: str) -> None:
        _minutes_from_clock(new_time)
        self.time = new_time

    @property
    def start_minutes(self) -> int:
        return _minutes_from_clock(self.time)

    @property
    def end_minutes(self) -> int:
        return self.start_minutes + self.duration

    def recurrence_next_date(self, anchor: Optional[date] = None) -> Optional[str]:
        if self.frequency not in {"daily", "weekly"}:
            return None
        base = anchor or date.today()
        offset = 1 if self.frequency == "daily" else 7
        return (base + timedelta(days=offset)).strftime(DATE_FMT)

    def clone_for_next_occurrence(self, anchor: Optional[date] = None) -> Optional["Task"]:
        next_due = self.recurrence_next_date(anchor)
        if next_due is None:
            return None
        return Task(
            description=self.description,
            time=self.time,
            duration=self.duration,
            priority=self.priority,
            frequency=self.frequency,
            due_date=next_due,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "Task":
        return cls(**payload)


@dataclass(slots=True)
class Pet:
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> Task:
        self.tasks.append(task)
        return task

    def remove_task(self, task_id: str) -> bool:
        before = len(self.tasks)
        self.tasks = [task for task in self.tasks if task.task_id != task_id]
        return len(self.tasks) != before

    def tasks_for_display(self) -> list[Task]:
        return list(self.tasks)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "tasks": [task.to_dict() for task in self.tasks],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Pet":
        return cls(
            name=payload["name"],
            species=payload["species"],
            age=payload["age"],
            tasks=[Task.from_dict(item) for item in payload.get("tasks", [])],
        )


@dataclass(slots=True)
class Owner:
    name: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> Pet:
        existing = self.find_pet(pet.name)
        if existing is None:
            self.pets.append(pet)
            return pet
        return existing

    def find_pet(self, pet_name: str) -> Optional[Pet]:
        needle = pet_name.strip().lower()
        for pet in self.pets:
            if pet.name.strip().lower() == needle:
                return pet
        return None

    def remove_pet(self, pet_name: str) -> bool:
        before = len(self.pets)
        self.pets = [pet for pet in self.pets if pet.name.strip().lower() != pet_name.strip().lower()]
        return len(self.pets) != before

    def all_tasks(self) -> list[tuple[Pet, Task]]:
        pairs: list[tuple[Pet, Task]] = []
        for pet in self.pets:
            for task in pet.tasks:
                pairs.append((pet, task))
        return pairs

    def tasks_for_pet(self, pet_name: Optional[str] = None) -> list[Task]:
        if pet_name is None or pet_name == "All pets":
            return [task for _, task in self.all_tasks()]
        pet = self.find_pet(pet_name)
        return list(pet.tasks) if pet else []

    def to_dict(self) -> dict:
        return {"name": self.name, "pets": [pet.to_dict() for pet in self.pets]}

    def save_to_json(self, filepath: str | Path) -> None:
        Path(filepath).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_from_json(cls, filepath: str | Path) -> "Owner":
        payload = json.loads(Path(filepath).read_text(encoding="utf-8"))
        return cls(name=payload["name"], pets=[Pet.from_dict(item) for item in payload.get("pets", [])])


class Scheduler:
    """Provides views and helper algorithms over an owner's pet-care tasks."""

    def __init__(self, owner: Owner):
        self.owner = owner

    def _task_pairs(self, pet_name: Optional[str] = None) -> list[tuple[Pet, Task]]:
        if pet_name is None or pet_name == "All pets":
            return self.owner.all_tasks()
        pet = self.owner.find_pet(pet_name)
        return [(pet, task) for task in pet.tasks] if pet else []

    def _sort_key_time(self, task: Task) -> tuple[int, str]:
        return (task.start_minutes, task.description.lower())

    def get_daily_schedule(self) -> list[Task]:
        return self.sort_by_time()

    def sort_by_time(self, tasks: Optional[Iterable[Task]] = None) -> list[Task]:
        task_list = list(tasks) if tasks is not None else self.owner.tasks_for_pet()
        return sorted(task_list, key=self._sort_key_time)

    def sort_by_priority(self, tasks: Optional[Iterable[Task]] = None) -> list[Task]:
        task_list = list(tasks) if tasks is not None else self.owner.tasks_for_pet()
        return sorted(
            task_list,
            key=lambda task: (-PRIORITY_WEIGHT.get(task.priority, 0), task.start_minutes, task.description.lower()),
        )

    def filter_tasks(self, pet_name: Optional[str] = None, is_complete: Optional[bool] = None) -> list[Task]:
        filtered = self.owner.tasks_for_pet(pet_name)
        if is_complete is not None:
            filtered = [task for task in filtered if task.is_complete is is_complete]
        return filtered

    def detect_conflicts(self) -> list[str]:
        warnings: list[str] = []
        sorted_pairs = sorted(self.owner.all_tasks(), key=lambda pair: pair[1].start_minutes)
        for index, (pet_a, task_a) in enumerate(sorted_pairs):
            for pet_b, task_b in sorted_pairs[index + 1 :]:
                if task_b.start_minutes >= task_a.end_minutes:
                    break
                warnings.append(
                    f"{pet_a.name}: {task_a.description} overlaps with {pet_b.name}: {task_b.description} at {task_b.time}."
                )
        return warnings

    def handle_recurring_tasks(self, anchor: Optional[date] = None) -> list[tuple[Pet, Task]]:
        created: list[tuple[Pet, Task]] = []
        for pet in self.owner.pets:
            existing_signatures = {(t.description, t.time, t.due_date, t.frequency) for t in pet.tasks}
            for task in list(pet.tasks):
                if not task.is_complete:
                    continue
                follow_up = task.clone_for_next_occurrence(anchor)
                if follow_up is None:
                    continue
                signature = (follow_up.description, follow_up.time, follow_up.due_date, follow_up.frequency)
                if signature in existing_signatures:
                    continue
                pet.add_task(follow_up)
                existing_signatures.add(signature)
                created.append((pet, follow_up))
        return created

    def find_next_available_slot(self, duration: int, day_start: str = "06:00", day_end: str = "22:00") -> Optional[str]:
        start_boundary = _minutes_from_clock(day_start)
        end_boundary = _minutes_from_clock(day_end)
        blocks = sorted((task.start_minutes, task.end_minutes) for task in self.owner.tasks_for_pet())
        cursor = start_boundary
        for start, end in blocks:
            if start - cursor >= duration:
                return _clock_from_minutes(cursor)
            cursor = max(cursor, end)
        if end_boundary - cursor >= duration:
            return _clock_from_minutes(cursor)
        return None

    def weighted_sort(self, tasks: Optional[Iterable[Task]] = None) -> list[Task]:
        task_list = list(tasks) if tasks is not None else self.owner.tasks_for_pet()

        def score(task: Task) -> tuple[int, int]:
            urgency = PRIORITY_WEIGHT.get(task.priority, 0)
            daytime_bonus = 24 * 60 - task.start_minutes
            return (urgency * 10_000 + daytime_bonus, -task.duration)

        return sorted(task_list, key=score, reverse=True)
