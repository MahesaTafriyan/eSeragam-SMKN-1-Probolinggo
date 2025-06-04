from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta, datetime

# Configuration Constants
CONFIG = {
    'SECRET_KEY': 'your-secret-key-here',  # Change to a strong secret key
    'DATA_FILE': "data_seragam_gui.json",
    'ADMIN_USERNAME': "admin",
    'ADMIN_PASSWORD': "admin123",  # Change this password
    'SESSION_TIMEOUT': timedelta(minutes=30),
    'ITEMS': {
        'male': {
            "Baju Seragam Abu-abu": 75000,
            "Baju Seragam Pramuka": 90000,
            "Baju Seragam Khas": 85000,
            "Baju Seragam Olahraga": 80000,
            "Kain Bawahan Hitam": 65000,
            "Kain Bawahan Batik": 65000,
            "Jas Almamater": 120000,
            "Dasi Hitam": 20000,
            "Dasi Abu-Abu": 20000,
            "Topi Abu-Abu": 15000,
            "Topi Merah": 15000,
            "Ikat Pinggang / Sabuk": 20000,
            "Nama Dada (ND)": 15000,
            "Bed Osis": 30000,
            "Bed Jurusan": 30000,
            "Bed Bendera": 30000,
            "Bed Bowolaksono": 30000,
            "Kaos Kaki Hitam": 10000,
            "Kaos Kaki Putih": 10000
        },
        'female': {
            "Jilbab Putih": 20000,
            "Jilbab Coklat": 20000,
            "Jilbab Batik": 25000,
            "Jilbab Khas": 25000,
            "Jilbab Hitam": 20000
        }
    },
    'CLASSES': [
        "X RPL 1", "X RPL 2",
        "X MP 1", "X MP 2", "X MP 3",
        "X BD 1", "X BD 2", "X BD 3", "X BD 4",
        "X LP 1", "X LP 2", "X LP 3",
        "X AK 1", "X AK 2"
    ]
}

app = Flask(__name__)
app.secret_key = CONFIG['SECRET_KEY']
app.permanent_session_lifetime = CONFIG['SESSION_TIMEOUT']

# Pre-calculate all items
CONFIG['ITEMS']['all'] = {**CONFIG['ITEMS']['male'], **CONFIG['ITEMS']['female']}
ADMIN_PASSWORD_HASH = generate_password_hash(CONFIG['ADMIN_PASSWORD'])

# Helper Functions
def load_data():
    """Load student data from JSON file"""
    if os.path.exists(CONFIG['DATA_FILE']):
        with open(CONFIG['DATA_FILE'], "r", encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(data):
    """Save student data to JSON file"""
    with open(CONFIG['DATA_FILE'], "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def calculate_purchase(items_to_check, form_data):
    """Calculate purchase items and total"""
    purchase = {}
    total = 0
    
    for item in items_to_check:
        try:
            quantity = int(form_data.get(item, '0'))
            if quantity > 0:
                price = items_to_check[item]
                item_total = quantity * price
                purchase[item] = {
                    "jumlah": quantity,
                    "harga_satuan": price,
                    "total": item_total
                }
                total += item_total
        except ValueError:
            continue
            
    return purchase, total

# Custom Filters
@app.template_filter('format_currency')
def format_currency(value):
    """Format number as Indonesian currency"""
    return f"Rp{value:,.0f}".replace(',', '.')

@app.template_filter('highlight_search')
def highlight_search(text, query):
    """Highlight search query in text"""
    if not query:
        return text
    return text.replace(query, f'<span class="search-highlight">{query}</span>')

# Authentication Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Anda harus login sebagai admin untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == CONFIG['ADMIN_USERNAME'] and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.permanent = True
            session['admin_logged_in'] = True
            flash('Login berhasil!', 'success')
            return redirect(request.args.get('next') or url_for('index'))
        flash('Username atau password salah!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('index'))

@app.route('/')
def index():
    search_query = request.args.get('search', '').lower()
    gender_filter = request.args.get('jenis_kelamin', '')
    name_query = request.args.get('nama', '').lower()
    class_query = request.args.get('kelas', '').lower()
    
    students = load_data()
    
    # Apply filters
    filtered_students = [
        s for s in students 
        if (not search_query or search_query in s['nama'].lower()) and
           (not gender_filter or s['jenis_kelamin'] == gender_filter) and
           (not name_query or name_query in s['nama'].lower()) and
           (not class_query or class_query in s['kelas'].lower())
    ]
    
    # Group by class
    students_by_class = {}
    for student in filtered_students:
        class_name = student['kelas']
        students_by_class.setdefault(class_name, []).append(student)
    
    # Order classes according to CONFIG['CLASSES']
    ordered_classes = sorted(
        students_by_class.keys(),
        key=lambda x: CONFIG['CLASSES'].index(x) if x in CONFIG['CLASSES'] else len(CONFIG['CLASSES'])
    )
    
    # Determine items to display
    items_to_display = (
        CONFIG['ITEMS']['male'] if gender_filter == 'Laki-laki' else 
        CONFIG['ITEMS']['all']
    )
    
    current_year = datetime.now().year  # Get the current year
    
    return render_template(
        'index.html',
        barang=items_to_display,
        barang_laki=CONFIG['ITEMS']['male'],
        barang_perempuan=CONFIG['ITEMS']['female'],
        barang_all=CONFIG['ITEMS']['all'],
        kelas_opsi=CONFIG['CLASSES'],
        data_siswa=filtered_students,
        siswa_per_kelas=students_by_class,
        ordered_kelas=ordered_classes,
        jenis_kelamin_terpilih=gender_filter,
        nama_query=name_query,
        kelas_query=class_query,
        search_query=search_query,
        is_admin=session.get('admin_logged_in'),
        current_year=current_year  # Pass the current year to the template
    )

@app.route('/tambah', methods=['POST'])
@admin_required
def tambah_data():
    try:
        name = request.form['nama'].strip()
        class_name = request.form['kelas']
        gender = request.form['jenis_kelamin']
        
        items_to_check = CONFIG['ITEMS']['male'] if gender == 'Laki-laki' else CONFIG['ITEMS']['all']
        purchase, total = calculate_purchase(items_to_check, request.form)
        
        if not purchase:
            flash('Minimal pilih 1 barang', 'warning')
            return redirect(url_for('index'))
        
        students = load_data()
        students.append({
            "id": str(uuid.uuid4()),
            "nama": name,
            "kelas": class_name,
            "jenis_kelamin": gender,
            "pembelian": purchase,
            "total_bayar": total
        })
        
        save_data(students)
        flash('Data berhasil ditambahkan!', 'success')
    except Exception as e:
        app.logger.error(f"Error adding data: {str(e)}")
        flash('Gagal menambahkan data', 'danger')
    
    return redirect(url_for('index'))

@app.route('/hapus/<string:student_id>', methods=['POST'])
@admin_required
def hapus_data(student_id):
    try:
        students = load_data()
        updated_students = [s for s in students if s['id'] != student_id]
        
        if len(updated_students) < len(students):
            save_data(updated_students)
            flash('Data berhasil dihapus!', 'success')
        else:
            flash('Data tidak ditemukan', 'warning')
    except Exception as e:
        app.logger.error(f"Error deleting data: {str(e)}")
        flash('Terjadi kesalahan saat menghapus data', 'danger')
    
    # Redirect to the index page after deletion
    return redirect(url_for('index'))

@app.route('/edit/<string:student_id>', methods=['GET', 'POST'])
@admin_required
def edit_data(student_id):
    students = load_data()
    student = next((s for s in students if s['id'] == student_id), None)
    
    if not student:
        flash('Data tidak ditemukan', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            name = request.form['nama'].strip()
            class_name = request.form['kelas']
            gender = request.form['jenis_kelamin']
            
            items_to_check = CONFIG['ITEMS']['male'] if gender == 'Laki-laki' else CONFIG['ITEMS']['all']
            purchase, total = calculate_purchase(items_to_check, request.form)
            
            if not purchase:
                flash('Minimal pilih 1 barang', 'warning')
                return redirect(url_for('edit_data', student_id=student_id))
            
            # Update student data
            student.update({
                "nama": name,
                "kelas": class_name,
                "jenis_kelamin": gender,
                "pembelian": purchase,
                "total_bayar": total
            })
            
            save_data(students)
            flash('Data berhasil diperbarui!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error editing data: {str(e)}")
            flash('Gagal memperbarui data', 'danger')
    
    # GET request - show edit form
    return render_template(
        'edit.html',
        siswa=student,
        id=student_id,
        barang_laki=CONFIG['ITEMS']['male'],
        barang_perempuan=CONFIG['ITEMS']['female'],
        barang_all=CONFIG['ITEMS']['all'],
        kelas_opsi=CONFIG['CLASSES']
    )

# Cache control
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
