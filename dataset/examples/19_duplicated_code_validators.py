"""Bad smell: Duplicated Code - esperado: Template Method."""


class SignupFormValidator:
    def validate(self, form: dict) -> list[str]:
        errors = []
        if not form.get("email"):
            errors.append("email is required")
        if "@" not in form.get("email", ""):
            errors.append("email is invalid")
        if not form.get("password"):
            errors.append("password is required")
        if len(form.get("password", "")) < 8:
            errors.append("password is too short")
        if not form.get("accepted_terms"):
            errors.append("terms must be accepted")
        return errors


class ProfileFormValidator:
    def validate(self, form: dict) -> list[str]:
        errors = []
        if not form.get("email"):
            errors.append("email is required")
        if "@" not in form.get("email", ""):
            errors.append("email is invalid")
        if not form.get("display_name"):
            errors.append("display name is required")
        if len(form.get("display_name", "")) < 3:
            errors.append("display name is too short")
        if not form.get("timezone"):
            errors.append("timezone is required")
        return errors


class CheckoutFormValidator:
    def validate(self, form: dict) -> list[str]:
        errors = []
        if not form.get("email"):
            errors.append("email is required")
        if "@" not in form.get("email", ""):
            errors.append("email is invalid")
        if not form.get("address"):
            errors.append("address is required")
        if not form.get("payment_method"):
            errors.append("payment method is required")
        if form.get("installments", 1) > 12:
            errors.append("too many installments")
        return errors
