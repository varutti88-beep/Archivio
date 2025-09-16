import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from db.database import init_db
from views.auth_view import AuthView
from views.admin_dashboard_view import AdminDashboardView
from views.admin_dashboard_view import greeting_for_hour


def load_qss(app):
    try:
        with open("assets/style.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print("QSS non trovato:", e)


class MainApp:
    def __init__(self):
        init_db()
        self.app = QApplication(sys.argv)
        load_qss(self.app)

        self.auth = AuthView()
        self.auth.login_success.connect(self.show_dashboard)
        self.auth.resize(450, 500)
        self.auth.show()

        self.dashboard = None

    def show_dashboard(self, user):
        if user["is_admin"]:
            self.dashboard = AdminDashboardView(user)
            self.dashboard.resize(800, 600)
            self.dashboard.show()
        else:
            w = QWidget()
            layout = QVBoxLayout()
            top = QLabel(f"{greeting_for_hour()}, {user['username']} (area utente)")
            layout.addWidget(top)
            w.setLayout(layout)
            w.resize(700, 500)
            w.show()
            self.dashboard = w

        self.auth.close()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    MainApp().run()
