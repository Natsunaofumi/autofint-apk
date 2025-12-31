import flet as ft
import sqlite3
import csv
from datetime import datetime, date
import os
import traceback

def main(page: ft.Page):
    # --- ERROR HANDLING UTAMA ---
    try:
        # --- KONFIGURASI HALAMAN ---
        page.title = "Autofint Pro"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 0
        page.spacing = 0
        
        # Warna Tema
        color_primary = "teal" 
        
        # --- FIX KOMPATIBILITAS VERSI ---
        # Deteksi otomatis nama komponen navigasi
        if hasattr(ft, "NavigationDestination"):
            NavDest = ft.NavigationDestination
        elif hasattr(ft, "NavigationBarDestination"):
            NavDest = ft.NavigationBarDestination
        else:
            NavDest = ft.NavigationDestination # Fallback

        # --- DATABASE SETUP ---
        storage_path = os.environ.get("FLET_APP_STORAGE_DATA")
        if storage_path:
            db_path = os.path.join(storage_path, "keuangan.db")
        else:
            db_path = "keuangan.db"

        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS transaksi
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      tanggal TEXT, 
                      tipe TEXT, 
                      kategori TEXT, 
                      deskripsi TEXT, 
                      jumlah REAL,
                      is_tabungan INTEGER DEFAULT 0)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS master_kategori
                     (nama TEXT PRIMARY KEY, tipe TEXT, is_tabungan INTEGER)''')
        
        # Init Kategori Default
        c.execute("SELECT COUNT(*) FROM master_kategori")
        if c.fetchone()[0] == 0:
            defaults = [
                ("Gaji", "Pemasukan", 0), ("Bonus", "Pemasukan", 0),
                ("Makan", "Pengeluaran", 0), ("Transport", "Pengeluaran", 0),
                ("Belanja", "Pengeluaran", 0), ("Tagihan", "Pengeluaran", 0),
                ("Hiburan", "Pengeluaran", 0), ("Kesehatan", "Pengeluaran", 0),
                ("Dana Darurat", "Pengeluaran", 1), ("Investasi Saham", "Pengeluaran", 1)
            ]
            c.executemany("INSERT INTO master_kategori VALUES (?,?,?)", defaults)
            conn.commit()

        # --- STATE MANAGEMENT ---
        state = {
            "edit_id": None,
            "edit_date": None,
            "total_cash": 0,
            "is_logged_in": False, 
            "user_pin": "1234"
        }

        map_bulan = {
            "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
            "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
            "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
        }
        thn_skrg = datetime.now().year
        list_tahun = ["Semua"] + [str(thn_skrg - i) for i in range(3)]

        # --- HELPER FUNCTIONS ---
        def format_rupiah(value):
            if value is None: return "Rp 0"
            try:
                val = float(value)
                return f"Rp {int(val):,}".replace(",", ".")
            except: return "Rp 0"

        def get_icon_for_category(kategori):
            if not kategori: return "category"
            kat = kategori.lower()
            if "makan" in kat: return "fastfood"
            if "transport" in kat: return "directions_car"
            if "gaji" in kat: return "attach_money"
            if "invest" in kat or "tabungan" in kat or "darurat" in kat: return "savings"
            if "tagihan" in kat or "listrik" in kat: return "receipt_long"
            if "belanja" in kat: return "shopping_bag"
            if "kesehatan" in kat: return "medical_services"
            return "category"

        def get_logo(is_dark_bg=False):
            color = "white" if is_dark_bg else color_primary
            return ft.Row(
                [
                    ft.Icon("token", color=color, size=20), 
                    ft.Text("Gita Technology", weight="bold", size=18, color=color, font_family="Roboto")
                ], 
                alignment=ft.MainAxisAlignment.CENTER
            )
            
        def get_watermark():
            return ft.Container(
                content=ft.Text("Powered by Gita Technology", size=10, italic=True, color="grey"),
                alignment=ft.alignment.center,
                padding=ft.padding.only(top=10, bottom=10)
            )

        # --- NAVIGATION BAR ---
        nav_bar = ft.NavigationBar(
            destinations=[
                NavDest(icon="dashboard", label="Beranda"),
                NavDest(icon="add_circle", label="Input"),
                NavDest(icon="insert_chart", label="Laporan"),
            ]
        )

        def save_file_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    c.execute("SELECT * FROM transaksi")
                    rows = c.fetchall()
                    with open(e.path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(["ID", "Tanggal", "Tipe", "Kategori", "Deskripsi", "Jumlah", "Is Tabungan"])
                        writer.writerows(rows)
                    page.show_snack_bar(ft.SnackBar(ft.Text(f"Tersimpan di: {e.path}"), bgcolor="green"))
                except Exception as ex:
                    page.show_snack_bar(ft.SnackBar(ft.Text(f"Gagal simpan: {str(ex)}"), bgcolor="red"))

        file_picker = ft.FilePicker(on_result=save_file_result)
        page.overlay.append(file_picker)

        # --- UI COMPONENTS ---
        # PERBAIKAN: Menghapus 'height' dari Dropdown dan TextField agar kompatibel
        input_tipe = ft.Dropdown(
            label="Tipe", options=[ft.dropdown.Option("Pengeluaran"), ft.dropdown.Option("Pemasukan")],
            value="Pengeluaran", prefix_icon="swap_vert", border_radius=12
        )
        input_kategori = ft.Dropdown(label="Kategori", prefix_icon="category", border_radius=12)
        input_deskripsi = ft.TextField(label="Catatan", prefix_icon="note", border_radius=12)
        
        lbl_helper_nominal = ft.Text("Rp 0", size=12, italic=True, color="teal")
        input_jumlah = ft.TextField(
            label="Nominal (Angka Saja)", prefix_icon="money", 
            keyboard_type=ft.KeyboardType.NUMBER, border_radius=12
        )

        btn_simpan = ft.ElevatedButton(
            text="SIMPAN TRANSAKSI", icon="save",
            style=ft.ButtonStyle(bgcolor=color_primary, color="white", padding=15, shape=ft.RoundedRectangleBorder(radius=10)),
            width=float("inf")
        )
        btn_batal_edit = ft.TextButton("Batal Edit", visible=False)

        # --- DASHBOARD ---
        txt_saldo = ft.Text("Rp 0", size=28, weight="bold", color="white")
        txt_masuk = ft.Text("Rp 0", size=14, color="white70")
        txt_keluar = ft.Text("Rp 0", size=14, color="white70")
        txt_invest = ft.Text("Rp 0", size=14, color="white70") 
        
        # PERBAIKAN: Menghapus height=40 dari TextField ini
        txt_search = ft.TextField(
            hint_text="Cari...", prefix_icon="search", 
            border_radius=10, text_size=12, content_padding=10
        )
        lv_dashboard = ft.Column(spacing=10)

        # --- LAPORAN ---
        # PERBAIKAN: Menghapus height=45 dari Dropdown ini
        filter_bulan = ft.Dropdown(
            label="Bulan", options=[ft.dropdown.Option("Semua")] + [ft.dropdown.Option(k) for k in map_bulan.keys()],
            value="Semua", width=120, content_padding=10, text_size=12
        )
        # PERBAIKAN: Menghapus height=45 dari Dropdown ini
        filter_tahun = ft.Dropdown(
            label="Tahun", options=[ft.dropdown.Option(t) for t in list_tahun],
            value=str(thn_skrg), width=90, content_padding=10, text_size=12
        )
        chart_pie = ft.PieChart(sections=[], sections_space=2, center_space_radius=40, expand=True)
        txt_chart_info = ft.Text("", size=12, italic=True, text_align="center")
        lv_laporan = ft.Column(spacing=10)

        # --- LOGIC ---
        def load_kategori_options(tipe_transaksi):
            c.execute("SELECT nama FROM master_kategori WHERE tipe=?", (tipe_transaksi,))
            rows = c.fetchall()
            input_kategori.options = [ft.dropdown.Option(r[0]) for r in rows]
            if input_kategori.options and not input_kategori.value: 
                input_kategori.value = input_kategori.options[0].key
            page.update()

        def on_nominal_change(e):
            raw = input_jumlah.value
            if raw.isdigit():
                lbl_helper_nominal.value = f"Terbaca: {format_rupiah(raw)}"
            elif raw == "":
                lbl_helper_nominal.value = "Rp 0"
            else:
                lbl_helper_nominal.value = "Hanya angka..."
            lbl_helper_nominal.update()
        
        input_jumlah.on_change = on_nominal_change
        input_tipe.on_change = lambda e: load_kategori_options(input_tipe.value)

        def delete_trx(id_trx):
            try:
                c.execute("DELETE FROM transaksi WHERE id=?", (id_trx,))
                conn.commit()
                page.show_snack_bar(ft.SnackBar(ft.Text("Dihapus!")))
                refresh_data_global()
            except Exception as ex:
                print(ex)

        def prepare_edit(row):
            state["edit_id"] = row[0]
            state["edit_date"] = row[1] 
            
            nav_bar.selected_index = 1
            navigate_to(1)
            
            input_tipe.value = row[2]
            load_kategori_options(row[2])
            input_kategori.value = row[3]
            input_deskripsi.value = row[4]
            input_jumlah.value = str(int(row[5]))
            on_nominal_change(None) 
            
            btn_simpan.text = "UPDATE TRANSAKSI"
            btn_simpan.icon = "update"
            btn_simpan.style.bgcolor = "orange" 
            btn_batal_edit.visible = True
            page.update()
            page.show_snack_bar(ft.SnackBar(ft.Text("Mode Edit Aktif")))

        def batal_edit(e=None):
            state["edit_id"] = None
            state["edit_date"] = None
            input_jumlah.value = ""
            input_deskripsi.value = ""
            lbl_helper_nominal.value = "Rp 0"
            btn_simpan.text = "SIMPAN TRANSAKSI"
            btn_simpan.icon = "save"
            btn_simpan.style.bgcolor = color_primary
            btn_batal_edit.visible = False
            page.update()
        
        btn_batal_edit.on_click = batal_edit

        def simpan_transaksi(e):
            if not input_jumlah.value:
                input_jumlah.error_text = "Wajib isi"
                input_jumlah.update()
                return
            
            try:
                val = float(input_jumlah.value)
                c.execute("SELECT is_tabungan FROM master_kategori WHERE nama=?", (input_kategori.value,))
                res = c.fetchone()
                is_sav = res[0] if res else 0
                
                if state["edit_id"]:
                    c.execute('''UPDATE transaksi SET tipe=?, kategori=?, deskripsi=?, jumlah=?, is_tabungan=?, tanggal=? WHERE id=?''',
                              (input_tipe.value, input_kategori.value, input_deskripsi.value, val, is_sav, state["edit_date"], state["edit_id"]))
                    msg = "Data berhasil di-update!"
                else:
                    tgl = datetime.now().strftime("%Y-%m-%d")
                    c.execute("INSERT INTO transaksi (tanggal, tipe, kategori, deskripsi, jumlah, is_tabungan) VALUES (?,?,?,?,?,?)",
                              (tgl, input_tipe.value, input_kategori.value, input_deskripsi.value, val, is_sav))
                    msg = "Data berhasil disimpan!"
                
                conn.commit()
                batal_edit() 
                page.show_snack_bar(ft.SnackBar(ft.Text(msg), bgcolor="green"))
                
                nav_bar.selected_index = 0
                navigate_to(0)
                
            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(ft.Text(f"Error: {str(ex)}")))

        btn_simpan.on_click = simpan_transaksi

        def build_list_transaksi(lv_control, where_clause="", params=(), limit=None, search_keyword=""):
            lv_control.controls.clear()
            limit_sql = f" LIMIT {limit}" if limit else ""
            
            sql_params = list(params)
            search_filter = ""
            if search_keyword:
                search_filter = " AND (deskripsi LIKE ? OR kategori LIKE ?)"
                sql_params.append(f"%{search_keyword}%")
                sql_params.append(f"%{search_keyword}%")
                
                if not where_clause:
                    search_filter = " WHERE (deskripsi LIKE ? OR kategori LIKE ?)"

            sql = f"SELECT * FROM transaksi {where_clause} {search_filter} ORDER BY tanggal DESC, id DESC{limit_sql}"
            
            c.execute(sql, tuple(sql_params))
            rows = c.fetchall()
            
            if not rows:
                lv_control.controls.append(ft.Text("Tidak ada data.", italic=True, text_align="center"))
                return

            current_date = None
            for row in rows:
                try:
                    tgl_obj = datetime.strptime(row[1], "%Y-%m-%d")
                    tgl_str = tgl_obj.strftime("%d %B %Y")
                    
                    if tgl_str != current_date:
                        lv_control.controls.append(ft.Container(padding=ft.padding.only(top=10), content=ft.Text(tgl_str, size=12, weight="bold", color="grey")))
                        current_date = tgl_str
                    
                    is_in = row[2] == "Pemasukan"
                    color_amt = "green" if is_in else ("orange" if row[6] == 1 else "red")
                    sign = "+" if is_in else "-"
                    
                    r_copy = row
                    
                    tile = ft.Container(
                        bgcolor="surface", 
                        padding=10, 
                        border_radius=10, 
                        border=ft.border.all(0.5, "grey"),
                        content=ft.Row([
                            ft.Container(
                                content=ft.Icon(get_icon_for_category(r_copy[3]), color="white", size=18), 
                                bgcolor=color_primary if is_in else "red400", 
                                padding=8, 
                                border_radius=8
                            ),
                            ft.Column([
                                ft.Text(r_copy[3], weight="bold", size=14),
                                ft.Text(r_copy[4] if r_copy[4] else "-", size=11, color="grey", overflow=ft.TextOverflow.ELLIPSIS)
                            ], expand=True, spacing=2),
                            ft.Column([
                                ft.Text(f"{sign} {format_rupiah(r_copy[5]).replace('Rp ','')}", color=color_amt, weight="bold", size=13),
                                ft.Row([
                                    ft.GestureDetector(content=ft.Icon("edit", size=18, color="teal"), on_tap=lambda e, r=r_copy: prepare_edit(r)),
                                    ft.GestureDetector(content=ft.Icon("delete", size=18, color="red"), on_tap=lambda e, r=r_copy[0]: delete_trx(r))
                                ])
                            ], alignment="end", spacing=2)
                        ])
                    )
                    lv_control.controls.append(tile)
                except Exception as e:
                     continue

        def refresh_data_laporan():
            bulan_nama = filter_bulan.value
            tahun = filter_tahun.value
            clauses = []
            params = []
            
            if tahun != "Semua":
                clauses.append("strftime('%Y', tanggal) = ?")
                params.append(tahun)
            
            if bulan_nama != "Semua":
                bulan_angka = map_bulan.get(bulan_nama, "01")
                clauses.append("strftime('%m', tanggal) = ?")
                params.append(bulan_angka)
                
            where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
            
            sql_chart = f"SELECT kategori, SUM(jumlah) FROM transaksi {where_sql} AND tipe='Pengeluaran' GROUP BY kategori"
            if not where_sql: sql_chart = sql_chart.replace("AND tipe", "WHERE tipe")
            
            c.execute(sql_chart, tuple(params))
            data_chart = c.fetchall()
            
            chart_pie.sections.clear()
            colors = ["blue", "red", "orange", "purple", "green", "teal", "pink"]
            total_filtered = sum([r[1] for r in data_chart])
            
            if not data_chart:
                txt_chart_info.value = "Tidak ada data pada periode ini."
            else:
                for i, row in enumerate(data_chart):
                    pct = (row[1] / total_filtered) * 100
                    chart_pie.sections.append(
                        ft.PieChartSection(
                            value=row[1], 
                            title=f"{pct:.0f}%", 
                            title_position=0.5, 
                            color=colors[i % len(colors)], 
                            radius=50, 
                            title_style=ft.TextStyle(size=12, weight="bold", color="white")
                        )
                    )
                txt_chart_info.value = f"Total Pengeluaran (Filter): {format_rupiah(total_filtered)}"
            
            build_list_transaksi(lv_laporan, where_sql, tuple(params), limit=None)
            page.update()

        filter_bulan.on_change = lambda e: refresh_data_laporan()
        filter_tahun.on_change = lambda e: refresh_data_laporan()

        def refresh_data_global():
            try:
                c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pemasukan'")
                m = c.fetchone()[0] or 0
                c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pengeluaran' AND is_tabungan=0")
                k = c.fetchone()[0] or 0
                c.execute("SELECT SUM(jumlah) FROM transaksi WHERE tipe='Pengeluaran' AND is_tabungan=1")
                inv = c.fetchone()[0] or 0
                
                saldo_cash = m - (k + inv)
                state["total_cash"] = saldo_cash 
                
                txt_saldo.value = format_rupiah(saldo_cash)
                txt_masuk.value = format_rupiah(m)
                txt_keluar.value = format_rupiah(k)
                txt_invest.value = format_rupiah(inv)
                
                build_list_transaksi(lv_dashboard, limit=20, search_keyword=txt_search.value)
                page.update()
            except Exception as e:
                pass

        txt_search.on_change = lambda e: build_list_transaksi(lv_dashboard, limit=20, search_keyword=txt_search.value)

        # --- VIEWS ---
        def view_login():
            input_pin = ft.TextField(
                password=True, can_reveal_password=True, text_align="center", 
                width=200, max_length=6, keyboard_type=ft.KeyboardType.NUMBER,
                input_filter=ft.InputFilter(regex_string=r"[0-9]"),
                hint_text="PIN (Default: 1234)"
            )
            
            def check_pin(e):
                if input_pin.value and input_pin.value.strip() == state["user_pin"]:
                    state["is_logged_in"] = True
                    input_pin.value = ""
                    navigate_to(0)
                else:
                    input_pin.error_text = "PIN Salah!"
                    input_pin.update()

            return ft.Container(
                expand=True,
                bgcolor="white",
                alignment=ft.alignment.center,
                padding=30,
                content=ft.Column([
                    ft.Icon("lock_outline", size=60, color=color_primary),
                    ft.Text("Secured Finance", size=24, weight="bold", color=color_primary),
                    ft.Container(height=30),
                    input_pin,
                    ft.ElevatedButton("BUKA KUNCI", on_click=check_pin, bgcolor=color_primary, color="white", width=200),
                    ft.Container(height=50),
                    get_watermark()
                ], horizontal_alignment="center", alignment="center")
            )

        def view_dashboard():
            return ft.Container(
                content=ft.Column([
                    ft.Container(
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                            colors=["teal400", "teal800"], 
                        ),
                        border_radius=ft.border_radius.only(bottom_left=30, bottom_right=30),
                        padding=25,
                        content=ft.Column([
                            get_logo(is_dark_bg=True),
                            ft.Container(height=15),
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Sisa Saldo Cash", color="white70", size=12),
                                    txt_saldo,
                                ]),
                                border_radius=10,
                                padding=ft.padding.symmetric(vertical=5, horizontal=0)
                            ),
                            ft.Container(height=15),
                            ft.Row([
                                ft.Column([ft.Icon("arrow_downward", color="greenAccent", size=14), txt_masuk]),
                                ft.Column([ft.Icon("arrow_upward", color="redAccent", size=14), txt_keluar]),
                                ft.Column([ft.Icon("savings", color="orangeAccent", size=14), txt_invest]),
                            ], alignment="spaceEvenly")
                        ])
                    ),
                    ft.Container(
                        padding=ft.padding.only(left=20, right=20, top=15),
                        content=txt_search
                    ),
                    ft.Container(content=lv_dashboard, padding=20, expand=True),
                ]),
                expand=True
            )
            
        def view_input():
            return ft.Container(
                padding=20,
                content=ft.Column([
                    get_logo(is_dark_bg=False), 
                    ft.Divider(height=10, color="transparent"),
                    ft.Text("Input Transaksi", size=20, weight="bold", color=color_primary),
                    input_tipe,
                    ft.Row([
                        ft.Container(content=input_kategori, expand=True),
                        ft.IconButton("add_box", icon_color=color_primary, on_click=lambda e: page.open(ft.AlertDialog(title=ft.Text("Tambah Kategori (Belum aktif)"))))
                    ]),
                    input_jumlah,
                    lbl_helper_nominal,
                    input_deskripsi,
                    ft.Divider(height=20, color="transparent"),
                    btn_simpan,
                    btn_batal_edit,
                    get_watermark() 
                ], scroll=ft.ScrollMode.AUTO)
            )

        def view_laporan():
            return ft.Container(
                padding=20,
                content=ft.Column([
                    get_logo(is_dark_bg=False), 
                    ft.Divider(height=10, color="transparent"),
                    ft.Text("Laporan & Analisis", size=20, weight="bold"),
                    ft.Row([ft.Text("Filter:"), filter_bulan, filter_tahun], alignment="center"),
                    ft.Container(height=10),
                    ft.Container(
                        content=chart_pie, height=300, padding=10,
                        border=ft.border.all(1, "grey"), 
                        border_radius=20
                    ),
                    txt_chart_info,
                    ft.Divider(),
                    ft.Row([ft.Text("Rincian Transaksi", weight="bold"), ft.IconButton("download", tooltip="Export CSV", on_click=lambda e: file_picker.save_file(file_name="Laporan.csv"))], alignment="spaceBetween"),
                    lv_laporan,
                    get_watermark() 
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                expand=True
            )

        # --- NAVIGATION SYSTEM ---
        body = ft.Container(expand=True)
        
        def navigate_to(index):
            if not state["is_logged_in"]:
                body.content = view_login()
                nav_bar.visible = False
            else:
                nav_bar.visible = True
                if index == 0: 
                    body.content = view_dashboard()
                    refresh_data_global()
                elif index == 1: 
                    body.content = view_input()
                    load_kategori_options(input_tipe.value)
                elif index == 2: 
                    body.content = view_laporan()
                    refresh_data_laporan()
                
                nav_bar.selected_index = index
            page.update()

        nav_bar.on_change = lambda e: navigate_to(e.control.selected_index)

        # START APP
        page.add(body, nav_bar)
        navigate_to(0)

    except Exception as e:
        error_trace = traceback.format_exc()
        page.clean()
        page.add(
            ft.SafeArea(
                ft.Container(
                    padding=20, 
                    bgcolor="red900", 
                    expand=True,
                    content=ft.Column([
                        ft.Icon("error_outline", color="white", size=50),
                        ft.Text("CRITICAL ERROR", color="white", weight="bold", size=20),
                        ft.Divider(color="white"),
                        ft.Text("Mohon screenshot layar ini:", color="white"),
                        ft.Container(
                            content=ft.Text(error_trace, color="white", font_family="monospace", size=12),
                            bgcolor="black", padding=10, border_radius=5
                        )
                    ], scroll=ft.ScrollMode.ALWAYS)
                )
            )
        )
        page.update()

ft.app(target=main)
