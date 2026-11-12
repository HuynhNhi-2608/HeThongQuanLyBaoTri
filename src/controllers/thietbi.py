from datetime import date, datetime
import pyodbc
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_config import get_db_connection

thietbi_bp = Blueprint('thietbi', __name__, url_prefix='/thiet-bi')

def ngay_hop_le(gia_tri):
    try:
        return datetime.strptime(gia_tri, '%Y-%m-%d').date() <= date.today()
    except (ValueError, TypeError):
        return False

@thietbi_bp.get('/')
def danh_sach():
    tu_khoa = request.args.get('q', '').strip()
    with get_db_connection() as conn:
        cur = conn.cursor()
        rows = cur.execute('''SELECT tb.MaThietBi,tb.TenThietBi,tb.SerialNumber,tb.NgayMua,
                              tb.ViTri,tb.TrangThai, dm.TenDanhMuc, pb.TenPhongBan
                              FROM THIET_BI tb JOIN DANH_MUC_THIET_BI dm ON tb.MaDanhMuc=dm.MaDanhMuc
                              JOIN PHONG_BAN pb ON tb.MaPhongBan=pb.MaPhongBan
                              WHERE (? = '' OR tb.MaThietBi LIKE ? OR tb.TenThietBi LIKE ? OR tb.SerialNumber LIKE ?)
                              ORDER BY tb.MaThietBi''', tu_khoa, *([f'%{tu_khoa}%'] * 3)).fetchall()
    return render_template('thietbi.html', rows=rows, q=tu_khoa)

@thietbi_bp.route('/them', methods=['GET','POST'])
def them():
    with get_db_connection() as conn:
        cur = conn.cursor()
        has_status = bool(cur.execute("SELECT CASE WHEN COL_LENGTH('dbo.DANH_MUC_THIET_BI','TrangThai') IS NOT NULL THEN 1 ELSE 0 END").fetchone()[0])
        if has_status:
            danhmuc = cur.execute("SELECT MaDanhMuc,TenDanhMuc FROM DANH_MUC_THIET_BI WHERE TrangThai=N'Đang sử dụng' ORDER BY TenDanhMuc").fetchall()
        else:
            danhmuc = cur.execute('SELECT MaDanhMuc,TenDanhMuc FROM DANH_MUC_THIET_BI ORDER BY TenDanhMuc').fetchall()
        phongban = cur.execute('SELECT MaPhongBan,TenPhongBan FROM PHONG_BAN').fetchall()
        if request.method == 'POST':
            ma = request.form.get('ma','').strip()
            ten = request.form.get('ten','').strip()
            ngay = request.form.get('ngay','')
            dm = request.form.get('danhmuc','')
            pb = request.form.get('phongban','')
            if not all([ma,ten,ngay,dm,pb]) or not ngay_hop_le(ngay) or dm not in [item.MaDanhMuc for item in danhmuc] or pb not in [item.MaPhongBan for item in phongban]:
                flash('Điền đầy đủ thông tin và kiểm tra ngày mua.', 'danger')
            else:
                try:
                    cur.execute('''INSERT INTO THIET_BI (MaThietBi,TenThietBi,SerialNumber,NgayMua,ViTri,MaDanhMuc,MaPhongBan)
                                   VALUES (?,?,?,?,?,?,?)''',ma,ten,request.form.get('serial',''),ngay,
                                request.form.get('vitri',''),dm,pb)
                    conn.commit()
                    flash('Đã thêm thiết bị.', 'success')
                    return redirect(url_for('thietbi.danh_sach'))
                except pyodbc.IntegrityError:
                    conn.rollback()
                    flash('Mã thiết bị bị trùng hoặc danh mục/phòng ban không hợp lệ.', 'danger')
    return render_template('thietbi_form.html', danhmuc=danhmuc, phongban=phongban, tb=None)

@thietbi_bp.route('/<ma>/sua', methods=['GET','POST'])
def sua(ma):
    with get_db_connection() as conn:
        cur=conn.cursor()
        tb=cur.execute('SELECT * FROM THIET_BI WHERE MaThietBi=?',ma).fetchone()
        if not tb: abort(404)
        if tb.TrangThai == 'Đã thanh lý': abort(403)
        has_status = bool(cur.execute("SELECT CASE WHEN COL_LENGTH('dbo.DANH_MUC_THIET_BI','TrangThai') IS NOT NULL THEN 1 ELSE 0 END").fetchone()[0])
        if has_status:
            danhmuc = cur.execute("SELECT MaDanhMuc,TenDanhMuc FROM DANH_MUC_THIET_BI WHERE TrangThai=N'Đang sử dụng' OR MaDanhMuc=? ORDER BY TenDanhMuc", tb.MaDanhMuc).fetchall()
        else:
            danhmuc = cur.execute('SELECT MaDanhMuc,TenDanhMuc FROM DANH_MUC_THIET_BI ORDER BY TenDanhMuc').fetchall()
        phongban=cur.execute('SELECT MaPhongBan,TenPhongBan FROM PHONG_BAN').fetchall()
        if request.method=='POST':
            ten=request.form.get('ten','').strip()
            ngay=request.form.get('ngay','')
            dm=request.form.get('danhmuc','')
            pb=request.form.get('phongban','')
            if not all([ten,ngay,dm,pb]) or not ngay_hop_le(ngay) or dm not in [item.MaDanhMuc for item in danhmuc] or pb not in [item.MaPhongBan for item in phongban]:
                flash('Dữ liệu không hợp lệ.', 'danger')
            else:
                try:
                    cur.execute('''UPDATE THIET_BI SET TenThietBi=?,SerialNumber=?,NgayMua=?,ViTri=?,MaDanhMuc=?,MaPhongBan=?
                                   WHERE MaThietBi=?''',ten,request.form.get('serial',''),ngay,
                                request.form.get('vitri',''),dm,pb,ma)
                    conn.commit()
                    flash('Đã cập nhật thiết bị.','success')
                    return redirect(url_for('thietbi.danh_sach'))
                except pyodbc.IntegrityError:
                    conn.rollback()
                    flash('Danh mục hoặc phòng ban không hợp lệ.','danger')
    return render_template('thietbi_form.html',danhmuc=danhmuc,phongban=phongban,tb=tb)

@thietbi_bp.post('/<ma>/doi-trang-thai')
def doi_trang_thai(ma):
    trangthai=request.form.get('trangthai')
    if trangthai not in ('Ngừng hoạt động','Đang hoạt động'):
        abort(400)
    with get_db_connection() as conn:
        cur=conn.cursor()
        tb=cur.execute('SELECT TrangThai FROM THIET_BI WHERE MaThietBi=?',ma).fetchone()
        if not tb: abort(404)
        if tb.TrangThai=='Đã thanh lý': abort(403)
        if trangthai=='Đang hoạt động' and tb.TrangThai!='Ngừng hoạt động': abort(400)
        if trangthai=='Đang hoạt động':
            dang_mo = cur.execute("SELECT COUNT(*) FROM PHIEU_BAO_TRI WHERE MaThietBi=? AND TrangThai<>N'Đã đóng'", ma).fetchone()[0]
            if dang_mo:
                flash('Thiết bị còn phiếu bảo trì đang mở, không thể đánh dấu đang hoạt động.', 'warning')
                return redirect(url_for('thietbi.danh_sach'))
        if trangthai=='Ngừng hoạt động' and tb.TrangThai=='Ngừng hoạt động': abort(400)
        cur.execute('UPDATE THIET_BI SET TrangThai=? WHERE MaThietBi=?',trangthai,ma)
        conn.commit()
    flash('Đã cập nhật trạng thái thiết bị.','success')
    return redirect(url_for('thietbi.danh_sach'))

@thietbi_bp.get('/<ma>')
def chi_tiet(ma):
    with get_db_connection() as conn:
        cur=conn.cursor()
        tb=cur.execute('SELECT * FROM THIET_BI WHERE MaThietBi=?',ma).fetchone()
        if not tb: abort(404)
        phieu=cur.execute('SELECT * FROM PHIEU_BAO_TRI WHERE MaThietBi=? ORDER BY NgayTao DESC',ma).fetchall()
    return render_template('thietbi_chitiet.html',tb=tb,phieu=phieu)
