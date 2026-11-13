from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db_config import get_db_connection

baotri_bp = Blueprint('baotri', __name__, url_prefix='/bao-tri')
TRANG_THAI=['Yêu cầu mới','Đã duyệt','Đang tiến hành','Đã hoàn thành','Đã đóng']

@baotri_bp.get('/')
def danh_sach():
    loc = request.args.get('trangthai', '').strip()
    if loc not in TRANG_THAI: loc = ''
    with get_db_connection() as conn:
        rows=conn.cursor().execute('''SELECT p.*,tb.TenThietBi,nd.HoTen AS TenNguoiYeuCau,
                      kt.HoTen AS TenKyThuatVien FROM PHIEU_BAO_TRI p
                      JOIN THIET_BI tb ON p.MaThietBi=tb.MaThietBi
                      JOIN NGUOI_DUNG nd ON p.MaNguoiYeuCau=nd.MaNguoiDung
                      LEFT JOIN NGUOI_DUNG kt ON p.MaKyThuatVien=kt.MaNguoiDung
                      WHERE (? = '' OR p.TrangThai = ?)
                      ORDER BY p.NgayTao DESC, p.MaPhieu DESC''', loc, loc).fetchall()
    return render_template('baotri.html',rows=rows, loc=loc, trangthai=TRANG_THAI)

@baotri_bp.route('/them',methods=['GET','POST'])
def them():
    with get_db_connection() as conn:
        cur=conn.cursor()
        thietbi=cur.execute("SELECT MaThietBi,TenThietBi FROM THIET_BI WHERE TrangThai IN (N'Đang hoạt động',N'Đang hỏng')").fetchall()
        nhanvien=cur.execute("SELECT MaNguoiDung,HoTen FROM NGUOI_DUNG WHERE VaiTro=N'Nhân viên'").fetchall()
        if request.method=='POST':
            ma=request.form.get('thietbi','')
            nguoi=request.form.get('nguoi','')
            mota=request.form.get('mota','').strip()
            uutien=request.form.get('uutien','Trung bình')
            if (not mota or uutien not in ('Thấp','Trung bình','Cao') or
                ma not in [x.MaThietBi for x in thietbi] or nguoi not in [x.MaNguoiDung for x in nhanvien]):
                flash('Kiểm tra lại thiết bị, người yêu cầu, mức ưu tiên và mô tả lỗi.','danger')
            else:
                dang_mo = cur.execute("SELECT COUNT(*) FROM PHIEU_BAO_TRI WHERE MaThietBi=? AND TrangThai<>N'Đã đóng'", ma).fetchone()[0]
                if dang_mo:
                    flash('Thiết bị đã có phiếu bảo trì chưa đóng.', 'warning')
                    return render_template('baotri_form.html', thietbi=thietbi, nhanvien=nhanvien)
                cur.execute('INSERT INTO PHIEU_BAO_TRI (MaThietBi,MaNguoiYeuCau,MoTaLoi,MucDoUuTien) VALUES (?,?,?,?)',ma,nguoi,mota,uutien)
                cur.execute("UPDATE THIET_BI SET TrangThai=N'Đang hỏng' WHERE MaThietBi=?",ma)
                conn.commit()
                flash('Đã lập phiếu bảo trì.','success')
                return redirect(url_for('baotri.danh_sach'))
    return render_template('baotri_form.html',thietbi=thietbi,nhanvien=nhanvien)

@baotri_bp.route('/<int:ma>/xu-ly',methods=['GET','POST'])
def xu_ly(ma):
    with get_db_connection() as conn:
        cur=conn.cursor()
        phieu=cur.execute('SELECT * FROM PHIEU_BAO_TRI WHERE MaPhieu=?',ma).fetchone()
        if not phieu: abort(404)
        kythuat=cur.execute("SELECT MaNguoiDung,HoTen FROM NGUOI_DUNG WHERE VaiTro=N'Kỹ thuật viên'").fetchall()
        if request.method=='POST':
            moi=request.form.get('trangthai')
            kt=request.form.get('kythuat') or None
            ketqua=request.form.get('ketqua','').strip()
            valid_next={'Yêu cầu mới':'Đã duyệt','Đã duyệt':'Đang tiến hành',
                        'Đang tiến hành':'Đã hoàn thành','Đã hoàn thành':'Đã đóng'}
            if moi!=valid_next.get(phieu.TrangThai):
                flash('Chỉ được chuyển phiếu sang trạng thái kế tiếp.','danger')
            elif moi in ('Đã duyệt','Đang tiến hành') and kt not in [x.MaNguoiDung for x in kythuat]:
                flash('Hãy chọn kỹ thuật viên.','danger')
            elif moi in ('Đã hoàn thành','Đã đóng') and not (ketqua or phieu.KetQua):
                flash('Phải nhập kết quả xử lý trước khi hoàn thành.','danger')
            elif moi in ('Đang tiến hành','Đã hoàn thành','Đã đóng') and not (kt or phieu.MaKyThuatVien):
                flash('Phiếu cần có kỹ thuật viên phụ trách.', 'danger')
            else:
                cur.execute('UPDATE PHIEU_BAO_TRI SET TrangThai=?,MaKyThuatVien=?,KetQua=? WHERE MaPhieu=?',
                            moi,kt or phieu.MaKyThuatVien,ketqua or phieu.KetQua,ma)
                if moi=='Đã đóng':
                    # Chỉ trả thiết bị về hoạt động nếu không còn phiếu mở khác.
                    count=cur.execute("SELECT COUNT(*) FROM PHIEU_BAO_TRI WHERE MaThietBi=? AND MaPhieu<>? AND TrangThai<>N'Đã đóng'",phieu.MaThietBi,ma).fetchone()[0]
                    if count==0:
                        cur.execute("UPDATE THIET_BI SET TrangThai=N'Đang hoạt động' WHERE MaThietBi=? AND TrangThai=N'Đang hỏng'",phieu.MaThietBi)
                conn.commit()
                flash('Cập nhật phiếu thành công.','success')
                return redirect(url_for('baotri.danh_sach'))
    return render_template('baotri_xuly.html',phieu=phieu,kythuat=kythuat,trangthai=TRANG_THAI)
