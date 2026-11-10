"""Bearbeitbare Importvorschau; bestehender Plan bleibt bis zur Gesamtübernahme erhalten."""
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QTableWidget,QCheckBox,QPlainTextEdit)
from .spreadsheets import COLUMNS
from .plan_import import prepare_plan_import


def import_dialog(window,rows,mapping,notes=()):
    dialog=QDialog(window);dialog.setWindowTitle('Termine, Dienste und Wünsche importieren');dialog.resize(1220,820)
    layout=QVBoxLayout(dialog)
    intro=QLabel('Personen-IDs zuordnen, Zeilen prüfen und danach den gesamten Import übernehmen. Fehler bleiben bearbeitbar vorgemerkt.');intro.setWordWrap(True);layout.addWidget(intro)
    people=QTableWidget();layout.addWidget(people)
    mapping=dict(mapping)
    for row in rows:
        if row.get('person_ref'):mapping.setdefault(row['person_ref'],row.get('person_id',''))
    window.table(people,('Personenreferenz der Datei','Personen-ID aus der App'),list(mapping.items()),True)
    table=QTableWidget();layout.addWidget(table)
    window.table(table,COLUMNS,[[r.get(k,'') for k in COLUMNS] for r in rows],True)
    discard=QCheckBox('Vorhandenen unfixierten Entwurf durch diesen Import ersetzen (Fixierungen bleiben erhalten)');layout.addWidget(discard)
    override=QCheckBox('Regeln für diesen Import übergehen (Verstöße bleiben sichtbar)');layout.addWidget(override)
    feedback=QPlainTextEdit();feedback.setReadOnly(True);feedback.setMaximumHeight(180);layout.addWidget(feedback)
    buttons=QHBoxLayout();layout.addLayout(buttons)
    check=QPushButton('Vorschau prüfen und vormerken');apply=QPushButton('Gesamten Import übernehmen');close=QPushButton('Schließen, Vormerkung behalten')
    for b in (check,apply,close):buttons.addWidget(b)
    revision=window.store.input_revision
    def read():
        updated_mapping={people.item(i,0).text().strip():people.item(i,1).text().strip() for i in range(people.rowCount())}
        updated=[]
        for i in range(table.rowCount()):
            row={k:table.item(i,j).text().strip() for j,k in enumerate(COLUMNS)}
            row['person_id']=updated_mapping.get(row['person_ref'],'') or row['person_id']
            updated.append(row)
        window.store.save_sheet_stage(updated,updated_mapping,notes)
        proposal=prepare_plan_import(window.inputs,updated,blocks=window.blocks,events=window.events,budgets=window.budgets(),discard_unfixed=discard.isChecked(),allow_rules=override.isChecked())
        feedback.setPlainText(('Übernahme möglich. ' if proposal.ready else 'Keine Übernahme: ')+ '\n'.join(proposal.errors+proposal.notes+tuple(notes)))
        return proposal
    check.clicked.connect(lambda:window.guard(read))
    def promote():
        window.ensure_team_saved();proposal=read()
        if not proposal.ready:return
        if override.isChecked() and not window.confirm_override(proposal.notes):return
        proposal=window.store.apply_sheet_import(proposal,window.profile,expected_revision=revision)
        window.inputs,window.blocks,window.events=proposal.inputs,proposal.blocks,proposal.events
        window.proofs=();window.dirty();window.fill();window.tabs.setCurrentWidget(window.plan.parentWidget());dialog.accept()
    apply.clicked.connect(lambda:window.guard(promote));close.clicked.connect(lambda:(window.guard(read),dialog.reject()))
    dialog.exec()
