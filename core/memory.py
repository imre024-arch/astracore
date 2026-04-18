class Memory:
    def __init__(self):
        self._store: dict = {}

    def set(self, key: str, value) -> None:
        self._store[key] = value

    def get(self, key: str, default=None):
        return self._store.get(key, default)

    def all(self) -> dict:
        return dict(self._store)

    def clear(self) -> None:
        self._store.clear()
