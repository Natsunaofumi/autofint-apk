import flet as ft
import sqlite3
import os

def main(page: ft.Page):
    # --- KONFIGURASI HALAMAN ---
    page.title = "Autofint Lite"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.ADAPTIVE
    
    # Supaya tampilan pas di HP (Android)
    page.window_width = 390
    page.window_height = 844

    # --- DATABASE SETUP (SQLite) ---
    # Di Android, database akan tersimpan otomatis di penyimpanan internal aplikasi
    db_path = "keuangan.db"
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    # Buat tabel jika belum ada
    c.execute('''CREATE TABLE IF NOT EXISTS transaksi
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tanggal TEXT, 
                  tipe TEXT, 
                  kategori TEXT, 
                  deskripsi TEXT, 
                  jumlah REAL)''')
    conn.commit()

    # --- STATE / VARIABLE ---
    # Kita pakai Ref agar mudah update nilai tanpa refresh halaman
    val_pemasukan = ft.Text("Rp 0", color="green", weight="bold", size=16)
    val_pengeluaran = ft.Text("Rp 0", color="red", weight="bold", size=16)
    val_sisa = ft.Text("Rp 0", color="blue", weight="bold", size=24)
    
    # Tabel Riwayat
    tabel_data = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Tgl")),
            ft.DataColumn(ft.Text("Ket")),
            ft.DataColumn(ft.Text("Jml")),
            ft.DataColumn(ft.Text("Hapus")), # Fitur Hapus
        ],
        rows=[]
    )

    # --- FUNGSI LOGIC ---

    def hitung_ringkasan():
        # Hitung Pemasukan
        c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pemasukan'")
        res_masuk = c.fetchone()[0]
        total_masuk = res_masuk if res_masuk is not None else 0
        
        # Hitung Pengeluaran
        c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pengeluaran'")
        res_keluar = c.fetchone()[0]
        total_keluar = res_keluar if res_keluar is not None else 0
        
        # Hitung Sisa
        sisa = total_masuk - total_keluar
        
        # Update Tampilan
        val_pemasukan.value = f"Rp {total_masuk:,.0f}"
        val_pengeluaran.value = f"Rp {total_keluar:,.0f}"
        val_sisa.value = f"Rp {sisa:,.0f}"
        page.update()

    def hapus_transaksi(e):
        # Ambil ID dari data tombol yang diklik
        id_hapus = e.control.data
        c.execute("DELETE FROM transaksi WHERE id=?", (id_hapus,))
        conn.commit()
        
        page.open(ft.SnackBar(ft.Text("Data dihapus!")))
        load_data_db() # Refresh tabel
        hitung_ringkasan() # Refresh angka

    def load_data_db():
        # Ambil 15 transaksi terakhir
        c.execute("SELECT * FROM transaksi ORDER BY id DESC LIMIT 15")
        data = c.fetchall()
        
        tabel_data.rows.clear()
        
        for row in data:
            # row structure: (0:id, 1:tgl, 2:tipe, 3:kat, 4:desc, 5:jml)
            id_transaksi = row[0]
            tipe = row[2]
            deskripsi = row[4]
            jumlah = row[5]
            tanggal = row[1]
            
            warna_teks = "green" if tipe == "Pemasukan" else "red"
            
            tabel_data.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(tanggal, size=11)),
                        ft.DataCell(ft.Text(deskripsi, size=11, weight="bold", overflow=ft.TextOverflow.ELLIPSIS)),
                        ft.DataCell(ft.Text(f"{jumlah:,.0f}", color=warna_teks, size=11)),
                        ft.DataCell(
                            ft.IconButton(
                                icon="delete", 
                                icon_color="red", 
                                icon_size=16,
                                data=id_transaksi, # Simpan ID di tombol
                                on_click=hapus_transaksi
                            )
                        ),
                    ]
                )
            )
        page.update()

    def simpan_klik(e):
        try:
            if not input_jumlah.value:
                input_jumlah.error_text = "Isi nominal dulu"
                page.update()
                return

            v_jumlah = float(input_jumlah.value)
            v_desc = input_deskripsi.value if input_deskripsi.value else "-"
            
            # Insert ke Database
            from datetime import datetime
            tgl_sekarang = datetime.now().strftime("%d-%m") # Format tgl pendek (Tgl-Bulan)

            c.execute("INSERT INTO transaksi (tanggal, tipe, kategori, deskripsi, jumlah) VALUES (?, ?, ?, ?, ?)",
                      (tgl_sekarang, input_tipe.value, input_kategori.value, v_desc, v_jumlah))
            conn.commit()

            # Reset Form
            input_jumlah.value = ""
            input_deskripsi.value = ""
            input_jumlah.error_text = None
            
            # Notifikasi
            page.open(ft.SnackBar(ft.Text("Berhasil Disimpan!")))
            
            # Refresh Data
            hit_tombol_nav(1) # Pindah ke tab laporan otomatis biar kelihatan
            load_data_db()
            hitung_ringkasan()

        except ValueError:
            input_jumlah.error_text = "Harus angka!"
            page.update()


    # --- KOMPONEN UI INPUT ---
    input_tipe = ft.Dropdown(
        label="Tipe",
        options=[ft.dropdown.Option("Pengeluaran"), ft.dropdown.Option("Pemasukan")],
        value="Pengeluaran",
        width=350
    )
    
    input_kategori = ft.Dropdown(
        label="Kategori",
        options=[
            ft.dropdown.Option("Makan"),
            ft.dropdown.Option("Transport"),
            ft.dropdown.Option("Belanja"),
            ft.dropdown.Option("Gaji"),
            ft.dropdown.Option("Lainnya"),
        ],
        value="Makan",
        width=350
    )
    
    input_deskripsi = ft.TextField(label="Catatan (Opsional)", width=350)
    input_jumlah = ft.TextField(label="Nominal (Rp)", keyboard_type=ft.KeyboardType.NUMBER, width=350)
    
    btn_simpan = ft.ElevatedButton(
        "SIMPAN DATA", 
        on_click=simpan_klik, 
        bgcolor="blue", 
        color="white", 
        width=350,
        height=50
    )

    # --- HALAMAN (VIEWS) ---
    
    # Halaman 1: Input
    view_input = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("Tambah Transaksi", size=20, weight="bold"),
            ft.Divider(),
            input_tipe,
            input_kategori,
            input_jumlah,
            input_deskripsi,
            ft.Container(height=20),
            btn_simpan
        ], horizontal_alignment="center")
    )

    # Halaman 2: Laporan
    view_laporan = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("Ringkasan Keuangan", size=18, weight="bold"),
            ft.Container(
                padding=15,
                bgcolor=ft.colors.BLUE_50,
                border_radius=10,
                content=ft.Column([
                    ft.Text("Sisa Saldo:", size=12),
                    val_sisa,
                    ft.Divider(color="white"),
                    ft.Row([
                        ft.Column([ft.Text("Masuk", size=10), val_pemasukan]),
                        ft.Column([ft.Text("Keluar", size=10), val_pengeluaran]),
                    ], alignment="spaceBetween")
                ])
            ),
            ft.Divider(),
            ft.Text("Riwayat Terakhir", size=16, weight="bold"),
            ft.Column([tabel_data], scroll=ft.ScrollMode.AUTO, height=400)
        ])
    )

    # --- NAVIGASI BAWAH (TAB) ---
    # Kita pakai Tabs manual dengan logika visible/invisible agar performa cepat
    
    body_container = ft.Container(content=view_input) # Default tampilan awal

    def ganti_tab(e):
        idx = e.control.selected_index
        hit_tombol_nav(idx)

    def hit_tombol_nav(index):
        if index == 0:
            body_container.content = view_input
            nav_bar.selected_index = 0
        else:
            load_data_db()     # Load data dulu sebelum tampil
            hitung_ringkasan() # Hitung uang dulu
            body_container.content = view_laporan
            nav_bar.selected_index = 1
        page.update()

    nav_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationDestination(icon="edit", label="Input"),
            ft.NavigationDestination(icon="analytics", label="Laporan"),
        ],
        on_change=ganti_tab,
        selected_index=0
    )

    # Add ke Page
    page.add(body_container)
    page.navigation_bar = nav_bar
    
    # Init Data Pertama kali
    hitung_ringkasan()
    load_data_db()

ft.app(target=main)
