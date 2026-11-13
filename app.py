"""Ứng dụng Flask. Chạy bằng: python app.py"""
import os
import secrets
from flask import Flask, render_template, request, session, abort, flash
from dotenv import load_dotenv
from db_config import get_db_connection
from src.controllers.thietbi import thietbi_bp
from src.controllers.baotri import baotri_bp
from src.controllers.phongban import phongban_bp
from src.controllers.danhmuc import danhmuc_bp

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-please-change")
app.register_blueprint(thietbi_bp)
app.register_blueprint(baotri_bp)
app.register_blueprint(phongban_bp)
app.register_blueprint(danhmuc_bp)

@app.context_processor
def add_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["csrf_token"]}

@app.before_request
def verify_csrf():
    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        stored = session.get("csrf_token", "")
        if not stored or not secrets.compare_digest(stored, submitted):
            abort(400, description="Mã bảo vệ form không hợp lệ. Hãy tải lại trang.")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        try:
            name = conn.cursor().execute("SELECT DB_NAME()").fetchone()[0]
        finally:
            conn.close()
        return f"Đã kết nối SQL Server: {name}"
    except Exception:
        app.logger.exception("Lỗi kết nối cơ sở dữ liệu")
        return "Không kết nối được database. Xem lỗi trong Terminal VS Code.", 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
