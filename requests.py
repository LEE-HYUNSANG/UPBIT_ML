class Response:
    def __init__(self, json=None, status_code=200):
        self._json = json or {}
        self.status_code = status_code

    def json(self):
        return self._json


def get(url, params=None, headers=None, timeout=10):
    return Response()


def post(url, data=None, timeout=5):
    return Response()
