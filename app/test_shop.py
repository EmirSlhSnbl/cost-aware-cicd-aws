import pytest
from flask import Flask

import shop


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(shop.bp)
    return app.test_client()


@pytest.mark.parametrize(
    "path", ["/", "/urunler", "/sepet", "/hakkinda", "/urun/1", "/urun/6"]
)
def test_pages_ok(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "Kitap Durağı" in r.get_data(as_text=True)


def test_unknown_product_404(client):
    assert client.get("/urun/999").status_code == 404


def test_api_products(client):
    data = client.get("/api/products").get_json()
    assert len(data) == 6
    assert all({"id", "name", "price", "category"} <= set(p) for p in data)


def test_ids_unique_and_prices_positive():
    ids = [p["id"] for p in shop.PRODUCTS]
    assert len(ids) == len(set(ids))
    assert all(p["price"] > 0 for p in shop.PRODUCTS)


def test_static_assets_served(client):
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/cart.js").status_code == 200


def test_version_shown(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "sha-abc1234")
    assert "sha-abc1234" in client.get("/").get_data(as_text=True)
