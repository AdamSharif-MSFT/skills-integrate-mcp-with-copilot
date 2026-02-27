"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
DB_PATH = current_dir / "activities.db"

SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                student_email TEXT NOT NULL,
                UNIQUE(activity_id, student_email),
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
            )
            """
        )


def seed_db_if_empty() -> None:
    with get_connection() as connection:
        activity_count = connection.execute(
            "SELECT COUNT(*) AS total FROM activities"
        ).fetchone()["total"]

        if activity_count > 0:
            return

        for activity_name, details in SEED_ACTIVITIES.items():
            cursor = connection.execute(
                """
                INSERT INTO activities (name, description, schedule, max_participants)
                VALUES (?, ?, ?, ?)
                """,
                (
                    activity_name,
                    details["description"],
                    details["schedule"],
                    details["max_participants"],
                ),
            )
            activity_id = cursor.lastrowid

            for participant in details["participants"]:
                connection.execute(
                    """
                    INSERT INTO signups (activity_id, student_email)
                    VALUES (?, ?)
                    """,
                    (activity_id, participant),
                )


def get_activity_record(activity_name: str) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT id, name, max_participants FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    seed_db_if_empty()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT a.name, a.description, a.schedule, a.max_participants, s.student_email
            FROM activities a
            LEFT JOIN signups s ON a.id = s.activity_id
            ORDER BY a.name, s.student_email
            """
        ).fetchall()

    activities: dict[str, dict] = {}
    for row in rows:
        name = row["name"]
        if name not in activities:
            activities[name] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [],
            }
        if row["student_email"]:
            activities[name]["participants"].append(row["student_email"])

    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    activity = get_activity_record(activity_name)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    with get_connection() as connection:
        existing_signup = connection.execute(
            """
            SELECT 1 FROM signups
            WHERE activity_id = ? AND student_email = ?
            """,
            (activity["id"], email),
        ).fetchone()

        if existing_signup:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )

        connection.execute(
            """
            INSERT INTO signups (activity_id, student_email)
            VALUES (?, ?)
            """,
            (activity["id"], email),
        )

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    activity = get_activity_record(activity_name)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    with get_connection() as connection:
        result = connection.execute(
            """
            DELETE FROM signups
            WHERE activity_id = ? AND student_email = ?
            """,
            (activity["id"], email),
        )

        if result.rowcount == 0:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

    return {"message": f"Unregistered {email} from {activity_name}"}
