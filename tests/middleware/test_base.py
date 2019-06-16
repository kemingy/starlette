import pytest

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient


def test_custom_middleware():
    class CustomMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["Custom-Header"] = "Example"
            return response


    app = Starlette()
    app.add_middleware(CustomMiddleware)


    @app.route("/")
    def homepage(request):
        return PlainTextResponse("Homepage")


    @app.route("/exc")
    def exc(request):
        raise Exception()


    @app.route("/no-response")
    class NoResponse:
        def __init__(self, scope, receive, send):
            pass

        def __await__(self):
            return self.dispatch().__await__()

        async def dispatch(self):
            pass


    @app.websocket_route("/ws")
    async def websocket_endpoint(session):
        await session.accept()
        await session.send_text("Hello, world!")
        await session.close()

    client = TestClient(app)
    response = client.get("/")
    assert response.headers["Custom-Header"] == "Example"

    with pytest.raises(Exception):
        response = client.get("/exc")

    with pytest.raises(RuntimeError):
        response = client.get("/no-response")

    with client.websocket_connect("/ws") as session:
        text = session.receive_text()
        assert text == "Hello, world!"


def test_middleware_decorator():
    app = Starlette()

    @app.route("/homepage")
    def homepage(request):
        return PlainTextResponse("Homepage")

    @app.middleware("http")
    async def plaintext(request, call_next):
        if request.url.path == "/":
            return PlainTextResponse("OK")
        response = await call_next(request)
        response.headers["Custom"] = "Example"
        return response

    client = TestClient(app)
    response = client.get("/")
    assert response.text == "OK"

    response = client.get("/homepage")
    assert response.text == "Homepage"
    assert response.headers["Custom"] == "Example"

def test_state_data_across_multiple_middlewares():
    expected_value = 'yes'

    class aMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.show_me = expected_value
            response = await call_next(request)
            return response

    class bMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["X-State-Show-Me"] = request.state.show_me
            return response

    app = Starlette()
    app.add_middleware(aMiddleware)
    app.add_middleware(bMiddleware)

    @app.route("/")
    def homepage(request):
        return PlainTextResponse("OK")

    client = TestClient(app)
    response = client.get("/")
    assert response.text == "OK"
    assert response.headers["X-State-Show-Me"] == expected_value
