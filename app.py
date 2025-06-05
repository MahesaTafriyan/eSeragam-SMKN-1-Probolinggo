from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta, datetime

class BaseSystem:
    def __init__(self, config):
        self.config = config
        
    def load_data(self):
        if os.path.exists(self.config['DATA_FILE']):
            with open(self.config['DATA_FILE'], "r", encoding='utf-8') as f:
                return json.load(f)
        return []

    def save_data(self, data):
        with open(self.config['DATA_FILE'], "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

class SchoolUniformSystem(BaseSystem):
    def __init__(self):
        config = {
            'SECRET_KEY': 'your-secret-key-here',
            'DATA_FILE': "data_seragam_gui.json",
            'ADMIN_USERNAME': "admin",
            'ADMIN_PASSWORD': "admin123",
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
        config['ITEMS']['all'] = {**config['ITEMS']['male'], **config['ITEMS']['female']}
        super().__init__(config)
        self.admin_password_hash = generate_password_hash(self.config['ADMIN_PASSWORD'])

    def calculate_purchase(self, items_to_check, form_data):
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

class BaseStudent:
    def __init__(self, name, class_name, gender):
        self.id = str(uuid.uuid4())
        self.name = name
        self.class_name = class_name
        self.gender = gender

    def to_dict(self):
        return {
            "id": self.id,
            "nama": self.name,
            "kelas": self.class_name,
            "jenis_kelamin": self.gender
        }

class UniformStudent(BaseStudent):
    def __init__(self, name, class_name, gender, items_data):
        super().__init__(name, class_name, gender)
        self.purchase, self.total = items_data

    def to_dict(self):
        base_dict = super().to_dict()
        base_dict.update({
            "pembelian": self.purchase,
            "total_bayar": self.total
        })
        return base_dict

class BaseAppFactory:
    def __init__(self, system):
        self.app = Flask(__name__)
        self.system = system
        self.setup_app()

    def setup_app(self):
        self.app.secret_key = self.system.config['SECRET_KEY']
        self.app.permanent_session_lifetime = self.system.config['SESSION_TIMEOUT']
        
        # Register filters
        self.app.template_filter('format_currency')(self.format_currency)
        self.app.template_filter('highlight_search')(self.highlight_search)
        
        # Add after_request handler
        self.app.after_request(self.add_header)

    # Helper methods
    def format_currency(self, value):
        return f"Rp{value:,.0f}".replace(',', '.')

    def highlight_search(self, text, query):
        if not query:
            return text
        return text.replace(query, f'<span class="search-highlight">{query}</span>')

    def add_header(self, response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

class SchoolUniformAppFactory(BaseAppFactory):
    def __init__(self):
        system = SchoolUniformSystem()
        super().__init__(system)
        self.setup_routes()

    def setup_routes(self):
        self.app.route('/')(self.index)
        self.app.route('/login', methods=['GET', 'POST'])(self.login)
        self.app.route('/logout')(self.logout)
        self.app.route('/tambah', methods=['POST'])(self.tambah_data)
        self.app.route('/hapus/<string:student_id>', methods=['POST'])(self.hapus_data)
        self.app.route('/edit/<string:student_id>', methods=['GET', 'POST'])(self.edit_data)

    def admin_required(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('admin_logged_in'):
                flash('Anda harus login sebagai admin untuk mengakses halaman ini.', 'danger')
                return redirect(url_for('login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function

    # Route handlers
    def login(self):
        if session.get('admin_logged_in'):
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if username == self.system.config['ADMIN_USERNAME'] and check_password_hash(
                self.system.admin_password_hash, password):
                session.permanent = True
                session['admin_logged_in'] = True
                flash('Login berhasil!', 'success')
                return redirect(request.args.get('next') or url_for('index'))
            flash('Username atau password salah!', 'danger')
        
        return render_template('login.html')

    def logout(self):
        session.clear()
        flash('Anda telah logout.', 'info')
        return redirect(url_for('index'))

    def index(self):
        search_query = request.args.get('search', '').lower()
        gender_filter = request.args.get('jenis_kelamin', '')
        name_query = request.args.get('nama', '').lower()
        class_query = request.args.get('kelas', '').lower()
        
        students = self.system.load_data()
        
        filtered_students = [
            s for s in students 
            if (not search_query or search_query in s['nama'].lower()) and
               (not gender_filter or s['jenis_kelamin'] == gender_filter) and
               (not name_query or name_query in s['nama'].lower()) and
               (not class_query or class_query in s['kelas'].lower())
        ]
        
        students_by_class = {}
        for student in filtered_students:
            class_name = student['kelas']
            students_by_class.setdefault(class_name, []).append(student)
        
        ordered_classes = sorted(
            students_by_class.keys(),
            key=lambda x: self.system.config['CLASSES'].index(x) if x in self.system.config['CLASSES'] 
                          else len(self.system.config['CLASSES'])
        )
        
        items_to_display = (
            self.system.config['ITEMS']['male'] if gender_filter == 'Laki-laki' 
            else self.system.config['ITEMS']['all']
        )
        
        current_year = datetime.now().year
        
        return render_template(
            'index.html',
            barang=items_to_display,
            barang_laki=self.system.config['ITEMS']['male'],
            barang_perempuan=self.system.config['ITEMS']['female'],
            barang_all=self.system.config['ITEMS']['all'],
            kelas_opsi=self.system.config['CLASSES'],
            data_siswa=filtered_students,
            siswa_per_kelas=students_by_class,
            ordered_kelas=ordered_classes,
            jenis_kelamin_terpilih=gender_filter,
            nama_query=name_query,
            kelas_query=class_query,
            search_query=search_query,
            is_admin=session.get('admin_logged_in'),
            current_year=current_year
        )

    def tambah_data(self):
        try:
            name = request.form['nama'].strip()
            class_name = request.form['kelas']
            gender = request.form['jenis_kelamin']
            
            items_to_check = (
                self.system.config['ITEMS']['male'] if gender == 'Laki-laki' 
                else self.system.config['ITEMS']['all']
            )
            purchase, total = self.system.calculate_purchase(items_to_check, request.form)
            
            if not purchase:
                flash('Minimal pilih 1 barang', 'warning')
                return redirect(url_for('index'))
            
            students = self.system.load_data()
            new_student = UniformStudent(name, class_name, gender, (purchase, total))
            students.append(new_student.to_dict())
            
            self.system.save_data(students)
            flash('Data berhasil ditambahkan!', 'success')
        except Exception as e:
            self.app.logger.error(f"Error adding data: {str(e)}")
            flash('Gagal menambahkan data', 'danger')
        
        return redirect(url_for('index'))

    def hapus_data(self, student_id):
        try:
            students = self.system.load_data()
            updated_students = [s for s in students if s['id'] != student_id]
            
            if len(updated_students) < len(students):
                self.system.save_data(updated_students)
                flash('Data berhasil dihapus!', 'success')
            else:
                flash('Data tidak ditemukan', 'warning')
        except Exception as e:
            self.app.logger.error(f"Error deleting data: {str(e)}")
            flash('Terjadi kesalahan saat menghapus data', 'danger')
        
        return redirect(url_for('index'))

    def edit_data(self, student_id):
        students = self.system.load_data()
        student = next((s for s in students if s['id'] == student_id), None)
        
        if not student:
            flash('Data tidak ditemukan', 'danger')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            try:
                name = request.form['nama'].strip()
                class_name = request.form['kelas']
                gender = request.form['jenis_kelamin']
                
                items_to_check = (
                    self.system.config['ITEMS']['male'] if gender == 'Laki-laki' 
                    else self.system.config['ITEMS']['all']
                )
                purchase, total = self.system.calculate_purchase(items_to_check, request.form)
                
                if not purchase:
                    flash('Minimal pilih 1 barang', 'warning')
                    return redirect(url_for('edit_data', student_id=student_id))
                
                student.update({
                    "nama": name,
                    "kelas": class_name,
                    "jenis_kelamin": gender,
                    "pembelian": purchase,
                    "total_bayar": total
                })
                
                self.system.save_data(students)
                flash('Data berhasil diperbarui!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                self.app.logger.error(f"Error editing data: {str(e)}")
                flash('Gagal memperbarui data', 'danger')
        
        return render_template(
            'edit.html',
            siswa=student,
            id=student_id,
            barang_laki=self.system.config['ITEMS']['male'],
            barang_perempuan=self.system.config['ITEMS']['female'],
            barang_all=self.system.config['ITEMS']['all'],
            kelas_opsi=self.system.config['CLASSES']
        )

    def run(self):
        self.app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == '__main__':
    app_factory = SchoolUniformAppFactory()
    app_factory.run()
