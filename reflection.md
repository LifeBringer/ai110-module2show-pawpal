# PawPal+ Project Reflection

## 1. System design

### Core user actions

Three things a pet owner needs to be able to do with PawPal+:

1. **Add a pet** — create a profile for each animal with a name, species, and age so tasks can be tracked per pet.
2. **Schedule a task** — attach a care activity (walk, feeding, medication, etc.) to a pet with a time, duration, priority, and recurrence so nothing gets forgotten.
3. **See today's plan** — view all pending tasks across pets in a clear, prioritized order so the owner knows what to do and when.

### Initial model
My first pass broke the problem into four parts:

- **Task** for a single care action with timing, priority, recurrence, and completion state
- **Pet** for grouping the tasks that belong to one animal
- **Owner** for household-level aggregation across pets
- **Scheduler** for algorithmic behavior rather than data storage

That structure gave me a clean place to put sorting and planning rules without overloading the UI layer.

### Design changes during implementation
One design change was moving schedule-related calculations into small task properties and helper methods. Instead of making the scheduler parse time strings everywhere, `Task` now exposes computed timing information and can generate its own next recurring occurrence. That made the scheduler easier to read and reduced repeated logic.

I also adjusted conflict detection to look for overlapping intervals instead of only exact time matches. That felt like a better fit for a planner because a 09:00 task lasting 30 minutes should still warn about a 09:15 task.

## 2. Scheduling logic and tradeoffs

### Constraints considered
The scheduler mainly considers:

- start time for building a readable daily plan
- priority for urgency
- recurrence for daily and weekly chores
- overlap/conflict checks for tasks that collide in time

### Tradeoff
The planner is intentionally lightweight. It warns about overlaps and can suggest an open slot, but it does not automatically rearrange the schedule or optimize across many competing constraints. That tradeoff keeps the system understandable and predictable for a small pet-care app.

## 3. AI collaboration

### How AI helped
AI was useful for brainstorming architecture, reviewing edge cases, and tightening test coverage. The best prompts were specific, such as asking for alternative ways to structure recurrence handling or ideas for boundary tests around free-slot calculation.

### Human judgment
I still had to evaluate every suggestion against the app goals. In particular, I avoided putting too much logic in the Streamlit file. Even when AI suggested directly sorting or filtering inside the UI code, I kept those decisions in the scheduler so the backend stayed reusable and testable.

## 4. Testing and verification

### What I tested
The test suite focuses on the behaviors that matter most to the planner:

- marking a task complete
- adding a task to a pet
- returning tasks in chronological order
- generating the next occurrence for a recurring task
- reporting schedule conflicts

### Confidence level
I am confident in the core scheduling flows because they are exercised both through tests and through the CLI demo. If I extended the project, I would add tests for invalid times, duplicate recurring events, and more UI-driven interactions.

## 5. Reflection

### What went well
The most successful part of the project was the boundary between the domain model and the scheduler. That made the Streamlit integration straightforward and kept the code from becoming one large script.

### What I would improve next
A next iteration could add editing and completion toggles directly in the UI, plus stronger validation around manual time entry.

### Key takeaway
The main lesson was that a simple system becomes much easier to evolve when the data model, planning logic, and presentation layer are separated early.
