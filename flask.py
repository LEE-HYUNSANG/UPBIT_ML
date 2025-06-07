import types
import json as _json

class Response:
    def __init__(self, data, status=200):
        if isinstance(data, str):
            self.data = data
        else:
            self.data = _json.dumps(data)
        self.status_code = status

    def get_json(self):
        try:
            return _json.loads(self.data)
        except Exception:
            return None


class Flask:
    def __init__(self, name):
        self.routes = {}

    def route(self, rule, methods=["GET"]):
        methods_key = tuple(sorted(m.upper() for m in methods))

        def decorator(func):
            self.routes[(rule, methods_key)] = func
            return func

        return decorator

    def test_client(self):
        app = self

        class Client:
            def get(self, path):
                func = app.routes.get((path, ("GET",))) or app.routes.get((path, ("GET", "POST")))
                return func()

        return Client()


def jsonify(obj):
    return Response(obj)


def render_template(*a, **k):
    return ""


request = types.SimpleNamespace(args={}, method="GET", get_json=lambda force=False: {})

__all__ = ["Flask", "Response", "jsonify", "render_template", "request"]
