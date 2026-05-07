"""Bad smell: God Class — esperado: Facade/SRP."""


class OrderManager:
    def __init__(self):
        self.orders = []
        self.users = []
        self.inventory = {}
        self.audit_log = []

    def create_user(self, name, email):
        self.users.append({"name": name, "email": email})

    def update_user(self, idx, name):
        self.users[idx]["name"] = name

    def delete_user(self, idx):
        self.users.pop(idx)

    def list_users(self):
        return list(self.users)

    def add_inventory(self, sku, qty):
        self.inventory[sku] = self.inventory.get(sku, 0) + qty

    def remove_inventory(self, sku, qty):
        self.inventory[sku] -= qty

    def check_stock(self, sku):
        return self.inventory.get(sku, 0)

    def reserve_stock(self, sku, qty):
        if self.inventory.get(sku, 0) >= qty:
            self.inventory[sku] -= qty
            return True
        return False

    def create_order(self, user_idx, sku, qty):
        if not self.reserve_stock(sku, qty):
            raise ValueError("no stock")
        order = {"user": self.users[user_idx], "sku": sku, "qty": qty}
        self.orders.append(order)
        self.log("order_created", order)
        self.send_email(self.users[user_idx]["email"], "Order placed")
        return order

    def cancel_order(self, idx):
        order = self.orders.pop(idx)
        self.add_inventory(order["sku"], order["qty"])
        self.log("order_cancelled", order)

    def list_orders(self):
        return list(self.orders)

    def send_email(self, to, body):
        print(f"Email -> {to}: {body}")

    def send_sms(self, to, body):
        print(f"SMS -> {to}: {body}")

    def log(self, event, payload):
        self.audit_log.append({"event": event, "payload": payload})

    def export_audit(self):
        return list(self.audit_log)

    def total_revenue(self):
        return sum(o.get("price", 0) * o["qty"] for o in self.orders)

    def report(self):
        return {
            "users": len(self.users),
            "orders": len(self.orders),
            "stock": dict(self.inventory),
            "revenue": self.total_revenue(),
        }
