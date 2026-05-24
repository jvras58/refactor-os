"""Bad smell: God Class - esperado: Facade/SRP."""


class ProjectWorkspace:
    def __init__(self):
        self.members = {}
        self.tasks = []
        self.comments = []
        self.activity_log = []
        self.notifications = []

    def add_member(self, member_id, name, role):
        self.members[member_id] = {"name": name, "role": role, "active": True}
        self.activity_log.append(f"member_added:{member_id}")

    def deactivate_member(self, member_id):
        self.members[member_id]["active"] = False
        self.activity_log.append(f"member_deactivated:{member_id}")

    def create_task(self, title, owner_id, estimate_hours):
        task = {"title": title, "owner_id": owner_id, "estimate_hours": estimate_hours, "status": "todo"}
        self.tasks.append(task)
        self.notifications.append(f"Task assigned to {self.members[owner_id]['name']}")
        return task

    def move_task(self, task_index, status):
        self.tasks[task_index]["status"] = status
        self.activity_log.append(f"task_{task_index}_moved_to_{status}")

    def add_comment(self, task_index, member_id, text):
        comment = {"task_index": task_index, "member_id": member_id, "text": text}
        self.comments.append(comment)
        self.notifications.append(f"New comment from {self.members[member_id]['name']}")

    def calculate_progress(self):
        if not self.tasks:
            return 0.0
        done = sum(1 for task in self.tasks if task["status"] == "done")
        return done / len(self.tasks)

    def estimate_remaining_hours(self):
        return sum(task["estimate_hours"] for task in self.tasks if task["status"] != "done")

    def build_status_report(self):
        return {
            "members": len([member for member in self.members.values() if member["active"]]),
            "tasks": len(self.tasks),
            "progress": self.calculate_progress(),
            "remaining_hours": self.estimate_remaining_hours(),
            "recent_comments": self.comments[-5:],
        }

    def flush_notifications(self):
        sent = list(self.notifications)
        self.notifications.clear()
        return sent
