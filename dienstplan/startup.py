"""Sichtbare Auswahl der bestehenden Anwendung oder des getrennten V2-Prüfbereichs."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QPushButton,QGroupBox

from .build_info import build_label


class StartDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.selection=None
        self.setWindowTitle('Dienstplan – Startauswahl')
        self.setMinimumWidth(620)
        layout=QVBoxLayout(self)
        heading=QLabel('Welchen Bereich möchtest du öffnen?')
        heading.setStyleSheet('font-size: 20px; font-weight: bold;');layout.addWidget(heading)
        self.identity=QLabel(build_label());self.identity.setWordWrap(True);layout.addWidget(self.identity)
        self.legacy_button=self.section(layout,'Bisherige Anwendung – vier Schichten',
            'Hier arbeitest du mit deinen bisher gespeicherten Dienstplänen und der bisherigen Oberfläche. '
            'Die Daten liegen weiterhin in deiner lokalen Benutzerdatenbank.',
            'Bisherige Anwendung öffnen','legacy')
        self.v2_button=self.section(layout,'V2-Prüfbereich – neuer Dienstkatalog',
            'Hier findest du die neuen V2-Funktionen mit getrennten Testdateien und fiktiven Beispieldaten. '
            'Dieser Bereich ist noch keine freigegebene produktive V2-Anwendung. '
            'Deine bisherigen Daten werden hier nicht automatisch übernommen oder geöffnet.',
            'V2-Prüfbereich öffnen','v2')
        note=QLabel('Die Auswahl führt keine Datenmigration durch. Ein neues Programmpaket löscht keine gespeicherten Dienstpläne.')
        note.setWordWrap(True);layout.addWidget(note)
        close=QPushButton('Beenden');close.clicked.connect(self.reject);layout.addWidget(close)

    def section(self,parent_layout,title,text,button_text,selection):
        group=QGroupBox(title);box=QVBoxLayout(group)
        description=QLabel(text);description.setWordWrap(True);box.addWidget(description)
        button=QPushButton(button_text);button.setMinimumHeight(42);button.setAutoDefault(False)
        button.clicked.connect(lambda:self.choose(selection));box.addWidget(button);parent_layout.addWidget(group)
        return button

    def choose(self,selection):
        self.selection=selection;self.accept()


def choose_start_mode():
    dialog=StartDialog()
    return dialog.selection if dialog.exec()==QDialog.DialogCode.Accepted else None


def check_start_dialog(app):
    """Paketprüfung: sichtbare Auswahl/Buildkennung und V2-Schaltfläche vorhanden."""
    dialog=StartDialog();dialog.show();app.processEvents()
    assert dialog.isVisible() and 'V2' in dialog.v2_button.text()
    assert 'vier Schichten' in dialog.findChildren(QGroupBox)[0].title()
    dialog.v2_button.click()
    assert dialog.selection=='v2' and dialog.result()==QDialog.DialogCode.Accepted
    dialog.close();app.processEvents()
    return True
