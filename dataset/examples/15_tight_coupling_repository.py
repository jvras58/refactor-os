"""Bad smell: Tight Coupling - esperado: Dependency Injection."""


class InMemoryCustomerRepository:
    def __init__(self):
        self.customers = {
            1: {"name": "Ana", "status": "active", "total_spent": 1200.0},
            2: {"name": "Bruno", "status": "inactive", "total_spent": 80.0},
        }

    def find_by_id(self, customer_id: int) -> dict:
        return self.customers[customer_id]

    def save(self, customer_id: int, data: dict) -> None:
        self.customers[customer_id] = data


class CustomerLoyaltyService:
    def __init__(self):
        self.repository = InMemoryCustomerRepository()

    def upgrade_customer(self, customer_id: int) -> dict:
        customer = self.repository.find_by_id(customer_id)
        if customer["status"] != "active":
            raise ValueError("inactive customers cannot be upgraded")
        if customer["total_spent"] >= 1000:
            customer["tier"] = "gold"
        else:
            customer["tier"] = "silver"
        self.repository.save(customer_id, customer)
        return customer
