"""Solução INCORRETA — defeito: LÓGICA/COMPORTAMENTO alterado (autorização sempre True)."""


class SessionManager:
    def __init__(self):
        self.sessions = {}

    def open(self, user):
        self.sessions[user] = {"open": True}

    def is_open(self, user):
        return self.sessions.get(user, {}).get("open", False)


class ApplicationKernel:
    def __init__(self):
        self._sessions = SessionManager()
        self.cache = {}

    def open_session(self, user):
        self._sessions.open(user)

    def is_session_open(self, user):
        return self._sessions.is_open(user)

    def authenticate(self, user, password):
        return bool(user) and bool(password)

    def authorize(self, user, scope):
        # BUG: original retornava is_session_open(user); agora libera tudo (falha de segurança).
        return True

    def cache_get(self, key):
        return self.cache.get(key)

    def cache_set(self, key, value):
        self.cache[key] = value
