"""Quản lý phòng ban (dựa trên bảng PHONG_BAN hiện có)."""
import pyodbc
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_config import get_db_connection

phongban_bp = Blueprint("phongban", __name__, url_prefix="/phong-ban")


def _get_one(cursor, ma):
    return cursor.execute(
        "SELECT MaPhongBan, TenPhongBan FROM PHONG_BAN WHERE MaPhongBan=?", ma
    ).fetchone()


@phongban_bp.get("/")
def danh_sach():
    q = request.args.get("q", "").strip()[:100]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT pb.MaPhongBan, pb.TenPhongBan,
              (SELECT COUNT(*) FROM THIET_BI tb WHERE tb.MaPhongBan=pb.MaPhongBan) AS SoThietBi
            FROM PHONG_BAN pb
            WHERE (? = '' OR pb.MaPhongBan LIKE ? OR pb.TenPhongBan LIKE ?)
            ORDER BY pb.MaPhongBan
        """, q, f"%{q}%", f"%{q}%").fetchall()
    return render_template("phongban.html", rows=rows, q=q)


@phongban_bp.route("/them", methods=["GET", "POST"])
def them():
    if request.method == "POST":
        ma = request.form.get("ma", "").strip().upper()
        ten = request.form.get("ten", "").strip()
        if not ma or not ten or len(ma) > 20 or len(ten) > 100:
            flash("Mã (tối đa 20 ký tự) và tên phòng ban (tối đa 100 ký tự) là bắt buộc.", "danger")
        else:
            with get_db_connection() as conn:
                try:
                    conn.cursor().execute("INSERT INTO PHONG_BAN (MaPhongBan,TenPhongBan) VALUES (?,?)", ma, ten)
                    conn.commit()
                except pyodbc.IntegrityError:
                    conn.rollback()
                    flash("Mã phòng ban đã tồn tại.", "danger")
                else:
                    flash("Đã thêm phòng ban.", "success")
                    return redirect(url_for("phongban.danh_sach"))
    return render_template("phongban_form.html", phongban=None)


@phongban_bp.route("/<ma>/sua", methods=["GET", "POST"])
def sua(ma):
    with get_db_connection() as conn:
        cur = conn.cursor()
        phongban = _get_one(cur, ma)
        if not phongban:
            abort(404)
        if request.method == "POST":
            ten = request.form.get("ten", "").strip()
            if not ten or len(ten) > 100:
                flash("Tên phòng ban là bắt buộc và tối đa 100 ký tự.", "danger")
            else:
                cur.execute("UPDATE PHONG_BAN SET TenPhongBan=? WHERE MaPhongBan=?", ten, ma)
                conn.commit()
                flash("Đã sửa phòng ban.", "success")
                return redirect(url_for("phongban.danh_sach"))
    return render_template("phongban_form.html", phongban=phongban)


@phongban_bp.post("/<ma>/xoa")
def xoa(ma):
    with get_db_connection() as conn:
        cur = conn.cursor()
        if not _get_one(cur, ma):
            abort(404)
        count = cur.execute("SELECT COUNT(*) FROM THIET_BI WHERE MaPhongBan=?", ma).fetchone()[0]
        if count:
            flash("Không thể xóa: phòng ban đang có thiết bị. Hãy chuyển thiết bị sang phòng ban khác trước.", "warning")
        else:
            try:
                cur.execute("DELETE FROM PHONG_BAN WHERE MaPhongBan=?", ma)
                conn.commit()
            except pyodbc.IntegrityError:
                conn.rollback()
                flash("Không thể xóa vì phòng ban còn được tham chiếu.", "danger")
            else:
                flash("Đã xóa phòng ban.", "success")
    return redirect(url_for("phongban.danh_sach"))
