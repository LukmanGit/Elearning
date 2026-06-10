# 🎓 PS Learning — Modul E-Learning untuk Odoo 17

[![Odoo](https://img.shields.io/badge/Odoo-17.0-714B67?logo=odoo&logoColor=white)](https://www.odoo.com)
[![Version](https://img.shields.io/badge/version-17.0.13.0.0-blue)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-green)](https://www.gnu.org/licenses/lgpl-3.0)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-supported-336791?logo=postgresql&logoColor=white)](#)

**PS Learning** adalah modul kustom Odoo 17 yang mengubah Odoo menjadi platform e-learning internal. Modul ini mengelola _course_, materi pembelajaran, serta evaluasi Pre-Test dan Post-Test dengan **alur belajar berurutan (sequential learning path)** — peserta tidak bisa melompati materi, dan materi berikutnya baru terbuka setelah rangkaian materi sebelumnya tuntas.

> Dibangun sebagai modul end-to-end: model & business logic (Python/ORM), halaman web peserta (QWeb + JavaScript), keamanan berbasis peran (RBAC), hingga skrip migrasi data.

---

## 📋 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Tangkapan Layar](#-tangkapan-layar)
- [Konsep Alur Belajar](#-konsep-alur-belajar)
- [Teknologi](#-teknologi)
- [Arsitektur & Model Data](#-arsitektur--model-data)
- [Instalasi](#-instalasi)
- [Cara Penggunaan](#-cara-penggunaan)
- [Hak Akses (RBAC)](#-hak-akses-rbac)
- [Struktur Direktori](#-struktur-direktori)
- [Catatan Teknis](#-catatan-teknis)
- [Lisensi](#-lisensi)
- [Penulis](#-penulis)

---

## ✨ Fitur Utama

- **Manajemen Course & Materi** — kelola course beserta materi multi-format: teks/artikel, dokumen, video (file atau URL embed), audio, dan presentasi.
- **Alur belajar berurutan** — setiap materi mengikuti pola **Pre-Test → Belajar → Post-Test**; materi berikutnya **terkunci** sampai rangkaian materi sebelumnya selesai.
- **Bank soal Pre-Test & Post-Test** — soal pilihan ganda dan esai, dengan bobot nilai dan kunci jawaban per soal.
- **Ujian online berbasis web** — dilengkapi **timer hitung mundur** dan **autosave** jawaban, sehingga jawaban tetap aman walau waktu habis atau koneksi terputus (saat waktu habis, jawaban otomatis dikumpulkan).
- **Pelacakan progress otomatis** — persentase kemajuan dihitung dari setiap langkah (pre-test, belajar, post-test) di seluruh materi.
- **Report hasil belajar** — perbandingan **Pre-Test vs Post-Test** beserta **peningkatan (improvement)**, lengkap dan dapat dicetak/diekspor PDF.
- **Workflow status** — alur publikasi course: `Draft → Segera Datang → Dipublikasi → Arsip`, dengan validasi prasyarat sebelum publikasi.
- **Hak akses berbasis peran (RBAC)** — pemisahan tegas antara **Peserta** dan **Admin/Pengajar**.
- **Pengaturan tampilan login** — opsi menyembunyikan header/footer pada halaman login untuk tampilan yang lebih fokus.

---

## 📸 Tangkapan Layar

> Simpan gambar di folder `docs/screenshots/` lalu sesuaikan nama file di bawah.

### Halaman Jalur Belajar (Peserta)
Alur Pre-Test → Belajar → Post-Test dengan penguncian materi berurutan.

![Halaman Belajar](docs/screenshots/learn-path.png)

### Form Test & Bank Soal (Admin)
Penyusunan soal dengan materi terkait yang terisi otomatis.

![Form Test](docs/screenshots/test-form.png)

### Dashboard Belajar & Report
Pelacakan progress dan perbandingan Pre-Test vs Post-Test.

![Report](docs/screenshots/report.png)

---

## 🔄 Konsep Alur Belajar

Inti dari modul ini adalah **sequential learning path** yang dikelola per materi:

```
Course
 └── Materi 1  [Berlangsung]
 │     ├── 1. Pre-Test      → wajib dikerjakan untuk membuka materi
 │     ├── 2. Belajar       → terbuka setelah Pre-Test selesai
 │     └── 3. Post-Test     → terbuka setelah materi ditandai selesai
 │
 └── Materi 2  [🔒 Terkunci] → terbuka setelah seluruh rangkaian Materi 1 tuntas
       └── ...
```

Setiap langkah memengaruhi perhitungan progress. Saat seluruh materi tuntas (100%), status pendaftaran otomatis menjadi **Selesai** dan report dapat diakses.

---

## 🛠 Teknologi

| Lapisan | Teknologi |
|---|---|
| Framework | Odoo 17 (ORM, QWeb server-side templating) |
| Backend | Python 3.10+ |
| Frontend | JavaScript (vanilla), Bootstrap 5, Font Awesome |
| Basis data | PostgreSQL |
| Dependensi Odoo | `base`, `web`, `mail`, `website` |

Modul **tidak** membutuhkan pustaka pip tambahan di luar bawaan Odoo.

---

## 🧩 Arsitektur & Model Data

Modul terdiri dari 8 model utama:

| Model | Keterangan |
|---|---|
| `pslearning.course` | Course / mata pelajaran |
| `pslearning.material` | Materi dalam course (+ Pre/Post-Test per materi) |
| `pslearning.test` | Test (Pre-Test / Post-Test) |
| `pslearning.question` | Soal di dalam test |
| `pslearning.answer` | Pilihan jawaban soal |
| `pslearning.enrollment` | Pendaftaran peserta + mesin progress & learning path |
| `pslearning.test.attempt` | Percobaan pengerjaan test (timer & penilaian) |
| `pslearning.attempt.answer` | Jawaban peserta per soal pada satu percobaan |

Relasi inti: `Course 1—N Material`, `Course 1—N Test`, `Test 1—N Question 1—N Answer`, `Enrollment 1—N Attempt 1—N AttemptAnswer`. Setiap pendaftaran bersifat unik per `(peserta, course)`.

---

## 🚀 Instalasi

### 1. Clone repository ke folder addons Anda

```bash
cd /path/ke/odoo/addons      # folder yang masuk addons_path
git clone https://github.com/LukmanGit/Elearning.git
```

Pastikan `addons_path` pada `odoo.conf` menunjuk ke folder yang **berisi** `pslearning`:

```ini
addons_path = /opt/odoo/odoo/addons,/path/ke/odoo/addons/Elearning
```

### 2. Restart Odoo & install modul

**Via UI (mode developer):**
> Apps → *Update Apps List* → cari **PS Learning** → **Install**

**Via command line:**

```bash
# Instalasi pertama kali
./odoo-bin -c /etc/odoo/odoo.conf -d NAMA_DB -i pslearning --stop-after-init

# Upgrade ke versi terbaru (menjalankan migration)
./odoo-bin -c /etc/odoo/odoo.conf -d NAMA_DB -u pslearning --stop-after-init
```

> ⚠️ **Lakukan backup database + filestore sebelum upgrade**, karena modul menyertakan skrip migrasi yang menyesuaikan data.

---

## 📖 Cara Penggunaan

### Untuk Admin / Pengajar

1. Buat **Course** (kode otomatis tergenerate) dan isi deskripsi.
2. Tambahkan **Materi** secara berurutan dan tetapkan durasi.
3. Buat **Test** (tombol _Buat Test_ dari materi mengisi nama, course, & materi otomatis), tambahkan soal + jawaban, lalu publikasikan.
4. Tetapkan Pre-Test/Post-Test pada materi, lalu **publikasikan materi**.
5. **Publikasikan Course** — hanya berhasil bila seluruh prasyarat terpenuhi.

### Untuk Peserta

1. Buka katalog course → **Daftar**.
2. Mulai belajar → kerjakan **Pre-Test** untuk membuka materi.
3. Pelajari materi → tandai **Selesai**.
4. Kerjakan **Post-Test**. Materi berikutnya akan terbuka otomatis.
5. Setelah 100%, lihat & cetak **Report** hasil belajar.

---

## 🔐 Hak Akses (RBAC)

| Grup | Peran | Kewenangan |
|---|---|---|
| `group_pslearning_participant` | Peserta | Mendaftar, mengerjakan test, belajar, melihat hasil sendiri (hanya baca pada course/materi/test) |
| `group_pslearning_manager` | Admin / Pengajar | Akses penuh (CRUD) atas seluruh data; mewarisi akses Peserta |

Dilengkapi _record rules_ yang memastikan peserta hanya dapat mengakses pendaftaran dan percobaan miliknya sendiri.

---

## 📁 Struktur Direktori

```
pslearning/
├── __manifest__.py            # metadata & daftar data
├── controllers/main.py        # rute website (test, belajar, report)
├── data/                      # sequence kode course & parameter
├── migrations/                # skrip migrasi per versi
├── models/                    # 8 model + pengaturan
├── security/                  # grup, record rules, ACL
├── views/                     # view backend + QWeb template website
└── static/                    # aset (css/js) & ikon
```

---

## 📝 Catatan Teknis

- Penilaian dihitung dari soal **pilihan ganda** (`nilai = poin benar / total poin × 100`). Soal esai belum dinilai otomatis.
- Sebuah test diasumsikan untuk **satu materi**. Field _Materi_ pada test otomatis menjadi default _Materi Terkait_ pada setiap soal baru, untuk mencegah salah pilih.
- Timer ujian bersifat absolut (berbasis waktu mulai + batas waktu); saat kedaluwarsa, percobaan otomatis dikumpulkan dengan jawaban yang sudah ter-autosave.

---

## 📄 Lisensi

Modul ini dirilis di bawah lisensi **LGPL-3**. Lihat berkas [LICENSE](LICENSE) untuk detail.

---

## 👤 Penulis

**Lukman Nul Hakim**
Odoo Developer

- GitHub: [@LukmanGit](https://github.com/LukmanGit)

---

<p align="center">
  <i>Dibuat dengan ❤️ menggunakan Odoo 17</i>
</p>
