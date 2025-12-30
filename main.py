import flet as ft

def main(page: ft.Page):
    page.title = "Autofint Lite"
    page.bgcolor = "white"
    page.scroll = "adaptive"

    # Komponen Sederhana
    txt_judul = ft.Text("Autofint Lite", size=30, color="blue", weight="bold")
    txt_info = ft.Text("Aplikasi Keuangan Berhasil Diinstall!", size=16, color="black")
    
    def tombol_klik(e):
        txt_info.value = "Tombol berfungsi! Hore!"
        txt_info.color = "green"
        page.update()

    btn_test = ft.ElevatedButton("Tes Tombol", on_click=tombol_klik, bgcolor="blue", color="white")

    # Masukkan ke halaman
    page.add(
        ft.Column(
            [
                txt_judul,
                ft.Divider(),
                txt_info,
                ft.Container(height=20),
                btn_test
            ],
            alignment="center",
            horizontal_alignment="center"
        )
    )

ft.app(target=main)
