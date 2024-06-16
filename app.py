import os
from flask import Flask, request, render_template, session, redirect, url_for
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from functools import wraps
import threading
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = '08001002653'  # Digunakan untuk mengenkripsi data sesi

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'database'

# Konfigurasi direktori upload
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024  # Batas ukuran file 16MB

mysql = MySQL(app)

# Fungsi untuk memasukkan data tamu ke dalam database
def input_tamu(nama):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO tamu (nama) VALUES (%s)", (nama,))
        mysql.connection.commit()
        cursor.close()
        return True
    except Exception as e:
        print("Error:", e)
        return False

# Fungsi decorator untuk memeriksa apakah pengguna sudah login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Halaman utama / home
@app.route("/", methods=['GET', 'POST'])
def home():
    # Cek sesi
    if 'username' in session:
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        nama = request.form['nama']
        if input_tamu(nama):
            return render_template('index.html', error=error, nama=nama)
        else:
            error = 'Gagal memasukkan data tamu'

    return render_template('index.html', error=error)

# Halaman buku
@app.route('/buku')
def daftar_buku():
    search = request.args.get('search')
    if search:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM buku WHERE judul LIKE %s", ('%' + search + '%',))
        bukus = cursor.fetchall()
        cursor.close()
    else:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM buku")
        bukus = cursor.fetchall()
        cursor.close()
    return render_template('buku.html', bukus=bukus, search=search)

@app.route('/buku/<int:id>')
def detail_buku(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM buku WHERE id = %s", (id,))
    buku = cursor.fetchone()
    cursor.close()
    if buku:
        return render_template('detail_buku.html', buku=buku)
    else:
        return "Buku tidak ditemukan", 404

# Halaman login
@app.route("/login", methods=['GET', 'POST'])
def login():
    # Cek sesi
    if 'username' in session:
        return redirect(url_for('dashboard'))

    error = None
    # Proses login
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM pengurus WHERE username=%s AND password=%s", (username, password,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Username atau password salah'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Dashboard home
@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    # Search
    if request.args.get('search', ''):
        search = request.args.get('search', '')
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM buku WHERE judul LIKE %s", ('%' + search + '%',))
        bukus = cursor.fetchall()
        cursor.close()
        return render_template('dashboard/buku/index.html', bukus=bukus, search=search)

    # Ambil semua buku
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM buku")
    bukus = cursor.fetchall()
    cursor.close()
    return render_template('dashboard/buku/index.html', bukus=bukus)

# Dashboard tambah buku
@app.route("/dashboard/tambah-buku", methods=['GET', 'POST'])
@login_required
def tambah_buku():
    error = None
    if request.method == 'POST':
        judul = request.form['judul']
        tahun_terbit = str(request.form['tahun_terbit'])
        sinopsis = request.form['sinopsis']
        penerbit = request.form['penerbit']
        lokasi = request.form['lokasi']
        jumlah = request.form['jumlah']
        cover = request.files['cover']

        if cover and allowed_file(cover.filename):
            filename = secure_filename(cover.filename)
            cover.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Insert data
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO buku (judul, tahun_terbit, sinopsis, penerbit, lokasi, total_stok, stok_terkini, cover) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                           (judul, tahun_terbit, sinopsis, penerbit, lokasi, jumlah, jumlah, filename))
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('dashboard'))
        else:
            error = 'Cover buku wajib diunggah dan harus dalam format yang diperbolehkan.'

    return render_template('dashboard/buku/tambah.html', error=error)

# Fungsi untuk memeriksa ekstensi file yang diunggah
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Dashboard edit buku
@app.route("/dashboard/buku/edit/<int:id>", methods=['GET', 'POST'])
@login_required
def edit_buku(id):
    error = None
    if request.method == 'POST':
        judul = request.form['judul']
        tahun_terbit = str(request.form['tahun_terbit'])
        sinopsis = request.form['sinopsis']
        penerbit = request.form['penerbit']
        lokasi = request.form['lokasi']
        jumlah = request.form['jumlah']
        jumlah_terkini = request.form['jumlah_terkini']
        cover = request.files['cover']

        if cover and allowed_file(cover.filename):
            filename = secure_filename(cover.filename)
            cover.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Update data
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE buku SET judul=%s, tahun_terbit=%s, sinopsis=%s, penerbit=%s, lokasi=%s, total_stok=%s, stok_terkini=%s, cover=%s WHERE id=%s",
                           (judul, tahun_terbit, sinopsis, penerbit, lokasi, jumlah, jumlah_terkini, filename, id))
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('dashboard'))
        else:
            # Update data tanpa mengubah cover
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE buku SET judul=%s, tahun_terbit=%s, sinopsis=%s, penerbit=%s, lokasi=%s, total_stok=%s, stok_terkini=%s WHERE id=%s",
                           (judul, tahun_terbit, sinopsis, penerbit, lokasi, jumlah, jumlah_terkini, id))
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('dashboard'))

    # Ambil buku
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM buku WHERE id=%s", (id,))
    buku = cursor.fetchone()
    cursor.close()
    return render_template('dashboard/buku/edit.html', buku=buku, error=error)

# Dashboard hapus buku
@app.route("/dashboard/buku/hapus/<int:id>", methods=['GET', 'POST'])
@login_required
def hapus_buku(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM buku WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('dashboard'))

# Dashboard tambah peminjaman
@app.route("/dashboard/peminjaman/tambah", methods=['GET','POST'])
@login_required
def peminjaman_tambah():
    if request.method == 'POST':
        id_buku = request.form['id_buku']
        nik = request.form['nik']
        tgl = datetime.now().strftime('%Y-%m-%d')
        date_1 = datetime.strptime(tgl, '%Y-%m-%d')
        tgl_jatuh_tempo = date_1 + timedelta(days=7)

        # Insert data
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO peminjaman (tgl, tgl_jatuh_tempo, nik_anggota, id_buku ) VALUES (%s, %s, %s, %s)", (tgl, tgl_jatuh_tempo, nik, id_buku,))
        mysql.connection.commit()

        # Update stok buku
        cursor.execute("UPDATE buku SET stok_terkini=stok_terkini-1 WHERE id=%s", (id_buku,))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('peminjaman'))

    # Ambil semua buku
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM buku")
    bukus = cursor.fetchall()
    # Ambil semua anggota
    cursor.execute("SELECT * FROM anggota")
    anggotas = cursor.fetchall()
    cursor.close()
    return render_template('dashboard/peminjaman/tambah.html', bukus = bukus, anggotas=anggotas)

# Dashboard peminjaman
@app.route("/dashboard/peminjaman", methods=['GET','POST'])
@login_required
def peminjaman():
    # Ambil semua peminjaman dan gabungkan tabel
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT peminjaman.id, buku.judul, anggota.nama, peminjaman.nik_anggota, peminjaman.status,  peminjaman.tgl, peminjaman.tgl_jatuh_tempo FROM peminjaman INNER JOIN buku ON peminjaman.id_buku = buku.id INNER JOIN anggota ON peminjaman.nik_anggota = anggota.nik")
    peminjamans = cursor.fetchall()
    cursor.close()
    return render_template('dashboard/peminjaman/index.html', peminjamans=peminjamans)

# Dashboard edit peminjaman
@app.route("/dashboard/peminjaman/edit/<id>", methods=['GET','POST'])
@login_required
def peminjaman_edit(id):
    error = None
    if request.method == 'POST':
        status = request.form['status']
        id_buku = request.form['id_buku']

        # Insert data
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE peminjaman SET status=%s WHERE id=%s", (status,id,))
        mysql.connection.commit()
        
        if status == 'kembali':
            # Update stok buku
            cursor.execute("UPDATE buku SET stok_terkini=stok_terkini+1 WHERE id=%s", (id_buku,))
            mysql.connection.commit()
        elif status == 'dipinjam':
            # Update stok buku
            cursor.execute("UPDATE buku SET stok_terkini=stok_terkini-1 WHERE id=%s", (id_buku,))
            mysql.connection.commit()
        cursor.close()
        return redirect(url_for('peminjaman'))


    # Ambil peminjaman dan gabungkan tabel
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT peminjaman.id, buku.judul, peminjaman.nik_anggota, peminjaman.status, buku.id FROM peminjaman INNER JOIN buku ON peminjaman.id_buku = buku.id WHERE peminjaman.id=%s", (id,))
    peminjaman = cursor.fetchone()
    cursor.close()
    return render_template('dashboard/peminjaman/edit.html', peminjaman=peminjaman, error=error)

# Dashboard tamu
@app.route("/dashboard/tamu", methods=['GET','POST'])
@login_required
def tamu():
    # Ambil semua tamu
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM tamu")
    tamus = cursor.fetchall()
    cursor.close()
    return render_template('dashboard/tamu/index.html', tamus=tamus)

# Dashboard anggota
@app.route("/dashboard/anggota", methods=['GET','POST'])
@login_required
def anggota():
    # Ambil semua anggota
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM anggota")
    anggotas = cursor.fetchall()
    cursor.close()
    return render_template('dashboard/anggota/index.html', anggotas=anggotas)

# Dashboard tambah anggota
@app.route("/dashboard/anggota/tambah", methods=['GET','POST'])
@login_required
def anggota_tambah():
    if request.method == 'POST':
        nik = request.form['nik']
        nama = request.form['nama']
        # Insert data
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO anggota (nik, nama) VALUES (%s, %s)", (nik, nama,))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('anggota'))
    return render_template('dashboard/anggota/tambah.html')

# Dashboard edit anggota
@app.route("/dashboard/anggota/edit/<nik>", methods=['GET','POST'])
@login_required
def anggota_edit(nik):
    if request.method == 'POST':
        nik_baru = request.form['nik']
        nama = request.form['nama']
        # Insert data
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE anggota SET nama=%s, nik=%s WHERE nik=%s", (nama, nik_baru, nik,))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('anggota'))
    # Ambil anggota
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM anggota WHERE nik=%s", (nik,))
    anggota = cursor.fetchone()
    cursor.close()
    return render_template('dashboard/anggota/edit.html', anggota=anggota)

# Logout
@app.route("/logout", methods=['GET','POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

def run_app():
    app.run(debug=True)

if __name__ == "__main__":
    # Menjalankan aplikasi dalam thread terpisah
    thread = threading.Thread(target=run_app)
    thread.start()