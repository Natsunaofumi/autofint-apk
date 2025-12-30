import flet as ft
import sqlite3
import os

def main(page: ft.Page):
    # --- 1. SETTING AMAN ---
    page.title = "Autofint Lite"
    page.theme_mode = "light" # String lebih aman
    page.scroll = "adaptive"
    page.bgcolor = "white"

    # --- 2. LOGIKA DEBUGGING (PENTING) ---
    # Kita bungkus semua kode dalam Try-Except
    # Agar kalau error, layar tidak putih, tapi muncul tulisan errornya
    try:
        # Tentukan lokasi database yang AMAN untuk Android
        # Kita cek apakah ada variabel lingkungan penyimpanan
        try:
            # Cara aman mencari folder dokumen di Android/PC
            db_folder = os.getenv("FLET_APP_STORAGE_DATA") 
            if not db_folder:
                db_folder = "." # Fallback ke folder saat ini (untuk PC)
            
            db_path = os.path.join(db_folder, "keuangan.db")
        except:
            # Jika gagal mencari path, pakai in-memory sementara biar gak crash
            db_path = "keuangan.db"

        # --- DATABASE SETUP ---
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS transaksi
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      tanggal TEXT, 
                      tipe TEXT, 
                      kategori TEXT, 
                      deskripsi TEXT, 
                      jumlah REAL)''')
        conn.commit()

        # --- VARIABEL ---
        val_pemasukan = ft.Text("Rp 0", color="green", weight="bold", size=16)
        val_pengeluaran = ft.Text("Rp 0", color="red", weight="bold", size=16)
        val_sisa = ft.Text("Rp 0", color="blue", weight="bold", size=24)
        
        tabel_data = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Tgl")),
                ft.DataColumn(ft.Text("Ket")),
                ft.DataColumn(ft.Text("Jml")),
                ft.DataColumn(ft.Text("Hapus")),
            ],
            rows=[]
        )

        # --- FUNGSI ---
        def hitung_ringkasan():
            c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pemasukan'")
            res_masuk = c.fetchone()[0]
            total_masuk = res_masuk if res_masuk is not None else 0
            
            c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pengeluaran'")
            res_keluar = c.fetchone()[0]
            total_keluar = res_keluar if res_keluar is not None else 0
            
            sisa = total_masuk - total_keluar
            
            val_pemasukan.value = f"Rp {total_masuk:,.0f}"
            val_pengeluaran.value = f"Rp {total_keluar:,.0f}"
            val_sisa.value = f"Rp {sisa:,.0f}"
            page.update()

        def hapus_transaksi(e):
            id_hapus = e.control.data
            c.execute("DELETE FROM transaksi WHERE id=?", (id_hapus,))
            conn.commit()
            page.open(ft.SnackBar(ft.Text("Data dihapus!")))
            load_data_db()
            hitung_ringkasan()

        def load_data_db():
            c.execute("SELECT * FROM transaksi ORDER BY id DESC LIMIT 15")
            data = c.fetchall()
            tabel_data.rows.clear()
            for row in data:
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
                            ft.DataCell(ft.Text(deskripsi, size=11, weight="bold")),
                            ft.DataCell(ft.Text(f"{jumlah:,.0f}", color=warna_teks, size=11)),
                            ft.DataCell(
                                ft.IconButton(
                                    icon="delete", 
                                    icon_color="red", 
                                    icon_size=16,
                                    data=id_transaksi,
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
                    input_jumlah.error_text = "Isi nominal"
                    page.update()
                    return
                v_jumlah = float(input_jumlah.value)
                v_desc = input_deskripsi.value if input_deskripsi.value else "-"
                
                from datetime import datetime
                tgl_sekarang = datetime.now().strftime("%d-%m")

                c.execute("INSERT INTO transaksi (tanggal, tipe, kategori, deskripsi, jumlah) VALUES (?, ?, ?, ?, ?)",
                          (tgl_sekarang, input_tipe.value, input_kategori.value, v_desc, v_jumlah))
                conn.commit()

                input_jumlah.value = ""
                input_deskripsi.value = ""
                page.open(ft.SnackBar(ft.Text("Tersimpan!")))
                hit_tombol_nav(1)
            except ValueError:
                input_jumlah.error_text = "Harus angka!"
                page.update()

        # --- UI COMPONENTS ---
        input_tipe = ft.Dropdown(
            label="Tipe",
            options=[ft.dropdown.Option("Pengeluaran"), ft.dropdown.Option("Pemasukan")],
            value="Pengeluaran", width=300
        )
        input_kategori = ft.Dropdown(
            label="Kategori",
            options=[ft.dropdown.Option("Makan"), ft.dropdown.Option("Transport"), ft.dropdown.Option("Lainnya")],
            value="Makan", width=300
        )
        input_deskripsi = ft.TextField(label="Catatan", width=300)
        input_jumlah = ft.TextField(label="Nominal (Rp)", keyboard_type="number", width=300)
        
        btn_simpan = ft.ElevatedButton("SIMPAN", on_click=simpan_klik, bgcolor="blue", color="white", width=300)

        # View Containers
        view_input = ft.Column([
            ft.Text("Input Transaksi", size=20, weight="bold"),
            input_tipe, input_kategori, input_jumlah, input_deskripsi,
            ft.Container(height=10), btn_simpan
        ], horizontal_alignment="center", spacing=20)

        view_laporan = ft.Column([
            ft.Text("Laporan Keuangan", size=20, weight="bold"),
            ft.Container(
                padding=10, bgcolor="blue50", border_radius=10, # String color aman
                content=ft.Column([
                    ft.Text("Sisa Saldo:", size=12), val_sisa,
                    ft.Row([
                        ft.Column([ft.Text("Masuk"), val_pemasukan]),
                        ft.Column([ft.Text("Keluar"), val_pengeluaran]),
                    ], alignment="spaceBetween")
                ])
            ),
            ft.Divider(),
            ft.Column([tabel_data], scroll="auto", height=400)
        ])

        # Navigation Logic
        body = ft.Container(content=view_input, padding=20)

        def nav_change(e):
            idx = e.control.selected_index
            hit_tombol_nav(idx)

        def hit_tombol_nav(index):
            if index == 0:
                body.content = view_input
            else:
                load_data_db()
                hitung_ringkasan()
                body.content = view_laporan
            nav.selected_index = index
            page.update()

        nav = ft.NavigationBar(
            destinations=[
                ft.NavigationDestination(icon="edit", label="Input"),
                ft.NavigationDestination(icon="analytics", label="Laporan"),
            ],
            on_change=nav_change
        )

        page.add(body)
        page.navigation_bar = nav
        
        # Init Load
        hitung_ringkasan()
        load_data_db()

    except Exception as e:
        # INI BAGIAN PALING PENTING
        # Jika ada error apapun, tampilkan di layar HP!
        page.bgcolor = "red"
        page.add(
            ft.Column([
                ft.Text("TERJADI ERROR!", size=30, color="white", weight="bold"),
                ft.Text(f"Pesan Error:\n{str(e)}", color="white", size=16),
                ft.Text("Silakan screenshot dan kirim ke developer.", color="white")
            ], alignment="center")
        )

ft.app(target=main)
