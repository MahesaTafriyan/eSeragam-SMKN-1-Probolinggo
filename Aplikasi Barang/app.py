from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a strong secret key

# Admin credentials (in a real app, store these in a database)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")  # Change this password

# Barang untuk laki-laki
barang_laki = {
    "Kain Bawahan Hitam": 65000,
    "Baju Seragam Khas": 85000,
    "Baju Seragam Abu-abu": 75000,
    "Baju Seragam Pramuka": 90000,
    "Baju Seragam Olahraga": 80000,
    "Topi Abu-Abu": 15000,
    "Topi Merah": 15000,
    "Dasi Hitam": 20000,
    "Dasi Abu-Abu": 20000,
    "Bed Jurusan": 30000,
    "Bed Bowolaksono": 30000,
    "Bed Bendera": 30000,
    "Bed Osis": 30000,
    "Jas Almamater": 120000,
    "Kaos Kaki Hitam": 10000,
    "Kaos Kaki Putih": 10000,
    "Ikat Pinggang / Sabuk": 20000,
    "Nama Dada (ND)": 15000,
    "Kain Bawahan Batik": 65000
}

# Barang untuk perempuan
barang_perempuan = {
    "Jilbab Putih": 20000,
    "Jilbab Coklat": 20000,
    "Jilbab Batik": 25000,
    "Jilbab Khas": 25000,
    "Jilbab Hitam": 20000
}

# Gabungkan barang untuk laki-laki dan perempuan
barang_all = {**barang_laki, **barang_perempuan}

kelas_opsi = [
    "X RPL 1", "X RPL 2",
    "X MP 1", "X MP 2", "X MP 3",
    "X BD 1", "X BD 2", "X BD 3", "X BD 4",
    "X LP 1", "X LP 2", "X LP 3",
    "X AK 1", "X AK 2"
]

file_data = "data_seragam_gui.json"

if os.path.exists(file_data):
    with open(file_data, "r") as f:
        data_siswa = json.load(f)
else:
    data_siswa = []

def simpan_data():
    with open(file_data, "w") as f:
        json.dump(data_siswa, f, indent=4)

# Custom filter to format numbers
@app.template_filter('format_currency')
def format_currency(value):
    return f"Rp{value:,.0f}".replace(',', '.')

# Login routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            flash('Login berhasil!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Username atau password salah!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('Anda telah logout.', 'info')
    return redirect(url_for('index'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Anda harus login sebagai admin untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    jenis_kelamin = request.args.get('jenis_kelamin', '')
    nama_query = request.args.get('nama', '')
    kelas_query = request.args.get('kelas', '')
    
    filtered_data_siswa = []

    if search_query:
        filtered_data_siswa = [siswa for siswa in data_siswa if search_query.lower() in siswa['nama'].lower()]
    else:
        filtered_data_siswa = data_siswa

    # Kelompokkan siswa berdasarkan kelas
    siswa_per_kelas = {}
    for siswa in filtered_data_siswa:
        kelas = siswa['kelas']
        if kelas not in siswa_per_kelas:
            siswa_per_kelas[kelas] = []
        siswa_per_kelas[kelas].append(siswa)

    # Urutkan kelas sesuai dengan kelas_opsi
    ordered_kelas = sorted(siswa_per_kelas.keys(), 
                         key=lambda x: kelas_opsi.index(x) if x in kelas_opsi else len(kelas_opsi))

    # Determine which items to show based on selected gender
    if jenis_kelamin == 'Laki-laki':
        barang_tampil = barang_laki
    elif jenis_kelamin == 'Perempuan':
        barang_tampil = {**barang_laki, **barang_perempuan}
    else:
        barang_tampil = {**barang_laki, **barang_perempuan}

    return render_template('index.html', 
                        barang=barang_tampil,
                        barang_laki=barang_laki,
                        barang_perempuan=barang_perempuan,
                        kelas_opsi=kelas_opsi, 
                        data_siswa=filtered_data_siswa,
                        siswa_per_kelas=siswa_per_kelas,
                        ordered_kelas=ordered_kelas,
                        jenis_kelamin_terpilih=jenis_kelamin,
                        nama_query=nama_query,
                        kelas_query=kelas_query,
                        search_query=search_query,
                        is_admin=session.get('admin_logged_in'))

@app.route('/tambah', methods=['POST'])
@admin_required
def tambah_data():
    try:
        nama = request.form['nama']
        kelas = request.form['kelas']
        jenis_kelamin = request.form['jenis_kelamin']
        pembelian = {}
        total_bayar = 0

        # Determine which items to check based on gender
        if jenis_kelamin == 'Laki-laki':
            items_to_check = barang_laki
        elif jenis_kelamin == 'Perempuan':
            items_to_check = {**barang_laki, **barang_perempuan}
        else:
            items_to_check = {**barang_laki, **barang_perempuan}

        for item in items_to_check:
            jumlah = request.form.get(item, '0')
            try:
                jumlah_int = int(jumlah)
            except ValueError:
                jumlah_int = 0
            if jumlah_int > 0:
                harga = items_to_check[item]
                total = jumlah_int * harga
                pembelian[item] = {
                    "jumlah": jumlah_int,
                    "harga_satuan": harga,
                    "total": total
                }
                total_bayar += total

        if pembelian:
            data_siswa.append({
                "nama": nama,
                "kelas": kelas,
                "jenis_kelamin": jenis_kelamin,
                "pembelian": pembelian,
                "total_bayar": total_bayar
            })
            simpan_data()
            flash('Data berhasil ditambahkan!', 'success')
    except Exception as e:
        print(f"Error saat menambah data: {e}")
        flash('Gagal menambahkan data', 'danger')
    return redirect(url_for('index'))

@app.route('/hapus/<int:index>', methods=['POST'])
@admin_required
def hapus_data(index):
    if 0 <= index < len(data_siswa):
        data_siswa.pop(index)
        simpan_data()
        flash('Data berhasil dihapus!', 'success')
    else:
        flash('Data tidak ditemukan', 'danger')
    return redirect(url_for('index'))

@app.route('/edit/<int:index>', methods=['POST'])
@admin_required
def edit_data(index):
    if 0 <= index < len(data_siswa):
        try:
            nama_baru = request.form['nama']
            kelas_baru = request.form['kelas']
            jenis_kelamin_baru = request.form['jenis_kelamin']
            pembelian_baru = {}
            total_bayar_baru = 0

            # Determine which items to check based on gender
            items_to_check = barang_laki  # Default to male items
            if jenis_kelamin_baru == 'Perempuan':
                items_to_check = {**barang_laki, **barang_perempuan}

            for item in items_to_check:
                jumlah = request.form.get(item, '0')
                try:
                    jumlah_int = int(jumlah)
                except ValueError:
                    jumlah_int = 0
                
                if jumlah_int > 0:
                    harga = items_to_check[item]
                    total = jumlah_int * harga
                    pembelian_baru[item] = {
                        "jumlah": jumlah_int,
                        "harga_satuan": harga,
                        "total": total
                    }
                    total_bayar_baru += total

            data_siswa[index] = {
                "nama": nama_baru,
                "kelas": kelas_baru,
                "jenis_kelamin": jenis_kelamin_baru,
                "pembelian": pembelian_baru,
                "total_bayar": total_bayar_baru
            }
            simpan_data()
            flash('Data berhasil diperbarui!', 'success')
        except Exception as e:
            print(f"Error saat mengedit data: {e}")
            flash('Gagal memperbarui data', 'danger')
    else:
        flash('Data tidak ditemukan', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)