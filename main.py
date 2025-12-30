import flet as ft
import sqlite3
import os

def main(page: ft.Page):
    # --- 1. SETTING AMAN ---
    page.title = "Autofint Lite"
    page.theme_mode = "light" 
    page.scroll = "adaptive"
    page.bgcolor = "white"

    # TRY-CATCH UTAMA (Agar error ketahuan)
    try:
        # --- 2. DATABASE SETUP ---
        # Mencari lokasi aman penyimpanan data
        try:
            db_folder = os.getenv("FLET_APP_STORAGE_DATA") 
            if not db_folder:
                db_folder = "." 
            db_path = os.path.join(db_folder, "keuangan.db")
        except:
            db_path = "keuangan.db"

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

        # --- 3. VARIABEL & LOGIKA ---
        val_pemasukan = ft.Text("Rp 0", color="green", weight="bold", size=14)
        val_pengeluaran = ft.Text("Rp 0", color="red", weight="bold", size=14)
        val_sisa = ft.Text("Rp 0", color="blue", weight="bold", size=20)
        
        tabel_data = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Tgl")),
                ft.DataColumn(ft.Text("Ket")),
                ft.DataColumn(ft.Text("Jml")),
                ft.DataColumn(ft.Text("Del")), # Tombol Hapus
            ],
            rows=[]
        )

        def hitung_ringkasan():
            c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pemasukan'")
            res_masuk = c.fetchone()[0] or 0
            
            c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pengeluaran'")
            res_keluar = c.fetchone()[0] or 0
            
            sisa = total_masuk = res_masuk
            sisa = res_masuk - res_keluar
            
            val_pemasukan.value = f"Rp {res_masuk:,.0f}"
            val_pengeluaran.value = f"Rp {res_keluar:,.0f}"
            val_sisa.value = f"Rp {sisa:,.0f}"
            page.update()

        def hapus_transaksi(e):
            try:
                id_hapus = e.control.data
                c.execute("DELETE FROM transaksi WHERE id=?", (id_hapus,))
                conn.commit()
                page.open(ft.SnackBar(ft.Text("Data dihapus")))
                load_data_db()
                hitung_ringkasan()
            except Exception as ex:
                print(ex)

        def load_data_db():
            c.execute("SELECT * FROM transaksi ORDER BY id DESC LIMIT 15")
            data = c.fetchall()
            tabel_data.rows.clear()
            for row in data:
                # row: 0=id, 1=tgl, 2=tipe, 3=kat, 4=desc, 5=jml
                warna_teks = "green" if row[2] == "Pemasukan" else "red"
                tabel_data.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(row[1], size=11)),
                            ft.DataCell(ft.Text(row[4], size=11, weight="bold")),
                            ft.DataCell(ft.Text(f"{row[5]:,.0f}", color=warna_teks, size=11)),
                            ft.DataCell(
                                ft.IconButton(
                                    icon="delete", 
                                    icon_color="red", 
                                    icon_size=18,
                                    data=row[0],
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
                    input_jumlah.error_text = "Wajib isi"
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
                page.open(ft.SnackBar(ft.Text("Berhasil!")))
                
                # Refresh data
                load_data_db()
                hitung_ringkasan()
                
            except ValueError:
                input_jumlah.error_text = "Harus angka"
                page.update()

        # --- 4. KOMPONEN UI ---
        input_tipe = ft.Dropdown(
            label="Tipe", options=[ft.dropdown.Option("Pengeluaran"), ft.dropdown.Option("Pemasukan")],
            value="Pengeluaran"
        )
        input_kategori = ft.Dropdown(
            label="Kategori", options=[ft.dropdown.Option("Makan"), ft.dropdown.Option("Transport"), ft.dropdown.Option("Lainnya")],
            value="Makan"
        )
        input_deskripsi = ft.TextField(label="Catatan")
        input_jumlah = ft.TextField(label="Rp (Nominal)", keyboard_type="number")
        btn_simpan = ft.ElevatedButton("SIMPAN", on_click=simpan_klik, bgcolor="blue", color="white")

        # Kontainer Halaman Input
        tab_input_content = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Input Transaksi", size=18, weight="bold"),
                input_tipe, input_kategori, input_jumlah, input_deskripsi, 
                ft.Container(height=10), btn_simpan
            ])
        )

        # Kontainer Halaman Laporan
        tab_laporan_content = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Laporan Keuangan", size=18, weight="bold"),
                ft.Container(
                    padding=10, bgcolor="blue50", border_radius=10,
                    content=ft.Column([
                        ft.Text("Sisa Saldo:", size=12), val_sisa,
                        ft.Divider(),
                        ft.Row([
                            ft.Column([ft.Text("Masuk"), val_pemasukan]),
                            ft.Column([ft.Text("Keluar"), val_pengeluaran]),
                        ], alignment="spaceBetween")
                    ])
                ),
                ft.Divider(),
                ft.Column([tabel_data], scroll="auto", height=350)
            ])
        )

        # --- 5. TABS LAYOUT (SOLUSI FIX) ---
        # Kita pakai ft.Tabs (Menu Atas) karena lebih stabil daripada NavigationBar
        def on_tab_change(e):
            # Refresh data setiap kali pindah tab
            load_data_db()
            hitung_ringkasan()

        t = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            on_change=on_tab_change,
            tabs=[
                ft.Tab(text="Input", icon="edit", content=tab_input_content),
                ft.Tab(text="Laporan", icon="analytics", content=tab_laporan_content),
            ],
            expand=1,
        )

        page.add(t)
        
        # Init Data
        hitung_ringkasan()
        load_data_db()

    except Exception as e:
        # Layar Merah Penyelamat (Kalau masih ada error lain)
        page.bgcolor = "red"
        page.add(ft.Column([
            ft.Text("ERROR LAGI!", size=30, color="white"),
            ft.Text(str(e), color="white")
        ], alignment="center"))

ft.app(target=main)
