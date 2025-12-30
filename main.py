import flet as ft
import sqlite3
from datetime import datetime

def main(page: ft.Page):
    # --- KONFIGURASI HALAMAN ---
    page.title = "Autofint Lite"
    page.theme_mode = ft.ThemeMode.LIGHT
    # Hapus window_width/height karena tidak perlu di APK
    page.scroll = ft.ScrollMode.ADAPTIVE

    # --- DATABASE SETUP (SQLite) ---
    # Di Android, kita letakkan DB di folder dokumen aplikasi
    conn = sqlite3.connect("keuangan.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transaksi
                 (tanggal TEXT, tipe TEXT, kategori TEXT, deskripsi TEXT, jumlah REAL)''')
    conn.commit()

    # --- FUNGSI LOGIC ---
    def tambah_transaksi(e):
        try:
            if not input_jumlah.value:
                input_jumlah.error_text = "Isi angka dulu"
                page.update()
                return

            val_jumlah = float(input_jumlah.value)
            
            if not input_deskripsi.value:
                input_deskripsi.error_text = "Wajib diisi"
                page.update()
                return
            
            # Simpan ke DB
            c.execute("INSERT INTO transaksi VALUES (?, ?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d"), 
                       input_tipe.value, 
                       input_kategori.value, 
                       input_deskripsi.value, 
                       val_jumlah))
            conn.commit()
            
            # Reset Form
            input_jumlah.value = ""
            input_deskripsi.value = ""
            
            # Notifikasi
            page.open(ft.SnackBar(ft.Text("Data berhasil disimpan!")))
            
            load_data_laporan() # Refresh laporan
            page.update()
            
        except ValueError:
            input_jumlah.error_text = "Harus angka!"
            page.update()

    def load_data_laporan():
        # Hitung Total
        c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pemasukan'")
        res_masuk = c.fetchone()[0]
        total_masuk = res_masuk if res_masuk is not None else 0
        
        c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pengeluaran'")
        res_keluar = c.fetchone()[0]
        total_keluar = res_keluar if res_keluar is not None else 0
        
        sisa = total_masuk - total_keluar
        
        txt_pemasukan.value = f"Rp {total_masuk:,.0f}"
        txt_pengeluaran.value = f"Rp {total_keluar:,.0f}"
        txt_sisa.value = f"Rp {sisa:,.0f}"
        
        # Load Tabel (Ambil 10 terakhir)
        c.execute("SELECT * FROM transaksi ORDER BY rowid DESC LIMIT 10")
        data = c.fetchall()
        
        tabel_transaksi.rows.clear()
        for row in data:
            # PENTING: Gunakan string "green"/"red" agar kompatibel semua versi
            warna = "green" if row[1] == "Pemasukan" else "red"
            
            tabel_transaksi.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row[0], size=12)),
                        ft.DataCell(ft.Text(row[3], size=12, weight="bold")),
                        ft.DataCell(ft.Text(f"{row[4]:,.0f}", color=warna, size=12)),
                    ]
                )
            )
        page.update()

    # --- UI COMPONENTS ---
    
    input_tipe = ft.Dropdown(
        label="Tipe Transaksi",
        options=[ft.dropdown.Option("Pengeluaran"), ft.dropdown.Option("Pemasukan")],
        value="Pengeluaran"
    )
    input_kategori = ft.Dropdown(
        label="Kategori",
        options=[
            ft.dropdown.Option("Makanan"),
            ft.dropdown.Option("Transport"),
            ft.dropdown.Option("Tagihan"),
            ft.dropdown.Option("Gaji"),
            ft.dropdown.Option("Lainnya"),
        ],
        value="Makanan"
    )
    input_deskripsi = ft.TextField(label="Deskripsi (Cth: Nasi Goreng)")
    # keyboard_type NUMBER adalah standard baru
    input_jumlah = ft.TextField(label="Jumlah (Rp)", keyboard_type=ft.KeyboardType.NUMBER)
    
    # Gunakan string "blue" dan "white"
    btn_simpan = ft.ElevatedButton(text="SIMPAN DATA", on_click=tambah_transaksi, width=300, bgcolor="blue", color="white")

    tab_input = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("Catat Keuangan", size=20, weight="bold"),
            input_tipe,
            input_kategori,
            input_deskripsi,
            input_jumlah,
            ft.Divider(),
            btn_simpan
        ])
    )

    # Output Components
    txt_pemasukan = ft.Text("Rp 0", color="green", weight="bold")
    txt_pengeluaran = ft.Text("Rp 0", color="red", weight="bold")
    txt_sisa = ft.Text("Rp 0", color="blue", size=20, weight="bold")

    tabel_transaksi = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Tgl")),
            ft.DataColumn(ft.Text("Ket")),
            ft.DataColumn(ft.Text("Jml")),
        ],
        rows=[]
    )

    tab_laporan = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("Ringkasan Keuangan", size=20, weight="bold"),
            ft.Row([ft.Text("Pemasukan:"), txt_pemasukan], alignment="spaceBetween"),
            ft.Row([ft.Text("Pengeluaran:"), txt_pengeluaran], alignment="spaceBetween"),
            ft.Divider(),
            ft.Text("Sisa Kas:", size=16),
            txt_sisa,
            ft.Divider(),
            ft.Text("Riwayat Terakhir:", weight="bold"),
            ft.Column([tabel_transaksi], scroll=ft.ScrollMode.AUTO, height=300)
        ])
    )

    # --- MAIN LAYOUT ---
    t = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            # Gunakan String icon "edit" dan "analytics" agar aman
            ft.Tab(text="Input", icon="edit", content=tab_input),
            ft.Tab(text="Laporan", icon="analytics", content=tab_laporan),
        ],
        expand=1,
    )

    page.add(t)
    load_data_laporan() 

# FINAL FIX: Hapus view=WEB_BROWSER
ft.app(target=main)
