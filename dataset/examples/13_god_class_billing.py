"""Bad smell: God Class - esperado: Facade/SRP."""


class BillingBackOffice:
    def __init__(self):
        self.customers = {}
        self.invoices = []
        self.payments = []
        self.collection_notes = []
        self.exports = []

    def register_customer(self, customer_id, name, email, tax_id):
        self.customers[customer_id] = {"name": name, "email": email, "tax_id": tax_id, "blocked": False}

    def update_customer_email(self, customer_id, email):
        self.customers[customer_id]["email"] = email

    def create_invoice(self, customer_id, month, items):
        subtotal = sum(item["price"] * item["quantity"] for item in items)
        invoice = {"customer_id": customer_id, "month": month, "items": items, "total": subtotal, "status": "open"}
        self.invoices.append(invoice)
        return invoice

    def apply_discount(self, invoice, percent):
        invoice["total"] = invoice["total"] * (1 - percent)

    def register_payment(self, customer_id, month, amount, method):
        payment = {"customer_id": customer_id, "month": month, "amount": amount, "method": method}
        self.payments.append(payment)
        for invoice in self.invoices:
            if invoice["customer_id"] == customer_id and invoice["month"] == month:
                invoice["status"] = "paid"
        return payment

    def mark_overdue_invoices(self, month):
        for invoice in self.invoices:
            if invoice["month"] < month and invoice["status"] == "open":
                invoice["status"] = "overdue"
                self.collection_notes.append(f"Collect customer {invoice['customer_id']} for {invoice['month']}")

    def block_delinquent_customers(self):
        overdue_ids = {invoice["customer_id"] for invoice in self.invoices if invoice["status"] == "overdue"}
        for customer_id in overdue_ids:
            self.customers[customer_id]["blocked"] = True

    def send_collection_notice(self, customer_id):
        customer = self.customers[customer_id]
        self.collection_notes.append(f"Send notice to {customer['email']}")

    def export_monthly_summary(self, month):
        summary = {
            "month": month,
            "invoice_count": sum(1 for invoice in self.invoices if invoice["month"] == month),
            "paid_total": sum(payment["amount"] for payment in self.payments if payment["month"] == month),
        }
        self.exports.append(summary)
        return summary
