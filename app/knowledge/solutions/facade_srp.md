---
title: Facade/SRP — quebra de uma God Class de contas de usuário
smell: God Class
pattern: Facade/SRP
---

# Facade/SRP — exemplo de solução

Corpus de referência (autoral, distinto do dataset de avaliação). Guia a
refatoração de **God Class**.

## Problema (antes)

```python
class UserAccountManager:
    # mistura autenticação, perfil e notificação numa só classe
    def login(self, email, password): ...
    def logout(self, token): ...
    def reset_password(self, email): ...
    def update_profile(self, user_id, data): ...
    def avatar_url(self, user_id): ...
    def send_welcome(self, user_id): ...
    def send_password_reset(self, user_id): ...
```

## Solução (depois)

```python
class AuthService:
    def login(self, email, password): ...
    def logout(self, token): ...
    def reset_password(self, email): ...


class ProfileService:
    def update_profile(self, user_id, data): ...
    def avatar_url(self, user_id): ...


class NotificationService:
    def send_welcome(self, user_id): ...
    def send_password_reset(self, user_id): ...


class UserAccountManager:
    # Facade fina: orquestra, não reimplementa.
    def __init__(self, auth: AuthService, profile: ProfileService, notify: NotificationService):
        self._auth = auth
        self._profile = profile
        self._notify = notify

    def login(self, email, password):
        return self._auth.login(email, password)

    def update_profile(self, user_id, data):
        return self._profile.update_profile(user_id, data)
```

## Regras aplicadas
- Cada responsabilidade extraída para uma classe com uma única razão de mudar.
- A Facade mantém a API pública e apenas delega — não reintroduz a God Class.
