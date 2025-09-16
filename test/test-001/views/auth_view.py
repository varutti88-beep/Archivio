from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QFrame
)
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtCore import Signal
from models.user_model import (
    create_user, verify_password, is_approved,
    get_user_by_username, set_otp, verify_otp
)
from utils.otp import make_otp_payload
from utils.emailer import send_otp_email


class AuthView(QWidget):
    login_success = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestione Accesso")
        self.stack = QStackedWidget()
        self.current_username = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(15)

        logo = QLabel()
        pixmap = QPixmap("assets/logo.png")
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaledToWidth(120, Qt.SmoothTransformation))
            logo.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(logo)

        card_layout.addWidget(self.stack)

        main_layout.addWidget(card, alignment=Qt.AlignCenter)

        self._login_page = self._build_login_page()
        self._register_page = self._build_register_page()
        self._otp_page = self._build_otp_page()

        self.stack.addWidget(self._login_page)   
        self.stack.addWidget(self._register_page) 
        self.stack.addWidget(self._otp_page) 

        self.setLayout(main_layout)

    #  LOGIN 
    def _build_login_page(self):
        page = QWidget()
        v = QVBoxLayout(page)

        title = QLabel("Login")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        v.addWidget(title)

        v.addWidget(QLabel("Username"))
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Inserisci username")
        v.addWidget(self.login_username)

        v.addWidget(QLabel("Password"))
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setPlaceholderText("Inserisci password")
        v.addWidget(self.login_password)

        self.login_btn = QPushButton("Accedi")
        v.addWidget(self.login_btn)

        self.to_register_btn = QPushButton("Non hai un account? Registrati")
        self.to_register_btn.setProperty("secondary", True)
        v.addWidget(self.to_register_btn, alignment=Qt.AlignCenter)

        self.login_btn.clicked.connect(self._handle_login)
        self.to_register_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        return page

    def _handle_login(self):
        username = self.login_username.text().strip()
        password = self.login_password.text().strip()

        if not username or not password:
            self._msg("Inserisci username e password.")
            return

        user = get_user_by_username(username)
        if not user:
            from models.user_model import record_login_attempt
            record_login_attempt(username, False, ip=None, note="utente_non_trovato")
            self._msg("Utente non trovato.")
            return

        if user["is_blocked"] == 1:
            self._msg("Account bloccato. Contatta l'admin.")
            from models.user_model import record_login_attempt
            record_login_attempt(username, False, ip=None, note="account_bloccato")
            return

        if not verify_password(username, password):
            from models.user_model import record_login_attempt, increment_failed_attempt, block_user
            record_login_attempt(username, False, ip=None, note="password_errata")
            failed = increment_failed_attempt(username)
            if failed >= 5:
                block_user(user["id"])
                self._msg("Troppi tentativi errati. Account bloccato.")
            else:
                remaining = 5 - failed
                self._msg(f"Password errata. Tentativi rimasti: {remaining}")
            return

        from models.user_model import reset_failed_attempts, record_login_attempt
        reset_failed_attempts(username)
        record_login_attempt(username, True, ip=None, note="password_ok")

        if user["is_admin"]:
            self.login_success.emit(dict(user))
            return

        if not is_approved(username):
            self._msg("Il tuo account è in attesa di approvazione dall'admin.")
            return

        email = user["email"]
        if not email:
            self._msg("Nessuna email associata all'account.")
            return

        code, expiry = make_otp_payload()
        set_otp(username, code, expiry)
        ok, err = send_otp_email(email, username, code)
        if ok:
            self._msg("OTP inviato alla tua email.", info=True)
            self.current_username = username
            self.stack.setCurrentIndex(2)
        else:
            self._msg(f"Errore invio OTP: {err}")

    def _build_otp_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(8)

        title = QLabel("Verifica OTP")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        v.addWidget(title)

        v.addWidget(QLabel("OTP"))
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Inserisci codice OTP")
        v.addWidget(self.otp_input)

        self.otp_confirm_btn = QPushButton("Verifica")
        v.addWidget(self.otp_confirm_btn)

        self.otp_back_btn = QPushButton("Torna al Login")
        self.otp_back_btn.setProperty("secondary", True)
        v.addWidget(self.otp_back_btn, alignment=Qt.AlignCenter)

        self.otp_confirm_btn.clicked.connect(self._handle_otp_confirm)
        self.otp_back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        return page

    def _handle_otp_confirm(self):
        code = self.otp_input.text().strip()
        ok, msg = verify_otp(self.current_username, code)
        if ok:
            user = get_user_by_username(self.current_username)
            self._msg("Accesso eseguito.", info=True)
            self.login_success.emit(dict(user))
        else:
            self._msg(f"OTP non valido: {msg}")

    def _build_register_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(8)

        title = QLabel("Registrazione")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        v.addWidget(title)

        v.addWidget(QLabel("Username"))
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Inserisci username")
        v.addWidget(self.reg_username)

        v.addWidget(QLabel("Email"))
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Inserisci email")
        v.addWidget(self.reg_email)

        v.addWidget(QLabel("Password"))
        self.reg_password = QLineEdit()
        self.reg_password.setEchoMode(QLineEdit.Password)
        self.reg_password.setPlaceholderText("Crea password")
        v.addWidget(self.reg_password)

        self.register_btn = QPushButton("Crea account")
        v.addWidget(self.register_btn)

        self.to_login_btn = QPushButton("Hai già un account? Accedi")
        self.to_login_btn.setProperty("secondary", True)
        v.addWidget(self.to_login_btn, alignment=Qt.AlignCenter)

        self.register_btn.clicked.connect(self._handle_register)
        self.to_login_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        return page

    def _handle_register(self):
        username = self.reg_username.text().strip()
        email = self.reg_email.text().strip()
        password = self.reg_password.text().strip()

        if not username or not email or not password:
            self._msg("Compila tutti i campi.")
            return

        ok, err = create_user(username, email, password)
        if ok:
            self._msg("Account creato. Attendi approvazione.", info=True)
            self.stack.setCurrentIndex(0)
        else:
            self._msg(f"Errore: {err}")

    def _msg(self, text, info=False):
        from PySide6.QtWidgets import QMessageBox
        if info:
            QMessageBox.information(self, "Info", text)
        else:
            QMessageBox.warning(self, "Attenzione", text)
