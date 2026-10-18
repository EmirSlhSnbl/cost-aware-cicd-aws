import os
from flask import Flask, jsonify

app = Flask(__name__)
APP_VERSION = os.getenv("APP_VERSION", "dev")


@app.get("/")
def index():
    return jsonify(message="Merhaba, FinOps Guard!", version=APP_VERSION)


@app.get("/health")
def health():
    return jsonify(status="ok"), 200