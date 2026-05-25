"""Solução CORRETA — Facade/SRP: kernel delega a colaboradores coesos (API preservada)."""


class ConfigStore:
    def __init__(self):
        self.data = {}

    def load(self, path):
        self.data["path"] = path

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


class SessionManager:
    def __init__(self):
        self.sessions = {}

    def open(self, user):
        self.sessions[user] = {"open": True}

    def close(self, user):
        self.sessions.pop(user, None)

    def is_open(self, user):
        return self.sessions.get(user, {}).get("open", False)


class CacheStore:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def clear(self):
        self.data.clear()


class MetricsCollector:
    def __init__(self):
        self.items = []

    def record(self, name, value):
        self.items.append((name, value))

    def flush(self):
        data = list(self.items)
        self.items.clear()
        return data


class ApplicationKernel:
    """Facade fina sobre colaboradores especializados."""

    def __init__(self):
        self._config = ConfigStore()
        self._sessions = SessionManager()
        self._cache = CacheStore()
        self._metrics = MetricsCollector()

    def load_config(self, path):
        self._config.load(path)

    def get_config(self, key):
        return self._config.get(key)

    def set_config(self, key, value):
        self._config.set(key, value)

    def open_session(self, user):
        self._sessions.open(user)

    def close_session(self, user):
        self._sessions.close(user)

    def is_session_open(self, user):
        return self._sessions.is_open(user)

    def cache_get(self, key):
        return self._cache.get(key)

    def cache_set(self, key, value):
        self._cache.set(key, value)

    def cache_clear(self):
        self._cache.clear()

    def record_metric(self, name, value):
        self._metrics.record(name, value)

    def flush_metrics(self):
        return self._metrics.flush()

    def authenticate(self, user, password):
        return bool(user) and bool(password)

    def authorize(self, user, scope):
        return self.is_session_open(user)

    def render_template(self, name, context):
        return f"{name}:{context}"

    def send_email(self, to, body):
        print(f"email to {to}: {body}")

    def send_push(self, device, body):
        print(f"push to {device}: {body}")

    def enqueue_job(self, job):
        self._cache.data.setdefault("jobs", []).append(job)

    def run_jobs(self):
        return self._cache.data.pop("jobs", [])

    def healthcheck(self):
        return {"ok": True}

    def shutdown(self):
        self._sessions.sessions.clear()
        self._cache.clear()
