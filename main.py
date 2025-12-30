import flet as ft
import sqlite3
import csv
from datetime import datetime, date
import calendar
import os
import traceback # Penting untuk menampilkan error di layar HP

def main(page: ft.Page):
    # --- ERROR HANDLING UTAMA ---
    # Membungkus seluruh aplikasi agar jika crash, error muncul di layar HP
    try:
        # --- KONFIGURASI HALAMAN ---
        page.title = "Autofint Pro"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 0
        page.spacing = 0
        # window settings diabaikan di mobile, tapi aman dibiarkan
        
        # Warna Tema
        color_primary = ft.colors.TEAL_600
        
        # --- DATABASE SETUP (ANDROID FIX) ---
        # Di Android, kita tidak bisa tulis di root. Harus di home directory user.
        try:
            # Mencari folder dokumen yang writable di Android/PC
            base_dir = os.path.expanduser("~")
            db_path = os.path.join(base_dir, "keuangan.db")
            # Debugging path (opsional, bisa dilihat jika error)
            print(f"Database path: {db_path}") 
        except Exception as e:
            # Fallback jika gagal ambil path (jarang terjadi)
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

        # --- STATE MANAGEMENT & VARIABLES ---
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
        
        # --- HELPER COMPONENTS (LOGO & WATERMARK) ---
        def get_logo(is_dark_bg=False):
            color = "white" if is_dark_bg else color_primary
            return ft.Row(
                [
                    ft.Icon(ft.icons.TOKEN, color=color, size=20),
                    ft.Text("Gita Technology", weight="bold", size=18, color=color, font_family="Roboto")
                ], 
                alignment=ft.MainAxisAlignment.CENTER
            )

        def get_watermark():
            return ft.Container(
                content=ft.Text("Powered by Gita Technology", size=10, italic=True, color=ft.colors.GREY_400),
                alignment=ft.alignment.center,
                padding=ft.padding.only(top=10, bottom=10)
            )

        # --- HELPER FUNCTIONS ---
        def format_rupiah(value):
            if value is None: return "Rp 0"
            try:
                val = float(value)
                return f"Rp {int(val):,}".replace(",", ".")
            except: return "Rp 0"

        def get_icon_for_category(kategori):
            if not kategori: return ft.icons.CATEGORY
            kat = kategori.lower()
            if "makan" in kat: return ft.icons.FASTFOOD
            if "transport" in kat: return ft.icons.DIRECTIONS_CAR
            if "gaji" in kat: return ft.icons.ATTACH_MONEY
            if "invest" in kat or "tabungan" in kat or "darurat" in kat: return ft.icons.SAVINGS
            if "tagihan" in kat or "listrik" in kat: return ft.icons.RECEIPT_LONG
            if "belanja" in kat: return ft.icons.SHOPPING_BAG
            if "kesehatan" in kat: return ft.icons.MEDICAL_SERVICES
            return ft.icons.CATEGORY

        # --- FEATURE: FILE SAVER (ANDROID COMPATIBLE) ---
        def save_file_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    c.execute("SELECT * FROM transaksi")
                    rows = c.fetchall()
                    with open(e.path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["ID", "Tanggal", "Tipe", "Kategori", "Deskripsi", "Jumlah", "Is Tabungan"])
                        writer.writerows(rows)
                    page.show_snack_bar(ft.SnackBar(ft.Text(f"Tersimpan di: {e.path}"), bgcolor="green"))
                except Exception as ex:
                    page.show_snack_bar(ft.SnackBar(ft.Text(f"Gagal simpan: {str(ex)}"), bgcolor="red"))

        file_picker = ft.FilePicker(on_result=save_file_result)
        page.overlay.append(file_picker)

        def export_csv(e):
            file_picker.save_file(file_name="Laporan_Keuangan.csv", allowed_extensions=["csv"])

        # --- UI COMPONENTS: LOGIN ---
        def view_login():
            input_pin = ft.TextField(
                password=True, can_reveal_password=True, text_align="center", 
                width=200, max_length=6, keyboard_type=ft.KeyboardType.NUMBER,
                input_filter=ft.InputFilter(regex_string=r"[0-9]"),
                hint_text="PIN (Default: 1234)",
                on_submit=lambda e: check_pin(e)
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
                    ft.Icon(ft.icons.LOCK_OUTLINE, size=60, color=color_primary),
                    ft.Text("Secured Finance", size=24, weight="bold", color=color_primary),
                    ft.Text("Gita Technology", size=12, color="grey"),
                    ft.Container(height=30),
                    ft.Text("Masukkan PIN Keamanan", size=14),
                    input_pin,
                    ft.ElevatedButton("BUKA KUNCI", on_click=check_pin, bgcolor=color_primary, color="white", width=200),
                    ft.Container(height=50),
                    get_watermark()
                ], horizontal_alignment="center", alignment="center")
            )

        # --- UI COMPONENTS: INPUT ---
        lbl_helper_nominal = ft.Text("Rp 0", size=12, italic=True, color=ft.colors.PRIMARY)
        
        def on_nominal_change(e):
            raw = input_jumlah.value
            if raw.isdigit():
                lbl_helper_nominal.value = f"Terbaca: {format_rupiah(raw)}"
            elif raw == "":
                lbl_helper_nominal.value = "Rp 0"
            else:
                lbl_helper_nominal.value = "Hanya angka..."
            lbl_helper_nominal.update()

        input_tipe = ft.Dropdown(
            label="Tipe", options=[ft.dropdown.Option("Pengeluaran"), ft.dropdown.Option("Pemasukan")],
            value="Pengeluaran", prefix_icon=ft.icons.SWAP_VERT, border_radius=12,
            on_change=lambda e: load_kategori_options(input_tipe.value)
        )
        input_kategori = ft.Dropdown(label="Kategori", prefix_icon=ft.icons.CATEGORY, border_radius=12)
        input_deskripsi = ft.TextField(label="Catatan", prefix_icon=ft.icons.NOTE, border_radius=12)
        input_jumlah = ft.TextField(
            label="Nominal (Angka Saja)", prefix_icon=ft.icons.MONEY, 
            keyboard_type=ft.KeyboardType.NUMBER, border_radius=12,
            on_change=on_nominal_change
        )
        
        btn_simpan = ft.ElevatedButton(
            text="SIMPAN TRANSAKSI", icon=ft.icons.SAVE,
            style=ft.ButtonStyle(bgcolor=color_primary, color="white", padding=15, shape=ft.RoundedRectangleBorder(radius=10)),
            width=float("inf"), on_click=lambda e: simpan_transaksi(e)
        )
        
        btn_batal_edit = ft.TextButton("Batal Edit", visible=False, on_click=lambda e: batal_edit())

        def view_input():
            return ft.Container(
                padding=20,
                content=ft.Column([
                    get_logo(is_dark_bg=False), 
                    ft.Divider(height=10, color="transparent"),
                    ft.Text("Input Transaksi", size=20, weight="bold", color=color_primary),
                    ft.Divider(color="transparent", height=10),
                    input_tipe,
                    ft.Row([
                        ft.Container(content=input_kategori, expand=True),
                        ft.IconButton(ft.icons.ADD_BOX, icon_color=color_primary, on_click=dialog_tambah_kategori)
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

        # --- UI COMPONENTS: DASHBOARD ---
        txt_saldo = ft.Text("Rp 0", size=28, weight="bold", color="white")
        txt_masuk = ft.Text("Rp 0", size=14, color="white70")
        txt_keluar = ft.Text("Rp 0", size=14, color="white70")
        txt_invest = ft.Text("Rp 0", size=14, color="white70") 
        
        txt_search = ft.TextField(
            hint_text="Cari transaksi...", 
            prefix_icon=ft.icons.SEARCH, 
            border_radius=10, 
            height=40, 
            text_size=12,
            content_padding=10,
            on_change=lambda e: build_list_transaksi(lv_dashboard, limit=20, search_keyword=e.control.value)
        )
        
        lv_dashboard = ft.Column(spacing=10)

        def create_clickable_stat(icon, label, value_ref, color_icon, click_action):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(icon, color=color_icon, size=14), ft.Text(label, color="white70", size=11)]), 
                    value_ref
                ]),
                on_click=click_action,
                ink=True,
                padding=5,
                border_radius=5
            )

        def view_dashboard():
            return ft.Container(
                content=ft.Column([
                    ft.Container(
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                            colors=[ft.colors.TEAL_400, ft.colors.TEAL_800],
                        ),
                        border_radius=ft.border_radius.only(bottom_left=30, bottom_right=30),
                        padding=25,
                        content=ft.Column([
                            get_logo(is_dark_bg=True),
                            ft.Container(height=15),
                            ft.Row([
                                ft.Text("Dompet Saya", color="white", size=16),
                                ft.IconButton(ft.icons.DARK_MODE, icon_color="white", on_click=toggle_theme)
                            ], alignment="spaceBetween"),
                            ft.Container(height=5),
                            
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Sisa Saldo Cash", color="white70", size=12),
                                    txt_saldo,
                                ]),
                                on_click=open_simulator,
                                ink=True,
                                border_radius=10,
                                padding=ft.padding.symmetric(vertical=5, horizontal=0)
                            ),
                            
                            ft.Container(height=15),
                            
                            ft.Row([
                                create_clickable_stat(ft.icons.ARROW_DOWNWARD, "Masuk", txt_masuk, "greenAccent", lambda e: show_category_history("Pemasukan")),
                                ft.Container(width=1, height=30, bgcolor="white24"),
                                create_clickable_stat(ft.icons.ARROW_UPWARD, "Belanja", txt_keluar, "redAccent", lambda e: show_category_history("Pengeluaran")),
                                ft.Container(width=1, height=30, bgcolor="white24"),
                                create_clickable_stat(ft.icons.SAVINGS, "Invest/Tab", txt_invest, "orangeAccent", lambda e: show_category_history("Investasi")),
                            ], alignment="spaceEvenly")
                        ])
                    ),
                    ft.Container(
                        padding=ft.padding.only(left=20, right=20, top=15),
                        content=ft.Column([
                            ft.Row([
                                ft.Text("Riwayat Terakhir", weight="bold", size=16),
                                ft.TextButton("Lihat Semua", on_click=lambda _: nav_bar.on_change(ft.ControlEvent(control=nav_bar, data="2"))) 
                            ], alignment="spaceBetween"),
                            txt_search
                        ])
                    ),
                    ft.Container(
                        content=lv_dashboard,
                        padding=20
                    ),
                    get_watermark() 
                ], spacing=0, scroll=ft.ScrollMode.AUTO),
                expand=True
            )

        # --- UI COMPONENTS: LAPORAN ---
        filter_bulan = ft.Dropdown(
            label="Bulan", options=[ft.dropdown.Option("Semua")] + [ft.dropdown.Option(k) for k in map_bulan.keys()],
            value="Semua", width=120, height=45, content_padding=10, text_size=12,
            on_change=lambda e: refresh_data_laporan()
        )
        filter_tahun = ft.Dropdown(
            label="Tahun", options=[ft.dropdown.Option(t) for t in list_tahun],
            value=str(thn_skrg), width=90, height=45, content_padding=10, text_size=12,
            on_change=lambda e: refresh_data_laporan()
        )
        
        chart_pie = ft.PieChart(sections=[], sections_space=2, center_space_radius=40, expand=True)
        txt_chart_info = ft.Text("", size=12, italic=True, text_align="center")
        
        lv_laporan = ft.Column(spacing=10) 

        date_picker = ft.DatePicker(first_date=datetime.now(), last_date=datetime(2030, 12, 31))
        page.overlay.append(date_picker)
        
        def open_simulator(e):
            txt_hasil = ft.Text("Silakan klik tombol di atas untuk pilih tanggal...", italic=True, text_align="center", color=ft.colors.ON_SURFACE)
            
            def on_date_change(evt):
                if date_picker.value:
                    tgl_target = date_picker.value.date()
                    hari_ini = date.today()
                    delta = (tgl_target - hari_ini).days
                    
                    if delta <= 0:
                        txt_hasil.value = "Mohon pilih tanggal masa depan (besok atau lusa)!"
                        txt_hasil.color = ft.colors.ERROR
                    else:
                        saldo = state["total_cash"]
                        if saldo <= 0:
                            txt_hasil.value = "Saldo Cash saat ini Rp 0 atau minus.\nTidak ada dana untuk disimulasikan."
                            txt_hasil.color = ft.colors.ERROR
                        else:
                            per_hari = saldo / delta
                            txt_hasil.value = f"Sisa Waktu: {delta} Hari\nJatah Belanja Aman: {format_rupiah(per_hari)} / hari"
                            txt_hasil.color = ft.colors.PRIMARY
                            txt_hasil.weight = "bold"
                            txt_hasil.italic = False
                    txt_hasil.update()

            date_picker.on_change = on_date_change
            
            bs = ft.BottomSheet(
                ft.Container(
                    padding=20, height=300, 
                    bgcolor=ft.colors.SURFACE,
                    content=ft.Column([
                        ft.Text("Simulator Hemat", size=18, weight="bold", color=ft.colors.ON_SURFACE),
                        ft.Text("Hitung sisa uang aman per hari sampai gajian.", size=12, color=ft.colors.ON_SURFACE_VARIANT),
                        ft.Divider(),
                        ft.ElevatedButton("Pilih Tanggal Target", icon=ft.icons.CALENDAR_MONTH, on_click=lambda _: date_picker.pick_date(), width=float('inf')),
                        ft.Container(height=10),
                        ft.Container(
                            padding=20, 
                            bgcolor=ft.colors.SURFACE_VARIANT,
                            border_radius=10, width=float('inf'),
                            content=txt_hasil, alignment=ft.alignment.center
                        )
                    ], horizontal_alignment="center")
                ),
                dismissible=True
            )
            page.bottom_sheet = bs
            bs.open = True
            page.update()

        def show_category_history(mode):
            judul = ""
            where = ""
            
            if mode == "Pemasukan":
                judul = "Riwayat Pemasukan"
                where = "WHERE tipe='Pemasukan'"
            elif mode == "Pengeluaran":
                judul = "Riwayat Belanja"
                where = "WHERE tipe='Pengeluaran' AND is_tabungan=0"
            elif mode == "Investasi":
                judul = "Riwayat Investasi & Tabungan"
                where = "WHERE tipe='Pengeluaran' AND is_tabungan=1"
            
            lv_temp = ft.ListView(expand=True, spacing=10)
            build_list_transaksi(lv_temp, where_clause=where, limit=50)
            
            bs = ft.BottomSheet(
                ft.Container(
                    padding=20, height=450, 
                    bgcolor=ft.colors.SURFACE,
                    content=ft.Column([
                        ft.Text(judul, size=18, weight="bold", color=ft.colors.ON_SURFACE),
                        ft.Divider(),
                        lv_temp
                    ])
                ),
                dismissible=True
            )
            page.bottom_sheet = bs
            bs.open = True
            page.update()

        def view_laporan():
            return ft.Container(
                padding=20,
                content=ft.Column([
                    get_logo(is_dark_bg=False), 
                    ft.Divider(height=10, color="transparent"),
                    ft.Row([ft.Text("Laporan & Analisis", size=20, weight="bold"), ft.IconButton(ft.icons.CALCULATE, icon_color="blue", tooltip="Simulator Hemat", on_click=open_simulator)], alignment="spaceBetween"),
                    ft.Row([ft.Text("Filter:"), filter_bulan, filter_tahun], alignment="center"),
                    ft.Container(height=10),
                    ft.Container(
                        content=chart_pie, height=300, padding=10,
                        border=ft.border.all(1, ft.colors.OUTLINE_VARIANT), border_radius=20
                    ),
                    txt_chart_info,
                    ft.Divider(),
                    ft.Row([ft.Text("Rincian Transaksi", weight="bold"), ft.IconButton(ft.icons.DOWNLOAD, tooltip="Export CSV", on_click=export_csv)], alignment="spaceBetween"),
                    lv_laporan,
                    get_watermark() 
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                expand=True
            )

        # --- LOGIC ---

        def load_kategori_options(tipe_transaksi):
            c.execute("SELECT nama FROM master_kategori WHERE tipe=?", (tipe_transaksi,))
            rows = c.fetchall()
            input_kategori.options = [ft.dropdown.Option(r[0]) for r in rows]
            if input_kategori.options: input_kategori.value = input_kategori.options[0].key
            page.update()

        def get_query_filter():
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
            return where_sql, tuple(params)

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
            except Exception as e: print(e)

            build_list_transaksi(lv_dashboard, limit=20, search_keyword=txt_search.value)
            refresh_data_laporan()
            page.update()

        def refresh_data_laporan():
            where_clause, params = get_query_filter()
            sql_chart = f"SELECT kategori, SUM(jumlah) FROM transaksi {where_clause} AND tipe='Pengeluaran' GROUP BY kategori"
            if not where_clause: sql_chart = sql_chart.replace("AND tipe", "WHERE tipe")
            
            c.execute(sql_chart, params)
            data_chart = c.fetchall()
            
            chart_pie.sections.clear()
            colors = [ft.colors.BLUE, ft.colors.RED, ft.colors.ORANGE, ft.colors.PURPLE, ft.colors.GREEN, ft.colors.TEAL, ft.colors.PINK]
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
                            title_style=ft.TextStyle(size=12, weight="bold", color="white"),
                            badge=ft.Container(
                                content=ft.Text(f"{row[0]}", size=10, weight="bold", color=ft.colors.ON_SURFACE),
                                padding=2,
                                bgcolor=ft.colors.with_opacity(0.7, ft.colors.SURFACE), 
                                border_radius=5,
                            ),
                            badge_position=1.3 
                        )
                    )
                txt_chart_info.value = f"Total Pengeluaran (Filter): {format_rupiah(total_filtered)}"
            
            build_list_transaksi(lv_laporan, where_clause, params, limit=None)
            page.update()

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
                        lv_control.controls.append(ft.Container(padding=ft.padding.only(top=10), content=ft.Text(tgl_str, size=12, weight="bold", color=ft.colors.OUTLINE)))
                        current_date = tgl_str
                    
                    is_in = row[2] == "Pemasukan"
                    color_amt = "green" if is_in else ("orange" if row[6] == 1 else "red")
                    sign = "+" if is_in else "-"
                    
                    tile = ft.Container(
                        bgcolor=ft.colors.SURFACE_VARIANT, 
                        padding=10, 
                        border_radius=10, 
                        border=ft.border.all(0.5, ft.colors.OUTLINE_VARIANT),
                        content=ft.Row([
                            ft.Container(
                                content=ft.Icon(get_icon_for_category(row[3]), color="white", size=18), 
                                bgcolor=color_primary if is_in else ft.colors.RED_400, 
                                padding=8, 
                                border_radius=8
                            ),
                            ft.Column([
                                ft.Text(row[3], weight="bold", size=14, color=ft.colors.ON_SURFACE),
                                ft.Text(row[4] if row[4] else "-", size=11, color=ft.colors.ON_SURFACE_VARIANT, overflow=ft.TextOverflow.ELLIPSIS)
                            ], expand=True, spacing=2),
                            ft.Column([
                                ft.Text(f"{sign} {format_rupiah(row[5]).replace('Rp ','')}", color=color_amt, weight="bold", size=13),
                                ft.Row([
                                    ft.GestureDetector(content=ft.Icon(ft.icons.EDIT, size=18, color=ft.colors.PRIMARY), on_tap=lambda e, r=row: prepare_edit(r)),
                                    ft.GestureDetector(content=ft.Icon(ft.icons.DELETE, size=18, color=ft.colors.ERROR), on_tap=lambda e, r=row[0]: delete_trx(r))
                                ])
                            ], alignment="end", spacing=2)
                        ])
                    )
                    lv_control.controls.append(tile)
                except: continue
                
            if search_keyword:
                page.update()

        def delete_trx(id_trx):
            c.execute("DELETE FROM transaksi WHERE id=?", (id_trx,))
            conn.commit()
            page.show_snack_bar(ft.SnackBar(ft.Text("Dihapus!")))
            refresh_data_global()

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
            btn_simpan.icon = ft.icons.UPDATE
            btn_simpan.style.bgcolor = ft.colors.ORANGE
            btn_batal_edit.visible = True
            page.update()
            page.show_snack_bar(ft.SnackBar(ft.Text("Mode Edit Aktif: Tanggal asli akan dipertahankan.")))

        def batal_edit():
            state["edit_id"] = None
            state["edit_date"] = None
            input_jumlah.value = ""
            input_deskripsi.value = ""
            lbl_helper_nominal.value = "Rp 0"
            btn_simpan.text = "SIMPAN TRANSAKSI"
            btn_simpan.icon = ft.icons.SAVE
            btn_simpan.style.bgcolor = color_primary
            btn_batal_edit.visible = False
            page.update()

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
                refresh_data_global()
                
            except Exception as ex:
                page.show_snack_bar(ft.SnackBar(ft.Text(f"Error: {str(ex)}")))

        def dialog_tambah_kategori(e):
            txt_new = ft.TextField(label="Nama Kategori")
            def save(e):
                if txt_new.value:
                    try:
                        c.execute("INSERT INTO master_kategori VALUES (?,?,0)", (txt_new.value, input_tipe.value))
                        conn.commit()
                        load_kategori_options(input_tipe.value)
                        d.open = False
                        page.update()
                    except: pass
            d = ft.AlertDialog(title=ft.Text("Tambah Kategori"), content=txt_new, actions=[ft.TextButton("Simpan", on_click=save)])
            page.dialog = d
            d.open = True
            page.update()

        def toggle_theme(e):
            page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
            e.control.icon = ft.icons.LIGHT_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.icons.DARK_MODE
            page.update()

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
                elif index == 1: body.content = view_input()
                elif index == 2: body.content = view_laporan(); refresh_data_laporan()
                
                if nav_bar.selected_index != index:
                    nav_bar.selected_index = index
                    nav_bar.update()
                
            page.update()

        nav_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationDestination(icon=ft.icons.DASHBOARD_OUTLINED, selected_icon=ft.icons.DASHBOARD, label="Beranda"),
                ft.NavigationDestination(icon=ft.icons.ADD_CIRCLE_OUTLINE, selected_icon=ft.icons.ADD_CIRCLE, label="Input"),
                ft.NavigationDestination(icon=ft.icons.INSERT_CHART_OUTLINED, selected_icon=ft.icons.INSERT_CHART, label="Laporan"),
            ],
            on_change=lambda e: navigate_to(int(e.data)) if isinstance(e.data, str) else navigate_to(e.control.selected_index)
        )

        load_kategori_options("Pengeluaran")
        page.add(body, nav_bar)
        
        navigate_to(0) 

    # --- ERROR HANDLING UI (Muncul di layar HP jika crash) ---
    except Exception as e:
        error_msg = f"Terjadi Kesalahan:\n{e}\n\nDetail:\n{traceback.format_exc()}"
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.ERROR_OUTLINE, size=50, color="red"),
                    ft.Text("Aplikasi Crash!", size=20, weight="bold", color="red"),
                    ft.Container(
                        content=ft.Text(error_msg, color="white", selectable=True),
                        bgcolor="black", padding=10, border_radius=5, expand=True
                    )
                ]),
                padding=20, alignment=ft.alignment.center, expand=True
            )
        )

ft.app(target=main)
