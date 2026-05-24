"""Bad smell: God Class - esperado: Facade/SRP."""


class SchoolOffice:
    def __init__(self):
        self.students = {}
        self.grades = {}
        self.attendance = {}
        self.messages = []
        self.payments = []

    def enroll_student(self, student_id, name, guardian_email):
        self.students[student_id] = {"name": name, "guardian_email": guardian_email, "active": True}
        self.grades[student_id] = []
        self.attendance[student_id] = []

    def transfer_student(self, student_id, destination_school):
        self.students[student_id]["active"] = False
        self.messages.append(f"Transfer {student_id} to {destination_school}")

    def record_grade(self, student_id, subject, score):
        self.grades[student_id].append({"subject": subject, "score": score})

    def calculate_average(self, student_id):
        scores = [entry["score"] for entry in self.grades.get(student_id, [])]
        return sum(scores) / len(scores) if scores else 0.0

    def mark_attendance(self, student_id, date, present):
        self.attendance[student_id].append({"date": date, "present": present})

    def attendance_rate(self, student_id):
        records = self.attendance.get(student_id, [])
        if not records:
            return 0.0
        attended = sum(1 for item in records if item["present"])
        return attended / len(records)

    def charge_monthly_fee(self, student_id, month, amount):
        payment = {"student_id": student_id, "month": month, "amount": amount, "paid": False}
        self.payments.append(payment)
        return payment

    def pay_fee(self, student_id, month):
        for payment in self.payments:
            if payment["student_id"] == student_id and payment["month"] == month:
                payment["paid"] = True
                return payment
        raise ValueError("payment not found")

    def send_guardian_message(self, student_id, text):
        email = self.students[student_id]["guardian_email"]
        self.messages.append(f"To {email}: {text}")

    def build_student_report(self, student_id):
        return {
            "student": self.students[student_id],
            "average": self.calculate_average(student_id),
            "attendance_rate": self.attendance_rate(student_id),
            "open_payments": [p for p in self.payments if p["student_id"] == student_id and not p["paid"]],
        }
