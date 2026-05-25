"""Solução INCORRETA — defeito: ASSINATURA PÚBLICA quebrada (métodos do original removidos)."""


class UserRepository:
    def __init__(self):
        self.users = []

    def create(self, name, email):
        self.users.append({"name": name, "email": email})

    def list(self):
        return list(self.users)


class OrderManager:
    """Facade incompleta: perdeu vários métodos públicos do original."""

    def __init__(self):
        self.orders = []
        self._users = UserRepository()
        self.inventory = {}

    def create_user(self, name, email):
        self._users.create(name, email)

    def list_users(self):
        return self._users.list()

    def create_order(self, user_idx, sku, qty):
        order = {"user": self._users.list()[user_idx], "sku": sku, "qty": qty}
        self.orders.append(order)
        return order

    # BUG: update_user, delete_user, add_inventory, remove_inventory, check_stock,
    # reserve_stock, cancel_order, list_orders, send_email, send_sms, log,
    # export_audit, total_revenue e report sumiram — a API pública foi quebrada.
