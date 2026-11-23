"""FinOps Guard örnek web sitesi: kitap mağazası.

Bilerek durumsuz (stateless) tutuldu: sepet tarayıcıda (localStorage) durur.
Böylece birden fazla Fargate görevi arkada çalışsa da oturum sorunu olmaz.
"""

import os

from flask import Blueprint, abort, jsonify, render_template

bp = Blueprint(
    "shop",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)

PRODUCTS = [
    {
        "id": 1,
        "name": "Bulut Mimarisi 101",
        "price": 189.90,
        "category": "Bulut",
        "desc": "Bulut kavramlarına giriş.",
    },
    {
        "id": 2,
        "name": "Terraform ile Altyapı",
        "price": 249.00,
        "category": "DevOps",
        "desc": "Kod olarak altyapı.",
    },
    {
        "id": 3,
        "name": "CI/CD Uygulamaları",
        "price": 219.50,
        "category": "DevOps",
        "desc": "Sürekli entegrasyon ve teslim.",
    },
    {
        "id": 4,
        "name": "FinOps Rehberi",
        "price": 279.00,
        "category": "Bulut",
        "desc": "Bulut maliyet yönetimi.",
    },
    {
        "id": 5,
        "name": "Python ile Veri Analizi",
        "price": 199.00,
        "category": "Veri",
        "desc": "Pandas ve görselleştirme.",
    },
    {
        "id": 6,
        "name": "Makine Öğrenmesi Temelleri",
        "price": 259.90,
        "category": "Veri",
        "desc": "Temel algoritmalar.",
    },
]


@bp.app_context_processor
def inject_version():
    return {"version": os.getenv("APP_VERSION", "dev")}


def _find(product_id: int):
    return next((p for p in PRODUCTS if p["id"] == product_id), None)


@bp.get("/")
def index():
    return render_template("index.html", featured=PRODUCTS[:3])


@bp.get("/urunler")
def products():
    return render_template("products.html", products=PRODUCTS)


@bp.get("/urun/<int:product_id>")
def product(product_id: int):
    item = _find(product_id)
    if item is None:
        abort(404)
    return render_template("product.html", p=item)


@bp.get("/sepet")
def cart():
    return render_template("cart.html")


@bp.get("/hakkinda")
def about():
    return render_template("about.html")


@bp.get("/api/products")
def api_products():
    return jsonify(PRODUCTS)
