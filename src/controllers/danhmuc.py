"""CRUD danh mục; tương thích schema gốc, hỗ trợ mở rộng Mô tả/Trạng thái."""
import pyodbc
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_config import get_db_connection

danhmuc_bp = Blueprint("danhmuc", __name__, url_prefix="/danh-muc")


def _extended(cur):
    """Không bắt buộc chạy migration: schema gốc vẫn dùng được."""
    return bool(cur.execute("""
        SELECT CASE WHEN COL_LENGTH('dbo.DANH_MUC_THIET_BI','MoTa') IS NOT NULL
          AND COL_LENGTH('dbo.DANH_MUC_THIET_BI','TrangThai') IS NOT NULL THEN 1 ELSE 0 END
    """).fetchone()[0])


def _get_one(cur, ma, extended):
    cols = "MaDanhMuc, TenDanhMuc, MoTa, TrangThai" if extended else "MaDanhMuc, TenDanhMuc"
    return cur.execute(f"SELECT {cols} FROM DANH_MUC_THIET_BI WHERE MaDanhMuc=?", ma).fetchone()


@danhmuc_bp.get("/")
def danh_sach():
    q = request.args.get("q", "").strip()[:100]
    with get_db_connection() as conn:
        cur = conn.cursor()
        extended = _extended(cur)
        cols = "dm.MoTa,dm.TrangThai," if extended else ""
        rows = cur.execute(f"""
            SELECT dm.MaDanhMuc,dm.TenDanhMuc,{cols}
             (SELECT COUNT(*) FROM THIET_BI tb WHERE tb.MaDanhMuc=dm.MaDanhMuc) AS SoThietBi
            FROM DANH_MUC_THIET_BI dm
            WHERE (? = '' OR dm.MaDanhMuc LIKE ? OR dm.TenDanhMuc LIKE ?)
            ORDER BY dm.MaDanhMuc
        """, q, f"%{q}%", f"%{q}%").fetchall()
    return render_template("danhmuc.html", rows=rows, q=q, extended=extended)


@danhmuc_bp.route("/them", methods=["GET", "POST"])
def them():
    with get_db_connection() as conn:
        cur = conn.cursor()
        extended = _extended(cur)
        if request.method == "POST":
            ma = request.form.get("ma", "").strip().upper()
            ten = request.form.get("ten", "").strip()
            mota = request.form.get("mota", "").strip()
            trangthai = request.form.get("trangthai", "Đang sử dụng")
            if not ma or not ten or len(ma)>20 or len(ten)>100 or len(mota)>500 or trangthai not in ("Đang sử dụng", "Ngừng sử dụng"):
                flash("Vui lòng kiểm tra mã, tên, mô tả hoặc trạng thái danh mục.", "danger")
            else:
                other = cur.execute("SELECT MaDanhMuc FROM DANH_MUC_THIET_BI WHERE TenDanhMuc=?",ten).fetchone()
                if other:
                    flash("Tên danh mục đã tồn tại.", "danger")
                else:
                    try:
                        if extended:
                            cur.execute("INSERT INTO DANH_MUC_THIET_BI (MaDanhMuc,TenDanhMuc,MoTa,TrangThai) VALUES (?,?,?,?)",ma,ten,mota,trangthai)
                        else:
                            cur.execute("INSERT INTO DANH_MUC_THIET_BI (MaDanhMuc,TenDanhMuc) VALUES (?,?)",ma,ten)
                        conn.commit()
                    except pyodbc.IntegrityError:
                        conn.rollback()
                        flash("Mã hoặc tên danh mục bị trùng.", "danger")
                    else:
                        flash("Đã thêm danh mục.", "success")
                        return redirect(url_for("danhmuc.danh_sach"))
    return render_template("danhmuc_form.html", danhmuc=None, extended=extended)


@danhmuc_bp.route("/<ma>/sua", methods=["GET", "POST"])
def sua(ma):
    with get_db_connection() as conn:
        cur = conn.cursor()
        extended = _extended(cur)
        danhmuc = _get_one(cur, ma, extended)
        if not danhmuc:
            abort(404)
        if request.method == "POST":
            ten = request.form.get("ten", "").strip()
            mota = request.form.get("mota", "").strip()
            trangthai = request.form.get("trangthai", "Đang sử dụng")
            if not ten or len(ten)>100 or len(mota)>500 or trangthai not in ("Đang sử dụng", "Ngừng sử dụng"):
                flash("Tên, mô tả hoặc trạng thái không hợp lệ.", "danger")
            elif cur.execute("SELECT MaDanhMuc FROM DANH_MUC_THIET_BI WHERE TenDanhMuc=? AND MaDanhMuc<>?",ten,ma).fetchone():
                flash("Tên danh mục đã tồn tại.", "danger")
            else:
                if extended:
                    cur.execute("UPDATE DANH_MUC_THIET_BI SET TenDanhMuc=?,MoTa=?,TrangThai=? WHERE MaDanhMuc=?",ten,mota,trangthai,ma)
                else:
                    cur.execute("UPDATE DANH_MUC_THIET_BI SET TenDanhMuc=? WHERE MaDanhMuc=?",ten,ma)
                conn.commit()
                flash("Đã sửa danh mục.", "success")
                return redirect(url_for("danhmuc.danh_sach"))
    return render_template("danhmuc_form.html", danhmuc=danhmuc, extended=extended)


@danhmuc_bp.post("/<ma>/xoa")
def xoa(ma):
    with get_db_connection() as conn:
        cur = conn.cursor()
        extended = _extended(cur)
        if not _get_one(cur, ma, extended):
            abort(404)
        count = cur.execute("SELECT COUNT(*) FROM THIET_BI WHERE MaDanhMuc=?",ma).fetchone()[0]
        if count:
            flash("Không thể xóa: danh mục đang có thiết bị. Hãy chuyển thiết bị sang danh mục khác trước.", "warning")
        else:
            try:
                cur.execute("DELETE FROM DANH_MUC_THIET_BI WHERE MaDanhMuc=?",ma)
                conn.commit()
            except pyodbc.IntegrityError:
                conn.rollback()
                flash("Không thể xóa danh mục vì còn liên kết dữ liệu.", "danger")
            else:
                flash("Đã xóa danh mục.", "success")
    return redirect(url_for("danhmuc.danh_sach"))
