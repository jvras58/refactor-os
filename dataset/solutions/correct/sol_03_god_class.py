"""Solução CORRETA — Facade/SRP: responsabilidades separadas, fachada delega (API preservada)."""


class UserRepository:
    def __init__(self):
        self.users = []

    def create(self, name, email):
        self.users.append({"name": name, "email": email})

    def update(self, idx, name):
        self.users[idx]["name"] = name

    def delete(self, idx):
        self.users.pop(idx)

    def list(self):
        return list(self.users)


class Inventory:
    def __init__(self):
        self.stock = {}

    def add(self, sku, qty):
        self.stock[sku] = self.stock.get(sku, 0) + qty

    def remove(self, sku, qty):
        self.stock[sku] -= qty

    def check(self, sku):
        return self.stock.get(sku, 0)

    def reserve(self, sku, qty):
        if self.stock.get(sku, 0) >= qty:
            self.stock[sku] -= qty
            return True
        return False


class Notifier:
    def email(self, to, body):
        print(f"Email -> {to}: {body}")

    def sms(self, to, body):
        print(f"SMS -> {to}: {body}")


class AuditLog:
    def __init__(self):
        self.entries = []

    def log(self, event, payload):
        self.entries.append({"event": event, "payload": payload})

    def export(self):
        return list(self.entries)


class OrderManager:
    """Facade que coordena os colaboradores, preservando a API pública original."""

    def __init__(self):
        self.orders = []
        self._users = UserRepository()
        self._inventory = Inventory()
        self._notifier = Notifier()
        self._audit = AuditLog()

    def create_user(self, name, email):
        self._users.create(name, email)

    def update_user(self, idx, name):
        self._users.update(idx, name)

    def delete_user(self, idx):
        self._users.delete(idx)

    def list_users(self):
        return self._users.list()

    def add_inventory(self, sku, qty):
        self._inventory.add(sku, qty)

    def remove_inventory(self, sku, qty):
        self._inventory.remove(sku, qty)

    def check_stock(self, sku):
        return self._inventory.check(sku)

    def reserve_stock(self, sku, qty):
        return self._inventory.reserve(sku, qty)

    def create_order(self, user_idx, sku, qty):
        if not self.reserve_stock(sku, qty):
            raise ValueError("no stock")
        user = self._users.list()[user_idx]
        order = {"user": user, "sku": sku, "qty": qty}
        self.orders.append(order)
        self.log("order_created", order)
        self.send_email(user["email"], "Order placed")
        return order

    def cancel_order(self, idx):
        order = self.orders.pop(idx)
        self.add_inventory(order["sku"], order["qty"])
        self.log("order_cancelled", order)

    def list_orders(self):
        return list(self.orders)

    def send_email(self, to, body):
        self._notifier.email(to, body)

    def send_sms(self, to, body):
        self._notifier.sms(to, body)

    def log(self, event, payload):
        self._audit.log(event, payload)

    def export_audit(self):
        return self._audit.export()

    def total_revenue(self):
        return sum(o.get("price", 0) * o["qty"] for o in self.orders)

    def report(self):
        return {
            "users": len(self._users.list()),
            "orders": len(self.orders),
            "stock": dict(self._inventory.stock),
            "revenue": self.total_revenue(),
        }
