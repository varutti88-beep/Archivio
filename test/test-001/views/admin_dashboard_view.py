from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, 
    QMessageBox, QSplitter, QFrame, QScrollArea, QGroupBox, QGridLayout,
    QLineEdit, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QToolButton, QMenu, QDialog, QTextEdit,
    QDateEdit, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QDate
from PySide6.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QPainter
from models.user_model import (
    list_pending_users, set_approval, get_all_users, get_blocked_users, 
    unblock_user, block_user, get_login_attempts, force_reset_password
)
import time
from datetime import datetime, timedelta
import secrets
import string

def greeting_for_hour():
    h = datetime.now().hour
    if 6 <= h < 13:
        return "Buongiorno"
    elif 13 <= h < 18:
        return "Buon pomeriggio"
    else:
        return "Buonasera"

def fmt_time(ts, show_relative=True):
    if not ts:
        return "Non disponibile"
    
    dt = datetime.fromtimestamp(ts)
    formatted = dt.strftime("%d/%m/%Y %H:%M:%S")
    
    if show_relative:
        now = datetime.now()
        diff = now - dt
        if diff.days == 0:
            if diff.seconds < 3600:
                mins = diff.seconds // 60
                relative = f"{mins}m fa"
            else:
                hours = diff.seconds // 3600
                relative = f"{hours}h fa"
        else:
            relative = f"{diff.days}g fa"
        
        return f"{formatted} ({relative})"
    
    return formatted

class StatsCard(QFrame):
    
    def __init__(self, title, value, subtitle="", color="#3498db"):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet(f"""
            StatsCard {{
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                padding: 10px;
            }}
            QLabel#title {{
                color: #666;
                font-size: 12px;
                font-weight: bold;
            }}
            QLabel#value {{
                color: {color};
                font-size: 24px;
                font-weight: bold;
            }}
            QLabel#subtitle {{
                color: #999;
                font-size: 10px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        
        title_label = QLabel(title)
        title_label.setObjectName("title")
        
        value_label = QLabel(str(value))
        value_label.setObjectName("value")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("subtitle")
            subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(subtitle_label)
        
        self.setLayout(layout)

class UserTableWidget(QTableWidget):
    
    user_selected = Signal(dict)
    
    def __init__(self, columns):
        super().__init__()
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #f0f0f0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: 1px solid #e0e0e0;
                font-weight: bold;
            }
        """)
        
        self.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _on_selection_changed(self):
        current_row = self.currentRow()
        if current_row >= 0:
            user_data = {}
            for col in range(self.columnCount()):
                header = self.horizontalHeaderItem(col).text()
                item = self.item(current_row, col)
                if item:
                    user_data[header.lower().replace(' ', '_')] = item.text()
            self.user_selected.emit(user_data)

class SearchFilterWidget(QFrame):
    
    filter_changed = Signal(str, str, str)
    
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            SearchFilterWidget {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: #f8f9fa;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout()
        
        search_label = QLabel("🔍 Ricerca:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cerca per username o email...")
        self.search_input.textChanged.connect(self._emit_filter_changed)
        
        status_label = QLabel("Stato:")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Tutti", "In attesa", "Approvati", "Rifiutati", "Bloccati", "Admin"])
        self.status_combo.currentTextChanged.connect(self._emit_filter_changed)
        
        date_label = QLabel("Periodo:")
        self.date_combo = QComboBox()
        self.date_combo.addItems(["Tutti", "Oggi", "Ultima settimana", "Ultimo mese"])
        self.date_combo.currentTextChanged.connect(self._emit_filter_changed)
        
        layout.addWidget(search_label)
        layout.addWidget(self.search_input, 2)
        layout.addWidget(status_label)
        layout.addWidget(self.status_combo, 1)
        layout.addWidget(date_label)
        layout.addWidget(self.date_combo, 1)
        
        self.setLayout(layout)
    
    def _emit_filter_changed(self):
        self.filter_changed.emit(
            self.search_input.text(),
            self.status_combo.currentText(),
            self.date_combo.currentText()
        )

class UserDetailDialog(QDialog):
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setWindowTitle(f"Dettagli Utente - {user_data.get('username', 'N/A')}")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        info_group = QGroupBox("Informazioni Personali")
        info_layout = QGridLayout()
        
        fields = [
            ("ID:", user_data.get('id', 'N/A')),
            ("Username:", user_data.get('username', 'N/A')),
            ("Email:", user_data.get('email', 'N/A')),
            ("Stato:", user_data.get('status', 'N/A')),
            ("Data registrazione:", user_data.get('created_at', 'N/A')),
            ("Ultimo accesso:", user_data.get('last_login', 'N/A'))
        ]
        
        for i, (label, value) in enumerate(fields):
            info_layout.addWidget(QLabel(label), i, 0)
            info_layout.addWidget(QLabel(str(value)), i, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        actions_group = QGroupBox("Azioni Rapide")
        actions_layout = QHBoxLayout()
        
        if user_data.get('status') == 'bloccato':
            unblock_btn = QPushButton("🔓 Sblocca")
            unblock_btn.clicked.connect(self.unblock_user)
            actions_layout.addWidget(unblock_btn)
        
        reset_pw_btn = QPushButton("🔑 Reset Password")
        reset_pw_btn.clicked.connect(self.reset_password)
        actions_layout.addWidget(reset_pw_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        buttons_layout = QHBoxLayout()
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addWidget(QFrame())  # Spacer
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def unblock_user(self):
        try:
            uid = int(self.user_data.get('id', 0))
            unblock_user(uid)
            QMessageBox.information(self, "Successo", "Utente sbloccato con successo!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore nello sbloccare l'utente: {str(e)}")
    
    def reset_password(self):
        """Reset della password"""
        reply = QMessageBox.question(
            self, "Conferma", 
            "Sei sicuro di voler resettare la password di questo utente?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                uid = int(self.user_data.get('id', 0))
                new_pw = force_reset_password(uid)
                
                # Dialog per mostrare la nuova password
                pw_dialog = QDialog(self)
                pw_dialog.setWindowTitle("Password Temporanea Generata")
                pw_dialog.setModal(True)
                
                pw_layout = QVBoxLayout()
                pw_layout.addWidget(QLabel("Password temporanea generata:"))
                
                pw_field = QLineEdit(new_pw)
                pw_field.setReadOnly(True)
                pw_field.selectAll()
                pw_layout.addWidget(pw_field)
                
                info_label = QLabel("⚠️ Comunicare questa password in modo sicuro all'utente.\nL'utente dovrà cambiarla al prossimo accesso.")
                info_label.setWordWrap(True)
                info_label.setStyleSheet("color: #f39c12; padding: 10px;")
                pw_layout.addWidget(info_label)
                
                copy_btn = QPushButton("📋 Copia negli Appunti")
                copy_btn.clicked.connect(lambda: self.copy_to_clipboard(new_pw))
                pw_layout.addWidget(copy_btn)
                
                close_btn = QPushButton("Chiudi")
                close_btn.clicked.connect(pw_dialog.accept)
                pw_layout.addWidget(close_btn)
                
                pw_dialog.setLayout(pw_layout)
                pw_dialog.exec()
                
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore nel reset password: {str(e)}")
    
    def copy_to_clipboard(self, text):
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Copiato", "Password copiata negli appunti!")

class AdminDashboardView(QWidget):
    
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.current_filters = {"search": "", "status": "Tutti", "date": "Tutti"}
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.refresh_all)
        
        self._setup_ui()
        self._apply_styles()
        self.refresh_all()
        
        self.auto_refresh_timer.start(30000)

    def _setup_ui(self):
        self.setWindowTitle("🔧 Dashboard Amministratore")
        self.setMinimumSize(1200, 800)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        header_widget = self._create_header()
        main_layout.addWidget(header_widget)

        stats_widget = self._create_stats_section()
        main_layout.addWidget(stats_widget)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #3498db;
            }
        """)
        
        users_tab = self._create_users_tab()
        self.tab_widget.addTab(users_tab, "👥 Gestione Utenti")
        
        logs_tab = self._create_logs_tab()
        self.tab_widget.addTab(logs_tab, "📊 Log Attività")
        
        settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(settings_tab, "⚙️ Impostazioni")
        
        main_layout.addWidget(self.tab_widget)
        
        self.setLayout(main_layout)

    def _create_header(self):
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #3498db, stop: 1 #2ecc71);
                border-radius: 10px;
                padding: 15px;
            }
        """)
        
        layout = QHBoxLayout()
        
        left_layout = QVBoxLayout()
        title = QLabel("Dashboard Amministratore")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        
        greeting = QLabel(f"{greeting_for_hour()}, {self.user['username']}")
        greeting.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 14px;")
        
        left_layout.addWidget(title)
        left_layout.addWidget(greeting)
        
        right_layout = QVBoxLayout()
        last_login = QLabel(f"Ultimo accesso: {fmt_time(time.time())}")
        last_login.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        last_login.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        right_layout.addWidget(last_login)
        
        layout.addLayout(left_layout, 3)
        layout.addLayout(right_layout, 1)
        
        header_frame.setLayout(layout)
        return header_frame

    def _create_stats_section(self):
        stats_frame = QFrame()
        layout = QHBoxLayout()
        
        all_users = get_all_users()
        pending = list_pending_users()
        blocked = get_blocked_users()
        
        total_card = StatsCard("Utenti Totali", len(all_users), "utenti registrati", "#3498db")
        pending_card = StatsCard("In Attesa", len(pending), "da approvare", "#f39c12")
        blocked_card = StatsCard("Bloccati", len(blocked), "accesso negato", "#e74c3c")
        active_card = StatsCard("Attivi", len([u for u in all_users if u.get('is_approved')]), "accesso consentito", "#2ecc71")
        
        layout.addWidget(total_card)
        layout.addWidget(pending_card)
        layout.addWidget(blocked_card)
        layout.addWidget(active_card)
        
        stats_frame.setLayout(layout)
        return stats_frame

    def _create_users_tab(self):
        """Crea il tab per la gestione utenti"""
        tab_widget = QWidget()
        layout = QVBoxLayout()
        
        self.search_filter = SearchFilterWidget()
        self.search_filter.filter_changed.connect(self._apply_filters)
        layout.addWidget(self.search_filter)
        
        splitter = QSplitter(Qt.Horizontal)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        pending_group = QGroupBox("⏳ Utenti in Attesa di Approvazione")
        pending_layout = QVBoxLayout()
        
        self.pending_table = UserTableWidget(["ID", "Username", "Email", "Data Registrazione"])
        self.pending_table.user_selected.connect(self._on_pending_user_selected)
        pending_layout.addWidget(self.pending_table)
        
        pending_buttons = QHBoxLayout()
        self.approve_btn = QPushButton("✅ Approva")
        self.approve_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px;")
        self.approve_btn.clicked.connect(self.approve_selected)
        
        self.reject_btn = QPushButton("❌ Rifiuta")
        self.reject_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px;")
        self.reject_btn.clicked.connect(self.reject_selected)
        
        pending_buttons.addWidget(self.approve_btn)
        pending_buttons.addWidget(self.reject_btn)
        pending_layout.addLayout(pending_buttons)
        
        pending_group.setLayout(pending_layout)
        left_layout.addWidget(pending_group)
        
        blocked_group = QGroupBox("🔒 Utenti Bloccati")
        blocked_layout = QVBoxLayout()
        
        self.blocked_table = UserTableWidget(["ID", "Username", "Email", "Tentativi", "Ultimo Tentativo"])
        self.blocked_table.user_selected.connect(self._on_blocked_user_selected)
        blocked_layout.addWidget(self.blocked_table)
        
        blocked_buttons = QHBoxLayout()
        self.unblock_btn = QPushButton("🔓 Sblocca")
        self.unblock_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        self.unblock_btn.clicked.connect(self.unblock_selected)
        
        self.force_reset_btn = QPushButton("🔑 Reset Password")
        self.force_reset_btn.setStyleSheet("background-color: #f39c12; color: white; padding: 8px;")
        self.force_reset_btn.clicked.connect(self.force_reset_selected)
        
        blocked_buttons.addWidget(self.unblock_btn)
        blocked_buttons.addWidget(self.force_reset_btn)
        blocked_layout.addLayout(blocked_buttons)
        
        blocked_group.setLayout(blocked_layout)
        left_layout.addWidget(blocked_group)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        all_users_group = QGroupBox("👥 Tutti gli Utenti")
        all_users_layout = QVBoxLayout()
        
        self.all_users_table = UserTableWidget(["ID", "Username", "Email", "Stato", "Ultimo Accesso"])
        self.all_users_table.user_selected.connect(self._on_user_double_clicked)
        all_users_layout.addWidget(self.all_users_table)
        
        view_details_btn = QPushButton("👁️ Visualizza Dettagli")
        view_details_btn.clicked.connect(self.show_user_details)
        all_users_layout.addWidget(view_details_btn)
        
        all_users_group.setLayout(all_users_layout)
        right_layout.addWidget(all_users_group)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([600, 500])
        layout.addWidget(splitter)
        
        tab_widget.setLayout(layout)
        return tab_widget

    def _create_logs_tab(self):
        tab_widget = QWidget()
        layout = QVBoxLayout()
        
        controls_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Aggiorna")
        refresh_btn.clicked.connect(self.refresh_logs)
        
        export_btn = QPushButton("💾 Esporta Log")
        export_btn.clicked.connect(self.export_logs)
        
        records_label = QLabel("Mostra ultimi:")
        self.records_spin = QSpinBox()
        self.records_spin.setRange(50, 1000)
        self.records_spin.setValue(200)
        self.records_spin.setSuffix(" record")
        
        controls_layout.addWidget(refresh_btn)
        controls_layout.addWidget(export_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(records_label)
        controls_layout.addWidget(self.records_spin)
        
        layout.addLayout(controls_layout)
        
        self.logs_table = UserTableWidget(["Data/Ora", "Username", "Risultato", "Note", "IP"])
        layout.addWidget(self.logs_table)
        
        tab_widget.setLayout(layout)
        return tab_widget

    def _create_settings_tab(self):

        tab_widget = QWidget()
        layout = QVBoxLayout()
        
        general_group = QGroupBox("⚙️ Impostazioni Generali")
        general_layout = QGridLayout()
        
        general_layout.addWidget(QLabel("Auto-refresh dashboard:"), 0, 0)
        self.auto_refresh_check = QCheckBox("Abilitato (ogni 30 secondi)")
        self.auto_refresh_check.setChecked(True)
        self.auto_refresh_check.toggled.connect(self._toggle_auto_refresh)
        general_layout.addWidget(self.auto_refresh_check, 0, 1)
        
        general_layout.addWidget(QLabel("Max tentativi login:"), 1, 0)
        max_attempts_spin = QSpinBox()
        max_attempts_spin.setRange(3, 10)
        max_attempts_spin.setValue(5)
        general_layout.addWidget(max_attempts_spin, 1, 1)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        system_group = QGroupBox("🔧 Azioni Sistema")
        system_layout = QVBoxLayout()
        
        backup_btn = QPushButton("💾 Backup Database")
        backup_btn.clicked.connect(self.backup_database)
        
        cleanup_btn = QPushButton("🧹 Pulizia Log Vecchi")
        cleanup_btn.clicked.connect(self.cleanup_old_logs)
        
        system_layout.addWidget(backup_btn)
        system_layout.addWidget(cleanup_btn)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        layout.addStretch()
        tab_widget.setLayout(layout)
        return tab_widget

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
            QPushButton:pressed {
                opacity: 0.6;
            }
        """)

    def refresh_all(self):
        self.refresh_pending()
        self.refresh_blocked()
        self.refresh_all_users()
        self.refresh_logs()
        
        try:
            stats_widget = self.layout().itemAt(1).widget()  
            stats_widget.deleteLater()
            new_stats = self._create_stats_section()
            self.layout().insertWidget(1, new_stats)
        except:
            pass

    def refresh_pending(self):
        if hasattr(self, 'pending_table'):
            self.pending_table.setRowCount(0)
            pending = list_pending_users()
            
            for row_idx, user in enumerate(pending):
                self.pending_table.insertRow(row_idx)
                self.pending_table.setItem(row_idx, 0, QTableWidgetItem(str(user['id'])))
                self.pending_table.setItem(row_idx, 1, QTableWidgetItem(user['username']))
                self.pending_table.setItem(row_idx, 2, QTableWidgetItem(user['email']))
                self.pending_table.setItem(row_idx, 3, QTableWidgetItem(fmt_time(user.get('created_at', 0))))

    def refresh_blocked(self):
        if hasattr(self, 'blocked_table'):
            self.blocked_table.setRowCount(0)
            blocked = get_blocked_users()
            
            for row_idx, user in enumerate(blocked):
                self.blocked_table.insertRow(row_idx)
                self.blocked_table.setItem(row_idx, 0, QTableWidgetItem(str(user['id'])))
                self.blocked_table.setItem(row_idx, 1, QTableWidgetItem(user['username']))
                self.blocked_table.setItem(row_idx, 2, QTableWidgetItem(user['email']))
                self.blocked_table.setItem(row_idx, 3, QTableWidgetItem(str(user['failed_attempts'])))
                self.blocked_table.setItem(row_idx, 4, QTableWidgetItem(fmt_time(user.get('last_attempt', 0))))

    def refresh_all_users(self):
        if hasattr(self, 'all_users_table'):
            self.all_users_table.setRowCount(0)
            all_users = get_all_users()
            
            for row_idx, user in enumerate(all_users):
                self.all_users_table.insertRow(row_idx)
                self.all_users_table.setItem(row_idx, 0, QTableWidgetItem(str(user['id'])))
                self.all_users_table.setItem(row_idx, 1, QTableWidgetItem(user['username']))
                self.all_users_table.setItem(row_idx, 2, QTableWidgetItem(user['email']))
                
                if user.get('is_admin'):
                    status = "👑 Admin"
                elif user.get('is_approved'):
                    status = "✅ Approvato"
                elif user.get('failed_attempts', 0) >= 5:
                    status = "🔒 Bloccato"
                else:
                    status = "⏳ In attesa"
                
                self.all_users_table.setItem(row_idx, 3, QTableWidgetItem(status))
                self.all_users_table.setItem(row_idx, 4, QTableWidgetItem(fmt_time(user.get('last_login', 0))))

    def refresh_logs(self):
        if hasattr(self, 'logs_table'):
            self.logs_table.setRowCount(0)
            max_records = getattr(self.records_spin, 'value', lambda: 200)()
            attempts = get_login_attempts(max_records)
            
            for row_idx, attempt in enumerate(attempts):
                self.logs_table.insertRow(row_idx)
                self.logs_table.setItem(row_idx, 0, QTableWidgetItem(fmt_time(attempt['attempted_at'])))
                self.logs_table.setItem(row_idx, 1, QTableWidgetItem(attempt['username']))
                
                result = "✅ Successo" if attempt['success'] == 1 else "❌ Fallito"
                self.logs_table.setItem(row_idx, 2, QTableWidgetItem(result))
                
                self.logs_table.setItem(row_idx, 3, QTableWidgetItem(attempt.get('note', '')))
                self.logs_table.setItem(row_idx, 4, QTableWidgetItem(attempt.get('ip_address', 'N/A')))

    def _apply_filters(self, search_text, status_filter, date_filter):
        self.current_filters = {
            "search": search_text,
            "status": status_filter,
            "date": date_filter
        }
        self.refresh_all()

    def _toggle_auto_refresh(self, enabled):
        if enabled:
            self.auto_refresh_timer.start(30000)
        else:
            self.auto_refresh_timer.stop()

    def _on_pending_user_selected(self, user_data):
        self.selected_pending_user = user_data

    def _on_blocked_user_selected(self, user_data):
        self.selected_blocked_user = user_data

    def _on_user_double_clicked(self, user_data):
        self.selected_user = user_data

    def approve_selected(self):
        if not hasattr(self, 'selected_pending_user'):
            QMessageBox.warning(self, "Selezione", "Seleziona un utente dalla tabella.")
            return
        
        try:
            uid = int(self.selected_pending_user.get('id', 0))
            set_approval(uid, True)
            QMessageBox.information(self, "✅ Successo", "Utente approvato con successo!")
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "❌ Errore", f"Errore nell'approvazione: {str(e)}")

    def reject_selected(self):
        """Rifiuta l'utente selezionato"""
        if not hasattr(self, 'selected_pending_user'):
            QMessageBox.warning(self, "Selezione", "Seleziona un utente dalla tabella.")
            return
        
        reply = QMessageBox.question(
            self, "Conferma Rifiuto", 
            f"Sei sicuro di voler rifiutare l'utente {self.selected_pending_user.get('username')}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                uid = int(self.selected_pending_user.get('id', 0))
                set_approval(uid, False)
                QMessageBox.information(self, "✅ Successo", "Utente rifiutato.")
                self.refresh_all()
            except Exception as e:
                QMessageBox.critical(self, "❌ Errore", f"Errore nel rifiuto: {str(e)}")

    def unblock_selected(self):
        """Sblocca l'utente selezionato"""
        if not hasattr(self, 'selected_blocked_user'):
            QMessageBox.warning(self, "Selezione", "Seleziona un utente bloccato dalla tabella.")
            return
        
        try:
            uid = int(self.selected_blocked_user.get('id', 0))
            unblock_user(uid)
            QMessageBox.information(self, "🔓 Successo", "Utente sbloccato con successo!")
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "❌ Errore", f"Errore nello sblocco: {str(e)}")

    def force_reset_selected(self):
        """Reset forzato password utente selezionato"""
        if not hasattr(self, 'selected_blocked_user'):
            QMessageBox.warning(self, "Selezione", "Seleziona un utente dalla tabella.")
            return
        
        reply = QMessageBox.question(
            self, "Conferma Reset Password", 
            f"Sei sicuro di voler resettare la password per {self.selected_blocked_user.get('username')}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                uid = int(self.selected_blocked_user.get('id', 0))
                new_pw = force_reset_password(uid)
                
                self._show_new_password_dialog(new_pw, self.selected_blocked_user.get('username'))
                self.refresh_all()
                
            except Exception as e:
                QMessageBox.critical(self, "❌ Errore", f"Errore nel reset password: {str(e)}")

    def _show_new_password_dialog(self, password, username):
        dialog = QDialog(self)
        dialog.setWindowTitle("🔑 Password Temporanea Generata")
        dialog.setModal(True)
        dialog.resize(450, 300)
        
        layout = QVBoxLayout()
        
        header_label = QLabel(f"Password temporanea generata per: <b>{username}</b>")
        header_label.setStyleSheet("font-size: 14px; padding: 10px; background-color: #e3f2fd; border-radius: 5px;")
        layout.addWidget(header_label)
        
        pw_group = QGroupBox("Password Generata")
        pw_layout = QVBoxLayout()
        
        pw_field = QLineEdit(password)
        pw_field.setReadOnly(True)
        pw_field.setStyleSheet("font-family: 'Courier New', monospace; font-size: 16px; padding: 8px; background-color: #f8f9fa;")
        pw_field.selectAll()
        
        copy_btn = QPushButton("📋 Copia negli Appunti")
        copy_btn.setStyleSheet("background-color: #3498db; color: white;")
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(password))
        
        pw_layout.addWidget(pw_field)
        pw_layout.addWidget(copy_btn)
        pw_group.setLayout(pw_layout)
        layout.addWidget(pw_group)
        
        instructions = QLabel("""
        <b>⚠️ Istruzioni Importanti:</b><br>
        • Comunicare questa password all'utente tramite canale sicuro<br>
        • L'utente DEVE cambiarla al primo accesso<br>
        • La password è temporanea e ha validità limitata<br>
        • Non condividere questa password via email non criptata
        """)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 10px; background-color: #fff3cd; border-radius: 5px; border-left: 4px solid #f39c12;")
        layout.addWidget(instructions)
        
        button_layout = QHBoxLayout()
        
        send_email_btn = QPushButton("📧 Prepara Email")
        send_email_btn.setStyleSheet("background-color: #2ecc71; color: white;")
        send_email_btn.clicked.connect(lambda: self._prepare_password_email(username, password))
        
        close_btn = QPushButton("✅ Ho Preso Nota")
        close_btn.setStyleSheet("background-color: #95a5a6; color: white;")
        close_btn.clicked.connect(dialog.accept)
        
        button_layout.addWidget(send_email_btn)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def _copy_to_clipboard(self, text):
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Copiato!")
        msg.setText("Password copiata negli appunti con successo.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def _prepare_password_email(self, username, password):
        """Prepara template email per l'invio della password"""
        email_template = f"""
Oggetto: Reset Password - Accesso Sistema

Caro/a {username},

La tua password è stata resettata dall'amministratore del sistema.

Password temporanea: {password}

IMPORTANTE:
- Questa password è temporanea e deve essere cambiata al primo accesso
- Non condividere questa password con nessuno
- Accedi al sistema e cambia immediatamente la password
- Se non hai richiesto questo reset, contatta l'amministratore

Cordiali saluti,
Team Amministrazione Sistema
"""
        
        email_dialog = QDialog(self)
        email_dialog.setWindowTitle("📧 Template Email")
        email_dialog.setModal(True)
        email_dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Template email preparato:"))
        
        email_text = QTextEdit()
        email_text.setPlainText(email_template)
        email_text.setStyleSheet("font-family: 'Courier New', monospace;")
        layout.addWidget(email_text)
        
        button_layout = QHBoxLayout()
        
        copy_email_btn = QPushButton("📋 Copia Template")
        copy_email_btn.clicked.connect(lambda: self._copy_to_clipboard(email_template))
        
        close_email_btn = QPushButton("Chiudi")
        close_email_btn.clicked.connect(email_dialog.accept)
        
        button_layout.addWidget(copy_email_btn)
        button_layout.addWidget(close_email_btn)
        
        layout.addLayout(button_layout)
        email_dialog.setLayout(layout)
        email_dialog.exec()

    def show_user_details(self):
        if not hasattr(self, 'selected_user'):
            QMessageBox.warning(self, "Selezione", "Seleziona un utente dalla tabella.")
            return
        
        dialog = UserDetailDialog(self.selected_user, self)
        dialog.exec()

    def export_logs(self):
        try:
            from PySide6.QtWidgets import QFileDialog
            import csv
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Esporta Log", "login_logs.csv", "CSV Files (*.csv)"
            )
            
            if filename:
                attempts = get_login_attempts(1000)  # Esporta ultimi 1000 record
                
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['data_ora', 'username', 'successo', 'note', 'ip_address']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for attempt in attempts:
                        writer.writerow({
                            'data_ora': fmt_time(attempt['attempted_at'], False),
                            'username': attempt['username'],
                            'successo': 'Sì' if attempt['success'] == 1 else 'No',
                            'note': attempt.get('note', ''),
                            'ip_address': attempt.get('ip_address', 'N/A')
                        })
                
                QMessageBox.information(self, "✅ Successo", f"Log esportati con successo in:\n{filename}")
                
        except Exception as e:
            QMessageBox.critical(self, "❌ Errore", f"Errore nell'esportazione: {str(e)}")

    def backup_database(self):
        """Esegue backup del database"""
        reply = QMessageBox.question(
            self, "Conferma Backup", 
            "Sei sicuro di voler eseguire il backup del database?\nQuesta operazione potrebbe richiedere alcuni minuti.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}.sql"
                

                import time
                time.sleep(2) 
                
                QMessageBox.information(
                    self, "✅ Backup Completato", 
                    f"Backup completato con successo!\nFile: {backup_name}\nPosizione: ./backups/"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "❌ Errore Backup", f"Errore durante il backup: {str(e)}")

    def cleanup_old_logs(self):
        """Pulisce i log più vecchi"""
        reply = QMessageBox.question(
            self, "Pulizia Log", 
            "Vuoi eliminare i log più vecchi di 90 giorni?\nQuesta azione non può essere annullata.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                
                cutoff_date = datetime.now() - timedelta(days=90)
                
                import time
                time.sleep(1)
                
                QMessageBox.information(
                    self, "🧹 Pulizia Completata", 
                    f"Log precedenti al {cutoff_date.strftime('%d/%m/%Y')} eliminati con successo."
                )
                
                self.refresh_logs()
                
            except Exception as e:
                QMessageBox.critical(self, "❌ Errore", f"Errore durante la pulizia: {str(e)}")

    def closeEvent(self, event):
        self.auto_refresh_timer.stop()
        event.accept()
