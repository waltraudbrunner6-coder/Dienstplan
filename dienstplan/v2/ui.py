"""Einzige Desktop-Oberfläche mit dauerhaftem lokalen Monatsarbeitsstand."""
from dataclasses import replace
from datetime import date,timedelta
from pathlib import Path
from fractions import Fraction
from threading import Event as StopEvent

from PySide6.QtCore import QThread,Signal
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,
    QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QSpinBox,QComboBox,QLineEdit,QInputDialog,
    QListWidget,QListWidgetItem,QDialogButtonBox,QWidget,QPlainTextEdit)

from .catalog import CATALOG,event
from .contracts import Contract,Contracts,exact_hours
from .application import standard_month, service_candidates, OPEN_PROFILE, SELECTED_PROFILE
from .presentation import hours_text, hours_minutes, contract_text
from .entries import WishBudget,preview,correct
from .errors import DomainError
from .exporting import export_package
from .history import historical_shares
from .objectives import evaluate
from .pauses import PausePolicy,pause_candidates
from .persistence import V2Store
from .reporting import hours_rows,shares,required_work_range
from .serialization import fingerprint
from .solver import solve_feasibility,verify,verify_for_planning
from .planning_validation import accepted_wish_warnings,blocking_issues,wish_warning_messages
from .time import Interval,vienna,day_segments
from .wishes import wish_rows


class Worker(QThread):
    completed=Signal(object,object)
    failed=Signal(str)
    def __init__(self,inputs,profile,blocks,events,seconds,token,parent=None):
        super().__init__(parent);self.inputs=inputs;self.profile=profile;self.blocks=blocks;self.events=events
        self.seconds=seconds;self.token=token;self.cancel=StopEvent()
    def run(self):
        try:self.completed.emit(solve_feasibility(self.inputs,objective_profile=self.profile,time_limit=self.seconds,
                         existing=self.blocks,existing_events=self.events,cancel=self.cancel),self.token)
        except Exception as exc:self.failed.emit(str(exc))


class Workbench(QDialog):
    def __init__(self,parent=None,*,database=None,initial=None,year=None,month=None):
        super().__init__(parent);self.setWindowTitle('Dienstplan');self.resize(1360,900)
        if database is None:
            from PySide6.QtCore import QStandardPaths
            base=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
            database=base/'dienstplan-v2.sqlite3'
        database=Path(database);database.parent.mkdir(parents=True,exist_ok=True)
        self.store=V2Store(database,create=not database.exists())
        today=date.today()
        available=[r[0].removeprefix('workspace:') for r in self.store.connection.execute("SELECT key FROM v2_meta WHERE key LIKE 'workspace:%' ORDER BY key")]
        key=f'{year or today.year:04d}-{month or today.month:02d}'
        if year is None and month is None and available:key=available[-1]
        loaded=self.store.load_workspace(*map(int,key.split('-')))
        if loaded:self.inputs,self.profile,self.blocks,self.events=loaded
        else:
            self.inputs,self.profile,self.blocks=initial or standard_month(*map(int,key.split('-')))
            if initial:
                from .plan_import import selected_events
                preferred=tuple(e for e in self.inputs.events if e.id in {b.id for b in self.blocks})
                self.events=selected_events(self.inputs,preferred)
            else:self.events=None
            self.store.save_workspace(self.inputs,self.profile,self.blocks,self.events,expected_revision=self.store.input_revision)
        self.proofs=();self.generation=0;self.worker=None;self.pending=None;self.batch=None;self.loading=False
        layout=QVBoxLayout(self)
        label=QLabel('1. Monat wählen  →  2. Personen erfassen  →  3. Dienste prüfen  →  4. Urlaub und Wünsche  →  5. Dienstplan erstellen');label.setWordWrap(True);layout.addWidget(label)
        from ..build_info import build_label
        self.build_identity=QLabel(build_label());self.build_identity.setWordWrap(True);layout.addWidget(self.build_identity)
        self.location=QLabel(str(database));layout.addWidget(self.location)
        top=QHBoxLayout();layout.addLayout(top)
        for text,handler in (('Datei kopieren',self.new_file),('Datei öffnen',self.open_file),('Monat wählen',self.new_month),('Arbeitsstand speichern',self.save),('Exportpaket',self.export),('Monat bestätigen',self.confirm)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));top.addWidget(button)
        imports=QHBoxLayout();layout.addLayout(imports)
        for text,handler in (('Termine / Dienstplan / Wünsche importieren',self.import_sheet),('Vorgemerkten Tabellenimport fortsetzen',self.resume_sheet),('Monatstabelle als Excel exportieren',self.export_grid),('BK/WL automatisch: 2 WL + 1 BK',self.configure_weekly)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));imports.addWidget(button)
        self.month_label=QLabel();layout.addWidget(self.month_label)
        self.tabs=QTabWidget();layout.addWidget(self.tabs)
        settings_page=QWidget();settings_box=QVBoxLayout(settings_page)
        settings_box.addWidget(QLabel('Der vollständige Standardkatalog ist bereits eingerichtet. Tägliche Dienste und Donnerstagsvarianten stehen automatisch im Monat.'))
        self.catalog_table=QTableWidget();settings_box.addWidget(self.catalog_table)
        self.month_notes=QLabel();self.month_notes.setWordWrap(True);settings_box.addWidget(self.month_notes)
        settings_box.addWidget(QLabel('Stundenberechnung'))
        self.calculation_profile=QComboBox();self.calculation_profile.addItem('');self.calculation_profile.setEnabled(False);settings_box.addWidget(self.calculation_profile)
        self.calculation_explanation=QLabel();settings_box.addWidget(self.calculation_explanation)
        self.tabs.addTab(settings_page,'Dienste und Einstellungen')
        team_page=QWidget();team_box=QVBoxLayout(team_page)
        self.team=QTableWidget();team_box.addWidget(self.team);self.tabs.addTab(team_page,'Personen')
        self.team.cellChanged.connect(self.dirty)
        person_bar=QHBoxLayout();team_box.addLayout(person_bar)
        for text,handler in (('Person ergänzen',self.add_person),('Person bearbeiten / Dienste ausschließen',self.person_details)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));person_bar.addWidget(button)
        term_page=QDialog();term_layout=QVBoxLayout(term_page);self.term_table=QTableWidget();term_layout.addWidget(self.term_table)
        row=QHBoxLayout();term_layout.addLayout(row)
        self.code=QComboBox();self.code.addItems([t.key for t in CATALOG]);row.addWidget(self.code)
        self.day=QLineEdit('2026-11-10');self.day.setPlaceholderText('Startdatum YYYY-MM-DD');row.addWidget(self.day)
        self.fixed=QLineEdit();self.fixed.setPlaceholderText('Feste IDs, z. B. A,B (Sondertermine)');row.addWidget(self.fixed)
        self.fk_start=QLineEdit();self.fk_start.setPlaceholderText('FK Beginn: YYYY-MM-DDTHH:MM±HH:MM');row.addWidget(self.fk_start)
        self.fk_end=QLineEdit();self.fk_end.setPlaceholderText('FK Ende mit Datum/Offset');row.addWidget(self.fk_end)
        for field in (self.code,self.day,self.fixed,self.fk_start,self.fk_end):field.hide()
        for text,handler in (('Termin hinzufügen',self.add_term_dialog),('LB-Termine ergänzen',self.add_lb_terms),('Termin entfernen',self.remove_term)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));row.addWidget(button)
        term_layout.addWidget(QLabel('Pausen: 0,5 h bei Anwesenheit über 6 h; geschützte Teamzeit bleibt frei. Reserve zählt als normale Arbeitszeit.'))
        self.tabs.addTab(term_page,'Monatstermine')
        import_page=QDialog();import_layout=QVBoxLayout(import_page);bar=QHBoxLayout();import_layout.addLayout(bar)
        bar.addWidget(QLabel('Wunschbudget pro Person (ausdrücklich festlegen): Einzeltage'))
        self.day_budget=QSpinBox();self.day_budget.setRange(0,31);self.day_budget.setValue(2);bar.addWidget(self.day_budget)
        bar.addWidget(QLabel('Wochenenden'));self.weekend_budget=QSpinBox();self.weekend_budget.setRange(0,5);self.weekend_budget.setValue(1);bar.addWidget(self.weekend_budget)
        for text,handler in (('CSV vormerken',self.import_csv),('Gesamten Stapel prüfen und übernehmen',self.promote),('Vormerkung verwerfen',self.discard)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));bar.addWidget(button)
        self.corrections=QTableWidget();import_layout.addWidget(self.corrections)
        self.import_status=QLabel('CSV-Format 2; unzulässige Donnerstagsanteile bleiben bearbeitbar vorgemerkt.');self.import_status.setWordWrap(True);import_layout.addWidget(self.import_status)
        self.active=QTableWidget();import_layout.addWidget(self.active);self.tabs.addTab(import_page,'Urlaub und Wünsche')
        active_bar=QHBoxLayout();import_layout.addLayout(active_bar)
        for text,handler in (('Urlaub oder Freiwunsch hinzufügen',self.manual_entry),('Aktiven Eintrag bearbeiten',self.edit_entry),('Aktiven Eintrag löschen',self.delete_entry)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));active_bar.addWidget(button)
        plan_page=QWidget();plan_box=QVBoxLayout(plan_page)
        self.plan_state=QLabel();self.plan_state.setWordWrap(True);plan_box.addWidget(self.plan_state)
        self.discard_preview=QPushButton('Vorschlag verwerfen und bisherigen Plan anzeigen')
        self.discard_preview.clicked.connect(self.discard_result);plan_box.addWidget(self.discard_preview)
        self.plan=QTableWidget();plan_box.addWidget(self.plan);self.tabs.addTab(plan_page,'Dienstplan')
        self.month_grid=QTableWidget();self.tabs.addTab(self.month_grid,'Monatsübersicht')
        self.hours=QTableWidget();self.tabs.addTab(self.hours,'Stundenprognose')
        self.distribution=QTableWidget();self.tabs.addTab(self.distribution,'Schichtverteilung')
        self.wishes=QTableWidget();self.tabs.addTab(self.wishes,'Freiwünsche')
        leave_page=QWidget();leave_layout=QVBoxLayout(leave_page)
        leave_layout.addWidget(QLabel('Urlaub: 2 Tage Anspruch pro Monat werden angespart; Teilmonate zählen anteilig nach beschäftigten Kalendertagen. Jeder Urlaubstag zählt mit den dann gültigen Wochenstunden ÷ 5. Anfangsbestand und Kontenstart einmalig angeben. Tagesbestände werden hier auf 2 Nachkommastellen angezeigt, intern exakt gerechnet; bestätigte Monate bleiben unverändert.'))
        self.leave_overview=QTableWidget();leave_layout.addWidget(self.leave_overview)
        leave_buttons=QHBoxLayout();leave_layout.addLayout(leave_buttons)
        repair=QPushButton('Fehlende Urlaubstage auswählen');repair.clicked.connect(lambda:self.guard(self.repair_leave));leave_buttons.addWidget(repair)
        account=QPushButton('Urlaubskonto bearbeiten');account.clicked.connect(lambda:self.guard(self.edit_leave_account));leave_buttons.addWidget(account)
        self.tabs.addTab(leave_page,'Urlaubsübersicht')
        status_row=QHBoxLayout();layout.addLayout(status_row)
        self.status=QLabel();self.status.setWordWrap(True);self.status.setMaximumHeight(90);status_row.addWidget(self.status,1)
        self.status_details=QPushButton('Alle Hinweise anzeigen');self.status_details.clicked.connect(self.show_status_details);status_row.addWidget(self.status_details)
        self.status_text=''

        bottom=QHBoxLayout();layout.addLayout(bottom);self.seconds=QSpinBox();self.seconds.setRange(1,600);self.seconds.setValue(60)
        bottom.addWidget(QLabel('Sekunden'));bottom.addWidget(self.seconds)
        self.calculate=QPushButton('Dienstplan erstellen');self.calculate.clicked.connect(lambda:self.guard(self.start));bottom.addWidget(self.calculate)
        self.stop=QPushButton('Abbrechen');self.stop.clicked.connect(self.cancel);self.stop.setEnabled(False);bottom.addWidget(self.stop)
        self.accept=QPushButton('Ergebnis übernehmen');self.accept.clicked.connect(lambda:self.guard(self.apply_result));self.accept.setEnabled(False);bottom.addWidget(self.accept)
        manual_bar=QHBoxLayout();plan_box.addLayout(manual_bar)
        for text,handler in (('Zuteilung ändern',self.change_assignment),('Zuteilung entfernen',self.remove_assignment),('Fixierung umschalten',self.lock_assignment),('Alle manuellen Fixierungen lösen',self.unlock_all)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));manual_bar.addWidget(button)
        for label in self.findChildren(QLabel):label.setWordWrap(True)
        self.tabs.tabBar().moveTab(self.tabs.indexOf(team_page),0)
        self.tabs.tabBar().moveTab(self.tabs.indexOf(leave_page),self.tabs.indexOf(self.hours)+1)
        self.fill();self.tabs.setCurrentWidget(plan_page if self.blocks else team_page)
        try:self.batch=self.store.load_correction('ui-current',budgets=self.budgets(),month=f'{self.inputs.year:04d}-{self.inputs.month:02d}',additional_existing=self.inputs.absences)
        except ValueError:pass
        self.fill_batch()

    def select_calculation_profile(self,index):
        if self.loading:return
        self.dirty();self.refresh_results()

    def guard(self,action):
        try:return action()
        except Exception as exc:QMessageBox.warning(self,'Eingabe prüfen',str(exc))

    def dirty(self,*_):
        if not self.loading:
            had_preview=self.pending is not None
            self.generation+=1;self.pending=None;self.accept.setEnabled(False)
            if had_preview:self.refresh_results()

    def displayed_result(self):
        if self.pending:
            result,_=self.pending
            return result.blocks,result.events,result.proofs
        return self.blocks,self.events,self.proofs

    def discard_result(self):
        self.pending=None;self.accept.setEnabled(False);self.refresh_results()

    def require_accepted_result(self):
        if self.pending:raise ValueError('Zuerst „Ergebnis übernehmen“ wählen oder den angezeigten Vorschlag verwerfen.')

    @staticmethod
    def table(table,header,rows,editable=False):
        from PySide6.QtCore import Qt
        table.setColumnCount(len(header));table.setHorizontalHeaderLabels(header);table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,value in enumerate(row):
                item=QTableWidgetItem(str(value))
                if not editable:item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEditable)
                table.setItem(i,j,item)
        table.resizeColumnsToContents()

    def fill(self):
        self.loading=True
        accounts={a.person_id:a for a in self.profile.accounts}
        def dates_text(span):
            return span.start.strftime('%d.%m.%Y')+' bis '+(span.end-timedelta(days=1)).strftime('%d.%m.%Y')
        names={p.id:p.name for p in self.inputs.people}
        self.table(self.team,('ID (fest)','Name','Wochenstunden (ein Vertrag)','Anfang (h)','Wunschende (h)','Beschäftigung (erster bis letzter Tag)','Ausgeschlossene Dienste'),
                   [(p.id,p.name,contract_text(p.contracts.versions[0].weekly_hours) if len(p.contracts.versions)==1 else 'mehrere Vertragsversionen',hours_text(accounts[p.id].opening_minutes),hours_text(accounts[p.id].desired_minutes),
                     dates_text(p.employment.dates),
                     '; '.join(dates_text(r.dates)+': '+(', '.join(sorted(r.excluded_codes)) or 'keine')+'; Führerschein '+{True:'ja',False:'nein',None:'unbekannt'}[r.driving_license] for r in p.rights)) for p in self.inputs.people],True)
        from PySide6.QtCore import Qt
        for i in range(self.team.rowCount()):
            for j in (0,5,6):self.team.item(i,j).setFlags(self.team.item(i,j).flags()&~Qt.ItemFlag.ItemIsEditable)
            if len(self.inputs.people[i].contracts.versions)>1:self.team.item(i,2).setFlags(self.team.item(i,2).flags()&~Qt.ItemFlag.ItemIsEditable)
        self.table(self.term_table,('Kennung','Beginn Wien','Ende Wien','Plätze','Feste Personen','W16-Grund','Status','Datum · Dienst'),[(e.id,e.attendance.start.astimezone(vienna()).strftime('%H:%M'),e.attendance.end.astimezone(vienna()).strftime('%d.%m. %H:%M'),e.service.staff or 'Teilnahme',', '.join(names.get(pid,pid) for pid in e.fixed_people),e.replacement_reason,('Datumsoption (automatisch)' if e.service.code in {'BK','WL'} else 'Ersatzoption bei Engpass' if e.service.code=='KC15' else 'Reguläre Tagesalternative') if e.id in self.inputs.optional_ids else 'Regulärer / fester Termin',('Mo','Di','Mi','Do','Fr','Sa','So')[e.attendance.start_day.weekday()]+' '+e.attendance.start_day.strftime('%d.%m.%Y')+' · '+e.service.key) for e in self.inputs.events])
        self.term_table.setColumnHidden(0,True)
        self.term_table.horizontalHeader().moveSection(self.term_table.horizontalHeader().visualIndex(7),0)
        self.month_label.setText(f'Monat {self.inputs.month:02d}/{self.inputs.year} · {len(self.inputs.people)} Personen · Änderungen mit „Arbeitsstand speichern“ sichern')
        mode=self.profile.month_profile
        self.calculation_profile.setItemText(0,'Dienst zählt vollständig im Startmonat' if mode=='M1' else 'Historische Buchung nach tatsächlichen Kalendertagen' if mode=='M0' else mode)
        self.calculation_explanation.setText('Monatssoll: gültige Wochenstunden × Kalendertage ÷ 7. '+('Die gesamte bezahlte Schicht wird dem Monat ihres Beginns zugerechnet; Nacht-, Sonn- und Feiertagsmengen zählen weiter nach tatsächlicher Lage.' if mode=='M1' else 'Historischer Stand: Arbeitszeit wird nach ihrer tatsächlichen Lage auf Kalendermonate verteilt. Bestätigte Vergangenheit bleibt unverändert.'))
        recurring={'T':'jeden Donnerstag','TS':'ausgewählte Donnerstage','KC15':'Ersatz für KC10 und KC16 bei notwendiger Besetzung','KC10':'täglich außer Donnerstag','KC16':'täglich außer Donnerstag','W17':'täglich außer Donnerstag','KCT10':'jeden Donnerstag','KCT':'jeden Donnerstag','TW':'jeden Donnerstag','W16':'begründeter Ersatz für W17','WL':'2 Termine/Woche – automatische Wahl','BK':'1 Termin/Woche – automatische Wahl','LB':'14-tägig ab Referenzdatum; feste Personen','VN':'feste Tage und Personen','INT':'2 feste Termine im Monat','N17':'1 fester Termin und Person; Führerschein','R':'24.12.–06.01.; volle normale Arbeitszeit','FK':'individuelle Zeit und feste Person'}
        def times(t):
            if t.start is None:return 'individuell'
            return f'{t.start:%H:%M}–{t.end:%H:%M}'+(' (Folgetag)' if t.end<=t.start else '')
        self.table(self.catalog_table,('Dienst','Uhrzeit Wien','Personen','Auftreten / notwendige Angaben'),[(t.key,times(t),t.staff or 'Teilnahme',recurring[t.code]) for t in CATALOG])
        self.month_notes.setText(f'{len(self.inputs.unchecked)} Hinweise zu den Planungsannahmen · Einzelheiten unten unter „Alle Hinweise anzeigen“.')
        self.day.setText(f'{self.inputs.year:04d}-{self.inputs.month:02d}-10')
        self.table(self.active,('ID','Person','Typ','Beginn','Ende','Gutschrifttage'),[(e.id,next((p.name for p in self.inputs.people if p.id==e.person_id),e.person_id),{'urlaub':'Urlaub','freiwunschtag':'Freiwunsch','wochenendwunsch':'Wochenendwunsch'}[e.kind],e.span.start.astimezone(vienna()).isoformat(),e.span.end.astimezone(vienna()).isoformat(),','.join(map(str,sorted(e.credit_days)))) for e in self.inputs.absences])
        self.active.setColumnHidden(0,True)
        self.loading=False;self.refresh_results()

    def read_team(self):
        from .accounting import MonthAccount
        people=[];accounts=[]
        previous={a.person_id:a for a in self.profile.accounts}
        for i,p in enumerate(self.inputs.people):
            name=self.team.item(i,1).text();contracts=p.contracts
            if len(contracts.versions)==1:
                text=self.team.item(i,2).text().replace(',','.')
                value=exact_hours(Fraction(text)) if '/' in text else exact_hours(text)
                v=contracts.versions[0];contracts=Contracts(p.id,(replace(v,weekly_hours=value),))
            people.append(replace(p,name=name,contracts=contracts))
            accounts.append(MonthAccount(p.id,hours_minutes(self.team.item(i,3).text(),previous=previous[p.id].opening_minutes),hours_minutes(self.team.item(i,4).text(),previous=previous[p.id].desired_minutes)))
        return replace(self.inputs,people=tuple(people)),replace(self.profile,accounts=tuple(accounts))

    def ensure_team_saved(self):
        if self.read_team()!=(self.inputs,self.profile):raise ValueError('Team- und Kontoeingaben zuerst mit „Arbeitsstand speichern“ übernehmen.')

    def clear_plan(self,confirm_only=False):
        if self.blocks and QMessageBox.question(self,'Entwurf nach Eingabeänderung','Diese Eingabe verwirft den angezeigten Entwurf. Gespeicherte Revisionen bleiben erhalten. Fortfahren?')!=QMessageBox.StandardButton.Yes:return False
        if confirm_only:return True
        self.blocks=();self.events=None;self.proofs=();self.dirty();return True

    def add_lb_terms(self):
        from .term_ui import add_missing_lb
        return add_missing_lb(self)

    def add_term_dialog(self):
        from .term_ui import TermDialog
        self.require_accepted_result();self.ensure_team_saved()
        dialog=TermDialog(self)
        if dialog.exec()==QDialog.DialogCode.Accepted:dialog.apply_to(self)

    def add_term(self,*,reason=None):
        self.ensure_team_saved()
        day=date.fromisoformat(self.day.text());key=self.code.currentText()
        if (day.year,day.month)!=(self.inputs.year,self.inputs.month):raise ValueError('Termin muss im geöffneten Monat beginnen.')
        if reason is None and key=='W16':
            reason,ok=QInputDialog.getText(self,'W16','Dokumentierter Ersatzgrund:')
            if not ok:return
        reason=reason or ''
        span=Interval.local(self.fk_start.text(),self.fk_end.text()) if key=='FK' else None
        people=tuple(v.strip() for v in self.fixed.text().split(',') if v.strip())
        try:term=event(key,day,people=people,attendance=span,reason=reason)
        except DomainError:
            # Fachliche Terminregeln sind nach der bestätigten Nutzerregel
            # übersteuerbar. Strukturelle Fehler bleiben auch hier ungültig;
            # change_terms prüft erneut und verlangt ausdrückliche Zustimmung.
            term=event(key,day,people=people,attendance=span,reason=reason,allow_rules=True)
        actual={e.id for e in self.events or ()}
        switchable=any((term.id==g.replacement_id and term.id not in actual) or (term.id in g.regular_ids and g.replacement_id in actual) for g in self.inputs.fallbacks)
        if any(e.id==term.id for e in self.inputs.events) and not switchable:raise ValueError('Dieser Termin existiert bereits.')
        replaced={'TS':{'T'},'T':{'TS'},'W16':{'W17'},'W17':{'W16'},'KC15':{'KC10','KC16'},'KC10':{'KC15'},'KC16':{'KC15'}}.get(key,set())
        removed={e.id for e in self.inputs.events if e.attendance.start_day==day and e.service.key in replaced}
        additions=[term]
        if key in {'T','TS'}:
            for old in self.inputs.events:
                if old.attendance.start_day==day and old.service.code=='LB':
                    removed.add(old.id)
                    additions.append(event('LB_TS' if key=='TS' else 'LB',day,people=old.fixed_people))
        self.change_terms(removed,tuple(additions))

    def change_terms(self,removed,additions=()):
        """Nur betroffene Dienste entfernen; erst nach atomarem Speichern anzeigen."""
        self.require_accepted_result()
        from .fallback import dissolve_fallback_groups
        added_ids={e.id for e in additions}
        keep={e.id for e in self.events or () if e.service.code=='KC15'}
        for group in self.inputs.fallbacks:
            if set(group.regular_ids)&added_ids:keep.discard(group.replacement_id)
        keep.update(e.id for e in additions if e.service.code=='KC15')
        base=dissolve_fallback_groups(self.inputs,set(removed)|added_ids,keep_replacement_ids=keep)
        keep_ids={e.id for e in base.events}-set(removed)-added_ids
        inputs=replace(base,
            events=tuple(e for e in base.events if e.id in keep_ids)+tuple(additions),
            candidates=tuple(b for b in base.candidates if b.id in keep_ids)+service_candidates(additions,base.people),
            locked=tuple(b for b in base.locked if b.id in keep_ids),
            optional_ids=base.optional_ids-set(removed)-added_ids)
        available={e.id for e in inputs.events}
        blocks=tuple(b for b in self.blocks if b.id in available and b.id not in set(removed)|added_ids)
        if additions and len(blocks)<len(self.blocks):
            count=len(self.blocks)-len(blocks)
            if QMessageBox.question(self,'Dienste ersetzen',f'Diese Änderung ersetzt {count} bestehende Zuteilungen der betroffenen Dienste. Alle anderen Dienste bleiben erhalten. Fortfahren?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        events=None
        if self.events is not None:
            chosen={e.id:e for e in self.events if e.id in available and e.id not in set(removed)|added_ids}
            newly_fixed=self.inputs.optional_ids-base.optional_ids
            chosen.update((e.id,e) for e in inputs.events if e.id in newly_fixed and e.id not in inputs.optional_ids)
            chosen.update((e.id,e) for e in additions)
            events=tuple(sorted(chosen.values(),key=lambda e:(e.attendance.start,e.id)))
        messages=()
        if events is None:
            from .validation import check_core
            mandatory=tuple(e for e in inputs.events if e.id not in inputs.optional_ids)
            messages=tuple(i.message for i in check_core(inputs.people,mandatory,(),check_fixed=False).issues)
        else:
            core,calendar=verify_for_planning(inputs,blocks,active_events=events)
            messages=tuple(i.message for i in core.issues+calendar.issues)
            from .automatic_weekly import check_shared_weeks
            try:check_shared_weeks(inputs,blocks,events,self.store.month_snapshots(inputs.year,inputs.month))
            except ValueError as exc:messages+=(str(exc),)
        if messages:
            if not self.confirm_override(messages):return
            inputs=replace(inputs,manual_override=True,override_notes=messages)
        self.store.save_workspace(inputs,self.profile,blocks,events,expected_revision=self.store.input_revision)
        self.inputs,self.blocks,self.events=inputs,blocks,events
        self.proofs=();self.dirty();self.fill()

    def remove_term(self):
        self.ensure_team_saved();self.require_accepted_result()
        row=self.term_table.currentRow()
        if row<0:return
        id=self.term_table.item(row,0).text()
        count=sum(b.id==id for b in self.blocks)
        if QMessageBox.question(self,'Termin entfernen',f'Termin {id} und seine {count} Zuteilungen entfernen? Alle anderen Zuteilungen und Fixierungen bleiben erhalten.')!=QMessageBox.StandardButton.Yes:return
        self.change_terms({id})

    def refresh_results(self):
        blocks,active_events,proofs=self.displayed_result()
        provisional_dates=False
        events=self.inputs.events if active_events is None else active_events
        if active_events is None and self.inputs.optional_ids:
            from .plan_import import selected_events
            events=selected_events(self.inputs);provisional_dates=any(e.id in self.inputs.optional_ids and e.service.code in {'BK','WL'} for e in self.inputs.events)
        preview=self.pending is not None
        self.plan_state.setText('BERECHNETER VORSCHLAG – noch nicht gespeichert. Zum Behalten „Ergebnis übernehmen“ wählen. Der bisherige Plan bleibt bis dahin erhalten.' if preview else
                               'Gespeicherter Plan / Entwurf.' if active_events is not None else 'Vorläufige automatische Termine, noch ohne Zuteilung. BK/WL-Daten bleiben für den Solver verschiebbar.' if provisional_dates else 'Noch kein berechneter Plan. Angezeigt werden die vorgesehenen Plätze.')
        self.discard_preview.setVisible(preview)
        names={p.id:f'{p.name} ({p.id})' for p in self.inputs.people}
        self.plan_rows=[];rows=[]
        for e in events:
            selected=[b for b in blocks if b.id==e.id]
            for i in range(max(e.service.staff or 0,len(selected))):
                b=selected[i] if i<len(selected) else None;self.plan_rows.append((e,b))
                rows.append((e.attendance.start_day.strftime('%d.%m.%Y'),e.service.code,i+1,names.get(b.person_id,b.person_id) if b else 'OFFEN',hours_text(b.work_minutes) if b else '',
                             'fixiert' if self.is_locked(b) else '',
                             '; '.join(p.start.astimezone(vienna()).strftime('%d.%m. %H:%M')+'–'+p.end.astimezone(vienna()).strftime('%d.%m. %H:%M') for p in b.breaks) if b else '',
                             ('Mo','Di','Mi','Do','Fr','Sa','So')[e.attendance.start_day.weekday()],
                             e.attendance.start.astimezone(vienna()).strftime('%H:%M'),e.attendance.end.astimezone(vienna()).strftime('%d.%m. %H:%M')))
        self.table(self.plan,('Termin','Dienst','Platz','Person','Arbeitsstunden (h)','Fixierung','Konkrete Pause','Wochentag','Beginn','Ende'),rows)
        self.plan.horizontalHeader().moveSection(self.plan.horizontalHeader().visualIndex(7),1)
        from .spreadsheets import WEEKDAYS
        import calendar
        from PySide6.QtGui import QColor
        days=[date(self.inputs.year,self.inputs.month,n) for n in range(1,calendar.monthrange(self.inputs.year,self.inputs.month)[1]+1)]
        grid=[]
        for person in self.inputs.people:
            values=[]
            for day in days:
                codes=[b.code for b in blocks if b.person_id==person.id and b.attendance.start_day==day]
                leave=any(e.person_id==person.id and e.kind=='urlaub' and day in {d for d,_ in day_segments(e.span)} for e in self.inputs.absences)
                values.append(' / '.join(codes) if codes else 'U' if leave else '')
            grid.append([person.name+' ('+person.id+')']+values)
        self.table(self.month_grid,('Person',)+tuple(d.strftime('%d.%m.')+' '+WEEKDAYS[d.weekday()] for d in days),grid)
        self.month_grid.setColumnHidden(0,True)
        self.month_grid.setVerticalHeaderLabels([p.name+' ('+p.id+')' for p in self.inputs.people])
        self.month_grid.verticalHeader().setVisible(True)
        for j,day in enumerate(days,1):
            if day.weekday()>=5:
                for i in range(self.month_grid.rowCount()):self.month_grid.item(i,j).setBackground(QColor('#e7eef5'))
        for i,(_,b) in enumerate(self.plan_rows):
            if b is None:self.plan.item(i,3).setBackground(QColor('#ffe4d6'))
        hours=hours_rows(self.inputs.people,blocks+self.inputs.boundary,self.inputs.absences,self.inputs.year,self.inputs.month,accounts=self.profile.accounts,target_profile=self.profile.target_profile,month_profile=self.profile.month_profile)
        profile_selected=True
        self.table(self.hours,('Person','Monatssoll (h)','Anfang (h)','Wunschende (h)','Urlaub (h)','Arbeitsziel (h)','Geplant (h)','Prognose Ende (h)','Abweichung (h)'),[(names.get(r.person_id,r.person_id),hours_text(r.target) if profile_selected else 'Berechnung wählen',hours_text(r.opening),hours_text(r.desired),hours_text(r.credits) if r.credits_known and profile_selected else 'ungeklärt',hours_text(r.goal) if r.credits_known and profile_selected else 'ungeklärt',hours_text(r.work),hours_text(r.projected) if r.credits_known and profile_selected else 'ungeklärt',hours_text(r.deviation) if r.credits_known and profile_selected else 'ungeklärt') for r in hours])
        distribution=shares(self.inputs.people,events,blocks,policy=self.profile.fairness_policy,absences=self.inputs.absences)
        self.table(self.distribution,('Person','Dienst','Anzahl','Stunden (h)','Fairer Anteil Anzahl','Fairer Anteil (h)'),[(names.get(r.person_id,r.person_id),r.code,r.count,hours_text(r.work_minutes),contract_text(r.expected_count),hours_text(r.expected_minutes)) for r in distribution])
        wishes=wish_rows(self.inputs.people,self.inputs.absences,events,blocks+self.inputs.boundary,policy=self.profile.wish_policy,history=self.profile.history)
        self.table(self.wishes,('Person','Relevant','Erfüllt','Übergangen','Historisch','Kumuliert'),[(names.get(r.person_id,r.person_id),len(r.relevant),r.fulfilled_count,len(r.violated),len(r.historical),len(r.cumulative)) for r in wishes])
        if active_events is not None:
            core,calendar=verify(self.inputs,blocks,active_events=active_events)
            wish_notes=wish_warning_messages(self.inputs)
            prefix=('GENEHMIGTE FREIWUNSCH-AUSNAHMEN – Planung unter angepassten Wunschvorgaben. '
                    if wish_notes and not blocking_issues(self.inputs,core.issues) and not calendar.issues else
                    'REGELÜBERSTEUERUNG – kein regelkonformer Plan. ' if self.inputs.manual_override else '')
            status=prefix+('VORSCHAU – noch nicht übernommen. ' if preview else '')+f'{len(blocks)} Zuteilungen; {sum(n for _,n in core.open_slots)} offene Plätze; {sum(p.proven and not p.conditional for p in proofs)} unbedingt bewiesene Zielstufen. '
            status+=' | '.join(dict.fromkeys(tuple(i.message for i in core.issues+calendar.issues)+self.inputs.override_notes))
            status+=' | '+' | '.join(dict.fromkeys(self.inputs.unchecked+calendar.unchecked+self.profile.history.missing))
            status+=' | '+' | '.join(wish_notes)
        else:status=('REGELÜBERSTEUERUNG – '+' | '.join(self.inputs.override_notes)+'. ' if self.inputs.manual_override else '')+'Noch kein berechneter Entwurf. Offene Planungsangaben siehe „Dienste und Einstellungen“.'
        if active_events is None:status+=' | '+' | '.join(dict.fromkeys(self.inputs.unchecked+self.profile.history.missing))
        from .fallback import fallback_notes
        fallback_messages=fallback_notes(self.inputs,events)
        # Auch ein ausdrücklich eingetragener KC15 bleibt als Ersatz erkennbar.
        replacement_count=sum(e.service.code=='KC15' for e in events)
        if replacement_count:
            status=f'{replacement_count} KC15-Ersatztermine statt regulärer KC10/KC16-Besetzung. '+status
            status+=' | '+' | '.join(fallback_messages)
        required=sum((e.service.staff or 0)*(e.attendance.minutes-(30 if e.attendance.minutes>360 else 0)) for e in events)
        target=sum(max(0,r.goal) for r in hours) if all(r.credits_known for r in hours) else None
        status+=(' | Vorläufige Datumswahl; tatsächliche Dauer kann sich durch Terminwahl an Zeitumstellungstagen ändern.' if provisional_dates else '')
        lower,upper=required_work_range(events,blocks,self.inputs.year,self.inputs.month,boundary=self.inputs.boundary,include_reserve=True)
        monthly=hours_text(lower) if lower==upper else hours_text(lower)+'–'+hours_text(upper)
        status+=f' | Operativer Bedarf im Planungshorizont: {hours_text(required)} h. Tatsächliche Arbeit im Kalendermonat inkl. Randdienste: {monthly} h; nicht negatives Arbeitsziel im Monat: '+(f'{hours_text(target)} h.' if target is not None else 'ungeklärt.')
        confirmed=self.store.confirmed_month(self.inputs.year,self.inputs.month)
        if confirmed:
            status=('MONAT BESTÄTIGT MIT ABWEICHUNGEN. ' if confirmed.get('confirmation_override') else 'MONAT BESTÄTIGT. ')+status
            status+=' | '+' | '.join(confirmed.get('warnings',()))
        from .leave import monthly_leave_rows
        leave_rows=monthly_leave_rows(self.inputs.people,self.inputs.absences,self.inputs.year,self.inputs.month)
        from .leave_accounts import leave_account_rows
        balances={r.person_id:r for r in leave_account_rows(self.store,self.inputs.people,self.inputs.year,self.inputs.month,current_entries=self.inputs.absences)}
        def days(value):
            from decimal import Decimal
            return format(Decimal(value.numerator)/Decimal(value.denominator),'.2f').replace('.',',') if value is not None else 'noch offen'
        self.table(self.leave_overview,('Person','Kontostart','Anfang am Kontostart (Tage)','Erworben seit Start (Tage)','Genommen seit Start (Tage)','Urlaubstage im Monat','Voraussichtlicher Rest (Tage)','Gutschrift im Monat (h)','Hinweise'),[
            (r.person_name+' ('+r.person_id+')',balances[r.person_id].start_month or 'Konto einrichten',days(balances[r.person_id].opening_days),days(balances[r.person_id].earned_days),days(balances[r.person_id].used_days),r.used_days if r.credits_known else str(r.used_days)+' + Auswahl fehlt',days(balances[r.person_id].projected_days),hours_text(r.credit_minutes) if r.credits_known else 'Tage auswählen','; '.join(r.diagnostics+balances[r.person_id].diagnostics) or 'Vollständig') for r in leave_rows])
        self.set_status(status)

    def set_status(self,status):
        self.status_text=status
        parts=tuple(dict.fromkeys(p.strip() for p in status.split(' | ') if p.strip()))
        summary=parts[0] if parts else ''
        if len(summary)>340:summary=summary[:337]+'…'
        for important in ('Noch keine Person zugeteilt; Zeitlimit und Eingaben prüfen.','Kein vollständiger Optimalitätsnachweis.','Alle gewählten Zielstufen bewiesen.'):
            if important in status and important not in summary:summary+=' '+important
        if len(parts)>1:summary+=f' · {len(parts)-1} weitere Hinweise'
        self.status.setText(summary)
        self.status.setToolTip('Vollständige Meldungen: „Alle Hinweise anzeigen“.')
        self.status_details.setEnabled(bool(status))

    def show_status_details(self):
        dialog=QDialog(self);dialog.setWindowTitle('Planungsstatus und Hinweise');dialog.resize(850,550)
        layout=QVBoxLayout(dialog);text=QPlainTextEdit();text.setReadOnly(True)
        text.setPlainText('\n\n'.join(dict.fromkeys(p.strip() for p in self.status_text.split(' | ') if p.strip())))
        layout.addWidget(text);close=QPushButton('Schließen');close.clicked.connect(dialog.accept);layout.addWidget(close);dialog.exec()

    def reviewed_inputs(self,inputs,blocks,events):
        if events is None:return inputs
        core,calendar=verify_for_planning(inputs,blocks,active_events=events)
        messages=tuple(i.message for i in core.issues+calendar.issues)
        from .automatic_weekly import check_shared_weeks
        try:check_shared_weeks(inputs,blocks,events,self.store.month_snapshots(inputs.year,inputs.month))
        except ValueError as exc:messages+=(str(exc),)
        if messages:
            if not self.confirm_override(messages):return None
            inputs=replace(inputs,manual_override=True,override_notes=tuple(dict.fromkeys(inputs.override_notes+messages)))
        return inputs

    def save(self):
        inputs,profile=self.read_team()
        changed=(inputs,profile)!=(self.inputs,self.profile)
        inputs=self.reviewed_inputs(inputs,self.blocks,self.events)
        if inputs is None:return False
        self.store.save_workspace(inputs,profile,self.blocks,self.events,expected_revision=self.store.input_revision)
        self.inputs,self.profile=inputs,profile
        if changed:self.proofs=()
        self.fill();return True

    def new_file(self):
        self.require_accepted_result()
        if self.worker and self.worker.isRunning():raise ValueError('Berechnung zuerst abbrechen.')
        path,_=QFileDialog.getSaveFileName(self,'Arbeitsstand in neue Dienstplandatei kopieren','','SQLite (*.sqlite3)')
        if not path:return
        inputs,profile=self.read_team()
        inputs=self.reviewed_inputs(inputs,self.blocks,self.events)
        if inputs is None:return
        from .leave_accounts import leave_account_settings,save_leave_account
        accounts=leave_account_settings(self.store)
        new=V2Store(path,create=True)
        try:
            new.save_workspace(inputs,profile,self.blocks,self.events,expected_revision=0)
            for setting in accounts.values():save_leave_account(new,setting.person_id,setting.start_month,setting.opening_days,expected_revision=new.input_revision)
        except Exception:
            new.close();Path(path).unlink(missing_ok=True);raise
        self.store.close();self.store=new;self.inputs,self.profile=inputs,profile;self.proofs=();self.location.setText(path);self.dirty();self.fill()
        self.batch=None;self.fill_batch()

    def open_file(self):
        if self.worker and self.worker.isRunning():raise ValueError('Berechnung zuerst abbrechen.')
        path,_=QFileDialog.getOpenFileName(self,'Dienstplandatei öffnen (V2-Format)','','SQLite (*.sqlite3)')
        if not path:return
        new=V2Store(path)
        try:
            months=[r[0].removeprefix('workspace:') for r in new.connection.execute("SELECT key FROM v2_meta WHERE key LIKE 'workspace:%' ORDER BY key")]
            if not months:raise ValueError('Datei enthält noch keinen V2-Arbeitsstand.')
            month,ok=QInputDialog.getItem(self,'Monat','Monat wählen:',months,0,False)
            if not ok:new.close();return
            inputs,profile,blocks,events=new.load_workspace(*map(int,month.split('-')))
        except Exception:new.close();raise
        self.store.close();self.store=new;self.inputs,self.profile,self.blocks,self.events=inputs,profile,blocks,events
        self.proofs=();self.location.setText(path);self.dirty();self.fill()
        try:self.batch=self.store.load_correction('ui-current',budgets=self.budgets(),month=month,additional_existing=self.inputs.absences)
        except ValueError:self.batch=None
        self.fill_batch()

    def new_month(self):
        if self.worker and self.worker.isRunning():raise ValueError('Berechnung zuerst abbrechen.')
        self.ensure_team_saved()
        value,ok=QInputDialog.getText(self,'Monat wählen','Monat YYYY-MM (neuer Monat übernimmt Personen und enthält die Standarddienste):')
        if not ok:return
        year,month=map(int,value.split('-'));date(year,month,1)
        loaded=self.store.load_workspace(year,month)
        if loaded:self.inputs,self.profile,self.blocks,self.events=loaded
        else:
            inputs,profile,_=standard_month(year,month,people=self.inputs.people,accounts=tuple(replace(a,desired_minutes=0) for a in self.profile.accounts),absences=self.inputs.absences)
            if self.inputs.week_policy is not None and self.inputs.week_policy.label.startswith('Betriebliche Eingabe:'):
                from .automatic_weekly import automatic_weekly
                inputs=automatic_weekly(inputs,snapshots=self.store.month_snapshots(inputs.year,inputs.month),full_weeks_only='nur volle' in self.inputs.week_policy.label)
            records=self.store.confirmations();month_key=f'{year:04d}-{month:02d}'
            history=self.store.wish_history(month_key,policy=profile.wish_policy)
            earlier=[v for _,v in records if v['month']<month_key]
            from .accounting import MonthAccount
            balances={r['person_id']:r['projected'] for r in max(earlier,key=lambda v:v['month'])['hours']} if earlier else {}
            profile=replace(profile,history=history,historical_shares=historical_shares(records,start=profile.wish_policy.history_start,month=month_key),
                            accounts=tuple(MonthAccount(p.id,balances.get(p.id,next((a.opening_minutes for a in self.profile.accounts if a.person_id==p.id),0))) for p in inputs.people))
            self.store.save_workspace(inputs,profile,expected_revision=self.store.input_revision)
            self.inputs,self.profile,self.blocks,self.events=inputs,profile,(),None
        self.proofs=();self.dirty();self.fill()

    def person_details(self):
        self.ensure_team_saved();row=self.team.currentRow()
        if row<0:raise ValueError('Zuerst eine Person in der Teamtabelle wählen.')
        self.edit_person(self.inputs.people[row])

    def add_person(self):
        self.ensure_team_saved()
        id,ok=QInputDialog.getText(self,'Stabile Person','Neue eindeutige Personenkennung:')
        if not ok:return
        if not id.strip() or any(p.id==id for p in self.inputs.people):raise ValueError('Kennung fehlt oder existiert bereits.')
        self.edit_person(None,id)

    def edit_person(self,person,new_id=None):
        from datetime import timedelta
        from .contracts import DateRange,Employment
        from .people import Eligibility,Person
        from .accounting import MonthAccount
        from .person_ui import date_edit,displayed_date,parsed_date,InclusiveDateDelegate,DriverDelegate
        self.require_accepted_result()
        dialog=QDialog(self);dialog.setWindowTitle('Person und gültige Vertragszeiten');box=QVBoxLayout(dialog)
        name=QLineEdit(person.name if person else '');name.setObjectName('person_name')
        start=date_edit(person.employment.dates.start if person else None,'person_employment_first')
        end=date_edit(person.employment.dates.end-timedelta(days=1) if person else None,'person_employment_last')
        for label,widget in (('Name',name),('Erster Beschäftigungstag',start),('Letzter Beschäftigungstag (einschließlich)',end)):
            box.addWidget(QLabel(label));box.addWidget(widget)
        help=QLabel('Alle letzten Tage sind eingeschlossen. Beispiel: Ein Ende am 31.12. bedeutet, dass der gesamte 31.12. noch zur Beschäftigung bzw. Vertragsversion gehört. Datumszellen lassen sich per Doppelklick im Kalender bearbeiten.');help.setWordWrap(True);box.addWidget(help)
        contracts=QTableWidget();rights=QTableWidget();contracts.setObjectName('person_contract_versions');rights.setObjectName('person_exclusion_versions')
        self.table(contracts,('Gültig ab','Letzter gültiger Tag (einschließlich)','Wochenstunden'),[(displayed_date(c.dates.start),displayed_date(c.dates.end-timedelta(days=1)),contract_text(c.weekly_hours)) for c in person.contracts.versions] if person else [('', '', '')],True)
        self.table(rights,('Gültig ab','Letzter gültiger Tag (einschließlich)','Ausgeschlossene Dienste','Führerschein'),[(displayed_date(r.dates.start),displayed_date(r.dates.end-timedelta(days=1)),' '.join(sorted(r.excluded_codes)),{True:'ja',False:'nein',None:'unbekannt'}[r.driving_license]) for r in person.rights] if person else [('', '', '', 'unbekannt')],True)
        for table in (contracts,rights):
            for col in (0,1):table.setItemDelegateForColumn(col,InclusiveDateDelegate(table))
        rights.setItemDelegateForColumn(3,DriverDelegate(rights))
        filling=False;automatic={(id(t),0,c) for t in (contracts,rights) for c in (0,1)} if not person else set()
        def user_edit(table,item):
            if not filling:automatic.discard((id(table),item.row(),item.column()))
        contracts.itemChanged.connect(lambda item:user_edit(contracts,item));rights.itemChanged.connect(lambda item:user_edit(rights,item))
        def sync_dates(*_):
            nonlocal filling
            filling=True
            for table in (contracts,rights):
                for row in range(table.rowCount()):
                    for col,field in ((0,start),(1,end)):
                        if (id(table),row,col) in automatic:
                            table.item(row,col).setText(displayed_date(field.date().toPython()) if field.date()!=field.minimumDate() else '')
            filling=False
        start.dateChanged.connect(sync_dates);end.dateChanged.connect(sync_dates)
        for label,table in (('Wochenstunden und ihre Gültigkeit',contracts),('Dienstausschlüsse und Führerschein – leer bedeutet keine ausgeschlossenen Dienste',rights)):
            box.addWidget(QLabel(label));box.addWidget(table);bar=QHBoxLayout();box.addLayout(bar)
            add=QPushButton('Version ergänzen');remove=QPushButton('Gewählte Version entfernen');bar.addWidget(add);bar.addWidget(remove)
            def append(t=table):
                row=t.rowCount();t.insertRow(row)
                for col in range(t.columnCount()):t.setItem(row,col,QTableWidgetItem('unbekannt' if t is rights and col==3 else ''))
                if row==0:
                    automatic.update((id(t),row,col) for col in (0,1));sync_dates()
                t.setCurrentCell(row,0)
            add.clicked.connect(lambda checked=False,f=append:f())
            def remove_version(t=table):
                nonlocal filling
                row=t.currentRow()
                if row<0:return
                moved={(table_id,index-1 if table_id==id(t) and index>row else index,col)
                       for table_id,index,col in automatic if table_id!=id(t) or index!=row}
                filling=True
                try:
                    t.removeRow(row);automatic.clear();automatic.update(moved)
                finally:filling=False
            remove.clicked.connect(lambda checked=False,f=remove_version:f())
        choose=QPushButton('Ausgeschlossene Dienste auswählen');box.addWidget(choose)
        def choose_exclusions():
            row=rights.currentRow()
            if row<0:row=0
            if rights.rowCount()==0:raise ValueError('Zuerst eine Ausschlussversion ergänzen.')
            selected=self.choose_exclusions(rights.item(row,2).text().split())
            if selected is not None:rights.item(row,2).setText(' '.join(sorted(selected)))
        choose.clicked.connect(lambda:self.guard(choose_exclusions))
        buttons=QHBoxLayout();box.addLayout(buttons)
        commit=QPushButton('Personendaten prüfen und übernehmen');buttons.addWidget(commit)
        cancel=QPushButton('Abbrechen');cancel.clicked.connect(dialog.reject);buttons.addWidget(cancel)
        def apply():
            pid=person.id if person else new_id
            def values(table,row):return [table.item(row,col).text().strip() for col in range(table.columnCount())]
            def span(a,z):return DateRange(parsed_date(a),parsed_date(z)+timedelta(days=1))
            if not person and (start.date()==start.minimumDate() or end.date()==end.minimumDate()):raise ValueError('Bitte ersten und letzten Beschäftigungstag ausdrücklich im Kalender auswählen.')
            versions=[];permissions=[]
            for i in range(contracts.rowCount()):
                a,z,w=values(contracts,i)
                if not w:raise ValueError('Bitte die Wochenstunden jeder Vertragsversion eingeben.')
                versions.append(Contract(pid,span(a,z),exact_hours(Fraction(w.replace(',','.')))))
            for i in range(rights.rowCount()):
                a,z,codes,driver=values(rights,i)
                if driver not in {'ja','nein','unbekannt'}:raise ValueError('Führerschein ausdrücklich ja, nein oder unbekannt.')
                if not set(codes.split())<={t.code for t in CATALOG}:raise ValueError('Unbekanntes Dienstkürzel bei ausgeschlossenen Diensten.')
                excluded=frozenset(codes.split());license_value={'ja':True,'nein':False,'unbekannt':None}[driver]
                original=person.rights[i] if person and i<len(person.rights) else None
                if original is not None and excluded==original.excluded_codes:
                    permissions.append(Eligibility(span(a,z),original.codes,license_value))
                else:permissions.append(Eligibility.from_exclusions(span(a,z),excluded,license_value))
            employment=DateRange(start.date().toPython(),end.date().toPython()+timedelta(days=1))
            updated=Person(pid,name.text(),Employment(pid,employment),Contracts(pid,tuple(versions)),tuple(permissions))
            if person is not None and updated==person:
                dialog.accept();return
            from .accounting import s0_target
            s0_target(updated.contracts,updated.employment,self.inputs.year,self.inputs.month,profile='S0')
            people=tuple(updated if p.id==pid else p for p in self.inputs.people) if person else self.inputs.people+(updated,)
            candidates=tuple(c for c in self.inputs.candidates if c.person_id!=pid)
            for term in self.inputs.events:
                if updated.eligibility_errors(term.service.code,term.attendance) or (term.fixed_people and pid not in term.fixed_people):continue
                candidates+=pause_candidates(term,pid,policy=PausePolicy('Pausenraster 0,5 h; Abdeckung ungeklärt',(term.attendance,),30))
            from .calendar_rules import dates
            current=DateRange(date(self.inputs.year,self.inputs.month,1),date(self.inputs.year+int(self.inputs.month==12),self.inputs.month%12+1,1))
            known=self.inputs.known_days|frozenset((pid,d) for d in dates(current))
            inputs=replace(self.inputs,people=people,candidates=candidates,known_days=known)
            inputs=self.reviewed_inputs(inputs,self.blocks,self.events)
            if inputs is None:return
            profile=self.profile if person else replace(self.profile,accounts=self.profile.accounts+(MonthAccount(pid,0),))
            self.store.save_workspace(inputs,profile,self.blocks,self.events,expected_revision=self.store.input_revision)
            self.inputs,self.profile=inputs,profile;self.proofs=();self.dirty();self.fill();dialog.accept()
        commit.clicked.connect(lambda:self.guard(apply));dialog.resize(950,760);dialog.exec()

    def choose_exclusions(self,excluded):
        from PySide6.QtCore import Qt
        dialog=QDialog(self);dialog.setWindowTitle('Dienste ausschließen');box=QVBoxLayout(dialog)
        box.addWidget(QLabel('Angehakte Dienste sind für diese Person ausgeschlossen.'))
        choices=QListWidget();box.addWidget(choices)
        for code in sorted({t.code for t in CATALOG}):
            item=QListWidgetItem(code);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if code in excluded else Qt.CheckState.Unchecked);choices.addItem(item)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);box.addWidget(buttons)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return None
        return frozenset(choices.item(i).text() for i in range(choices.count()) if choices.item(i).checkState()==Qt.CheckState.Checked)

    def start(self):
        if self.worker and self.worker.isRunning():return
        if not self.inputs.people:raise ValueError('Zuerst mindestens eine Person erfassen.')
        if self.save() is False:return
        if self.inputs.profile_label in (OPEN_PROFILE,SELECTED_PROFILE) and self.inputs.week_policy is None:
            self.configure_weekly()
            if self.inputs.week_policy is None:return
        self.discard_result()
        token=(self.generation,self.store.input_revision,self.inputs.fingerprint,fingerprint(self.profile))
        events=self.events if self.events is not None else (self.inputs.events if not self.inputs.optional_ids else None)
        self.worker=Worker(self.inputs,self.profile,self.blocks,events,self.seconds.value(),token,self)
        self.worker.completed.connect(self.on_worker_completed);self.worker.failed.connect(lambda error:self.set_status('Berechnung fehlgeschlagen: '+error))
        self.worker.finished.connect(lambda:(self.calculate.setEnabled(True),self.stop.setEnabled(False)))
        self.calculate.setEnabled(False);self.stop.setEnabled(True);self.set_status('Berechnung läuft; Eingabeänderungen machen das Ergebnis veraltet.');self.worker.start()

    def on_worker_completed(self,result,token):
        current=(self.generation,self.store.input_revision,self.inputs.fingerprint,fingerprint(self.profile))
        if current!=token:self.set_status('Eingaben geändert: Ergebnis veraltet und nicht übernommen.');return
        if result.status in {'unknown','cancelled','infeasible','invalid'}:
            headings={'unknown':'Innerhalb des Zeitlimits wurde noch kein gültiger neuer Vorschlag gefunden.',
                      'cancelled':'Die Berechnung wurde abgebrochen.',
                      'infeasible':'Die fixierten Vorgaben lassen sich so nicht gemeinsam planen.',
                      'invalid':'Die Planungsvorgaben enthalten einen Fehler.'}
            details=tuple(dict.fromkeys(self.describe_issue(i) for i in result.issues))
            message=headings[result.status]+(' '+details[0] if details else '')
            self.set_status(message+' | Der bisherige Dienstplan bleibt erhalten.'+(' | '+' | '.join(details[1:]) if len(details)>1 else '')+
                            (' | Betroffene Zuteilung im Dienstplan prüfen, ändern oder deren Fixierung lösen.' if result.issues else '')+
                            (' | '+' | '.join(result.unchecked) if result.unchecked else ''));return
        core,calendar=verify_for_planning(self.inputs,result.blocks,active_events=result.events)
        if not core.hard_ok or not calendar.hard_ok:
            self.set_status('Berechneter Vorschlag verletzt verbindliche Regeln und wird nicht angezeigt.');return
        self.pending=(result,token);self.accept.setEnabled(True)
        self.refresh_results();self.tabs.setCurrentWidget(self.plan.parentWidget())
        self.set_status(self.status_text+' '+('Alle gewählten Zielstufen bewiesen.' if result.global_optimal else 'Kein vollständiger Optimalitätsnachweis.')+
                            (' Noch keine Person zugeteilt; Zeitlimit und Eingaben prüfen.' if not result.blocks else ''))

    def describe_issue(self,issue):
        """Person und Dienst statt einer pauschalen Fixierungsfehlermeldung."""
        person=next((p for p in self.inputs.people if p.id==issue.person_id),None)
        term=next((e for e in self.inputs.events if e.id==issue.event_id),None)
        scope=[]
        if person:scope.append(person.name+' ('+person.id+')')
        elif issue.person_id:scope.append(issue.person_id)
        if term:
            scope.append(term.attendance.start_day.strftime('%d.%m.%Y')+' · '+term.service.key)
        elif issue.event_id:
            entry=next((e for e in self.inputs.absences if e.id==issue.event_id),None)
            scope.append(entry.span.start_day.strftime('%d.%m.%Y') if entry else issue.event_id)
        message=issue.message
        if issue.rule=='rest':
            import re
            match=re.fullmatch(r'Nur (\d+) Minuten Ruhe seit (.+); benötigt (\d+), fehlen (\d+)\.',message)
            if match:message=f'Nur {hours_text(int(match[1]))} h Ruhe seit {match[2]}; benötigt {hours_text(int(match[3]))} h, fehlen {hours_text(int(match[4]))} h.'
        return (' · '.join(scope)+': ' if scope else '')+message

    def apply_result(self):
        if not self.pending:return
        result,token=self.pending
        if token!=(self.generation,self.store.input_revision,self.inputs.fingerprint,fingerprint(self.profile)):raise ValueError('Ergebnis ist veraltet.')
        core,calendar=verify_for_planning(self.inputs,result.blocks,active_events=result.events)
        if not core.hard_ok or not calendar.hard_ok:raise ValueError('Ergebnis verletzt verbindliche Regeln.')
        self.store.save_workspace(self.inputs,self.profile,result.blocks,result.events,expected_revision=token[1])
        self.blocks,self.events,self.proofs=result.blocks,result.events,result.proofs;self.pending=None;self.accept.setEnabled(False);self.refresh_results()

    def cancel(self):
        if self.worker:self.worker.cancel.set()

    def selected(self):
        self.require_accepted_result()
        row=self.plan.currentRow()
        if row<0:raise ValueError('Zuerst eine Planzeile wählen.')
        return self.plan_rows[row]

    def is_locked(self,block):
        return block is not None and any((b.id,b.person_id)==(block.id,block.person_id) for b in self.inputs.locked)

    def manual_context(self,blocks,locked=None):
        inputs=self.inputs if locked is None else replace(self.inputs,locked=tuple(locked))
        # Manuelle Bearbeitung verändert die gewählten Termine niemals nebenbei.
        if self.events is not None:return inputs,self.events
        if inputs.optional_ids:
            from .plan_import import selected_events
            weekly={e.id for e in inputs.events if e.service.code in {'BK','WL'}}
            selection=replace(inputs,optional_ids=inputs.optional_ids-({b.id for b in blocks}&weekly))
            try:events=selected_events(selection)
            except ValueError:
                events=tuple(e for e in inputs.events if e.id not in selection.optional_ids)
        else:events=inputs.events
        return inputs,events

    def confirm_override(self,messages,*,confirmation=False):
        box=QMessageBox(self)
        box.setWindowTitle('Monat trotz Abweichungen bestätigen' if confirmation else 'Regeln ausdrücklich übergehen')
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText('Diesen Monat trotz der aufgeführten Abweichungen unveränderlich bestätigen? Die Hinweise bleiben gespeichert; die Bestätigung ist kein Nachweis der Regelkonformität.' if confirmation else 'Trotz Regelverstößen übernehmen? Der Plan bleibt als Regelabweichung gekennzeichnet; der automatische Solver erhält dadurch keine Erlaubnis, Regeln zu verletzen.')
        box.setInformativeText('\n'.join(messages[:5]))
        box.setDetailedText('\n'.join(messages) or 'Ausdrücklich gewählte Regelübersteuerung.')
        box.setStandardButtons(QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        return box.exec()==QMessageBox.StandardButton.Yes

    def manual(self,blocks,locked=None):
        self.require_accepted_result()
        self.ensure_team_saved()
        inputs,events=self.manual_context(blocks,locked)
        core,calendar=verify(inputs,blocks,active_events=events)
        allowed=accepted_wish_warnings(inputs,core.issues)
        messages=tuple(i.message for i in blocking_issues(inputs,core.issues)+calendar.issues)
        from .automatic_weekly import check_shared_weeks
        try:check_shared_weeks(inputs,blocks,events,self.store.month_snapshots(inputs.year,inputs.month))
        except ValueError as exc:messages+=(str(exc),)
        if messages:
            if not self.confirm_override(messages):return
            inputs=replace(inputs,manual_override=True,override_notes=tuple(dict.fromkeys(messages+tuple(i.message for i in allowed))))
        elif allowed:inputs=replace(inputs,manual_override=True,override_notes=tuple(i.message for i in allowed))
        else:inputs=replace(inputs,manual_override=False,override_notes=())
        self.store.save_workspace(inputs,self.profile,blocks,events,expected_revision=self.store.input_revision)
        self.inputs,self.blocks,self.events=inputs,tuple(blocks),events;self.proofs=();self.dirty();self.refresh_results()

    def change_assignment(self):
        term,old=self.selected()
        occupied={b.person_id for b in self.blocks if b.id==term.id and b!=old}
        people=[p for p in self.inputs.people if p.id not in occupied]
        labels=[p.name+' ('+p.id+')' for p in people]
        if not labels:raise ValueError('Alle Personen sind diesem Termin bereits zugeteilt.')
        label,ok=QInputDialog.getItem(self,'Zuteilung','Person wählen; Pause wird automatisch passend gesetzt:',labels,0,False)
        if not ok:return
        from .pauses import automatic_pause_choices
        pid=people[labels.index(label)].id
        if old is not None and pid==old.person_id:return
        fixed=self.is_locked(old)
        if fixed and QMessageBox.question(self,'Fixierte Zuteilung ändern','Die bisherige Fixierung aufheben und die neue Person fixieren?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        base=tuple(b for b in self.blocks if b!=old)
        remaining_locks=tuple(b for b in self.inputs.locked if (b.id,b.person_id)!=(old.id,old.person_id)) if old is not None else self.inputs.locked
        choices=automatic_pause_choices(term,pid,allow_rules=True)
        for choice in choices:
            locks=remaining_locks+(choice,) if fixed else self.inputs.locked
            inputs,events=self.manual_context(base+(choice,),locks)
            core,calendar=verify_for_planning(inputs,base+(choice,),active_events=events)
            if core.hard_ok and calendar.hard_ok:
                self.manual(base+(choice,),locks);return
            if calendar.issues or any(i.rule!='working_coverage' for i in core.issues):break
        if not choices:raise ValueError('Keine technisch gültige Pause möglich.')
        locks=remaining_locks+(choices[0],) if fixed else self.inputs.locked
        self.manual(base+(choices[0],),locks)

    def remove_assignment(self):
        _,old=self.selected()
        if old:
            if self.is_locked(old) and QMessageBox.question(self,'Fixierte Zuteilung entfernen','Diese Zuteilung einschließlich ihrer Fixierung entfernen? Alle anderen Dienste bleiben erhalten.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
            self.manual(tuple(b for b in self.blocks if b!=old),tuple(b for b in self.inputs.locked if (b.id,b.person_id)!=(old.id,old.person_id)))

    def lock_assignment(self):
        _,old=self.selected()
        if old:self.manual(self.blocks,tuple(b for b in self.inputs.locked if (b.id,b.person_id)!=(old.id,old.person_id)) if self.is_locked(old) else self.inputs.locked+(old,))

    def unlock_all(self):
        self.require_accepted_result()
        self.ensure_team_saved()
        inputs=replace(self.inputs,locked=())
        self.store.save_workspace(inputs,self.profile,self.blocks,self.events,expected_revision=self.store.input_revision)
        self.inputs=inputs;self.proofs=();self.dirty();self.refresh_results()

    def budgets(self):return {(p.id,f'{self.inputs.year:04d}-{self.inputs.month:02d}'):WishBudget(self.day_budget.value(),self.weekend_budget.value()) for p in self.inputs.people}

    def fill_batch(self):
        if not self.batch:
            self.corrections.setRowCount(0);self.import_status.setText('Keine CSV-Korrektur vorgemerkt.');return
        self.batch_headers=tuple(dict(r.fields) for r in self.batch.rows)
        fields=tuple(dict(self.batch.rows[0].fields)) if self.batch.rows else ()
        self.correction_fields=fields
        self.table(self.corrections,('Zeile',)+fields+('Fehler',),[(r.line,)+tuple(dict(r.fields).get(key,'') for key in fields)+('; '.join(r.errors),) for r in self.batch.rows],True)
        replacement=self.store.correction_replaces('ui-current')
        self.import_status.setText('Korrekturvormerkung – keine aktive Teilübernahme. '+(f'Ersetzt nach vollständiger Prüfung: {replacement}. ' if replacement else '')+'; '.join(self.batch.errors+self.batch.parse_errors))

    def import_csv(self):
        path,_=QFileDialog.getOpenFileName(self,'CSV-Format 2 vormerken','','CSV (*.csv)')
        if not path:return
        self.batch=preview(Path(path).read_text(encoding='utf-8-sig'),existing=self.inputs.absences+self.store.entries(),budgets=self.budgets(),month=f'{self.inputs.year:04d}-{self.inputs.month:02d}')
        self.store.save_correction('ui-current',self.batch,replaces='');self.fill_batch()

    def promote(self):
        if not self.batch:return
        self.require_accepted_result()
        self.ensure_team_saved()
        for i,row in enumerate(self.batch.rows):
            changes={key:self.corrections.item(i,j+1).text() for j,key in enumerate(self.correction_fields)}
            self.batch=correct(self.batch,row.line,changes,existing=self.store.correction_existing('ui-current',self.inputs.absences),budgets=self.budgets(),month=f'{self.inputs.year:04d}-{self.inputs.month:02d}')
        self.store.save_correction('ui-current',self.batch);self.fill_batch()
        allow_rules=False
        if not self.batch.ready:
            if not self.confirm_override(self.batch.errors+tuple(e for r in self.batch.rows for e in r.errors)):return
            allow_rules=True
            self.batch=self.store.load_correction('ui-current',budgets=self.budgets(),month=f'{self.inputs.year:04d}-{self.inputs.month:02d}',additional_existing=self.inputs.absences,allow_rules=True)
            if not self.batch.ready:raise ValueError('Technisch ungültige Angaben bleiben zur Korrektur vorgemerkt: '+'; '.join(self.batch.errors+tuple(e for r in self.batch.rows for e in r.errors)))
        entries=self.batch.promote();replaces=self.store.correction_replaces('ui-current')
        merged={e.identity:e for e in tuple(e for e in self.inputs.absences if e.id!=replaces)+entries}
        checked=replace(self.inputs,absences=tuple(merged.values()))
        if self.events is not None:
            core,calendar=verify_for_planning(checked,self.blocks,active_events=self.events)
            messages=tuple(i.message for i in core.issues+calendar.issues)
            if messages and not allow_rules:
                if not self.confirm_override(messages):return
                allow_rules=True
        self.inputs=self.store.apply_correction('ui-current',self.inputs,self.profile,budgets=self.budgets(),expected_revision=self.store.input_revision,allow_rules=allow_rules,blocks=self.blocks,events=self.events)
        self.proofs=();self.dirty()
        self.batch=None;self.fill_batch();self.fill()

    def discard(self):
        self.store.discard_correction('ui-current');self.batch=None;self.fill_batch();self.import_status.setText('Vormerkung verworfen. Aktive Eingaben unverändert.')

    def selected_entry(self):
        row=self.active.currentRow()
        if row<0:raise ValueError('Zuerst einen aktiven Eintrag wählen.')
        id=self.active.item(row,0).text()
        return next(e for e in self.inputs.absences if e.id==id)

    def edit_entry(self):self.manual_entry(self.selected_entry())

    def edit_leave_account(self):
        from .leave_accounts import leave_account_settings,save_leave_account
        from PySide6.QtWidgets import QDateEdit,QFormLayout
        from PySide6.QtCore import QDate
        self.require_accepted_result();self.ensure_team_saved()
        dialog=QDialog(self);dialog.setWindowTitle('Urlaubskonto: Anfangsbestand und Beginn');dialog.resize(640,360)
        layout=QVBoxLayout(dialog);form=QFormLayout();layout.addLayout(form)
        person=QComboBox();person.setObjectName('leave_account_person')
        for p in self.inputs.people:person.addItem(p.name+' ('+p.id+')',p.id)
        row=self.leave_overview.currentRow()
        if row>=0:person.setCurrentIndex(row)
        start=QDateEdit();start.setObjectName('leave_account_start_month');start.setMinimumDate(QDate(1900,1,1));start.setSpecialValueText('Startmonat auswählen');start.setDisplayFormat('MM.yyyy');start.setCalendarPopup(True)
        opening=QLineEdit();opening.setObjectName('leave_account_opening');opening.setPlaceholderText('Urlaubstage, z. B. 4 oder 3,5')
        form.addRow('Person',person);form.addRow('Konto beginnt im Monat',start);form.addRow('Anfangsbestand in Urlaubstagen',opening)
        help=QLabel('Der Anfangsbestand gilt vor der Gutschrift des Startmonats. Pro Monat kommen 2 Tage dazu; bei Ein-/Austritt im Monat anteilig nach beschäftigten Kalendertagen. Verbrauchte Urlaubstage werden einmal abgezogen; ein negativer Rest wird als Hinweis angezeigt.');help.setWordWrap(True);layout.addWidget(help)
        save=QPushButton('Urlaubskonto speichern');save.setObjectName('leave_account_save');layout.addWidget(save)
        settings=leave_account_settings(self.store)
        def load():
            setting=settings.get(person.currentData())
            if setting:
                year,month=map(int,setting.start_month.split('-'));start.setDate(QDate(year,month,1));opening.setText(contract_text(setting.opening_days))
            else:start.setDate(start.minimumDate());opening.clear()
        person.currentIndexChanged.connect(load);load()
        def commit():
            if start.date()==start.minimumDate():raise ValueError('Bitte den ersten Kontenmonat ausdrücklich auswählen.')
            if not opening.text().strip():raise ValueError('Bitte den Anfangsbestand in Urlaubstagen angeben; wenn keiner vorhanden ist, 0 eingeben.')
            value=start.date();save_leave_account(self.store,person.currentData(),f'{value.year():04d}-{value.month():02d}',opening.text(),expected_revision=self.store.input_revision)
            self.proofs=();self.dirty();self.refresh_results();dialog.accept()
        save.clicked.connect(lambda:self.guard(commit));dialog.exec()

    def missing_leave_entries(self):
        from .leave import monthly_leave_rows
        ids={id for r in monthly_leave_rows(self.inputs.people,self.inputs.absences,self.inputs.year,self.inputs.month) for id in r.unknown_entry_ids}
        return tuple(e for e in self.inputs.absences if e.id in ids)

    def repair_leave(self):
        missing=self.missing_leave_entries()
        if not missing:
            self.set_status('Die Urlaubstage dieses Monats sind vollständig ausgewählt.');return
        names={p.id:p.name for p in self.inputs.people}
        labels=[names[e.person_id]+' · '+e.span.start.astimezone(vienna()).strftime('%d.%m.%Y')+' bis '+max(d for d,_ in day_segments(e.span)).strftime('%d.%m.%Y') for e in missing]
        if len(missing)==1:entry=missing[0]
        else:
            label,ok=QInputDialog.getItem(self,'Urlaubstage ergänzen','Welchen Urlaub möchtest du vervollständigen?',labels,0,False)
            if not ok:return
            entry=missing[labels.index(label)]
        self.manual_entry(entry)

    def manual_entry(self,old=None):
        import csv,io,uuid
        from .entries import HEADER
        from .absence_ui import AbsenceDialog
        self.require_accepted_result();self.ensure_team_saved()
        dialog=AbsenceDialog(self,old);staged=False
        def stage():
            nonlocal staged
            pid,kind,start,end,credits,comment=dialog.fields()
            output=io.StringIO();writer=csv.writer(output,delimiter=';');writer.writerow(HEADER)
            writer.writerow(('2',pid,str(uuid.uuid4()),kind,start,end,credits,comment))
            existing=tuple(e for e in self.inputs.absences+self.store.entries() if old is None or e.id!=old.id)
            batch=preview(output.getvalue(),existing=existing,budgets=self.budgets(),month=f'{self.inputs.year:04d}-{self.inputs.month:02d}')
            self.store.save_correction('ui-current',batch,replaces=old.id if old else '')
            self.batch=batch;self.fill_batch();staged=True;dialog.accept()
        dialog.save.clicked.connect(lambda:self.guard(stage));dialog.exec()
        if staged:self.promote()

    def delete_entry(self):
        self.require_accepted_result();self.ensure_team_saved();entry=self.selected_entry()
        if QMessageBox.question(self,'Aktiven Eintrag löschen','Diesen Eintrag löschen? Der Dienstplan bleibt erhalten. Bestätigte historische Snapshots bleiben unverändert.')!=QMessageBox.StandardButton.Yes:return
        updated=self.store.delete_entry(entry.id,self.inputs,self.profile,expected_revision=self.store.input_revision,blocks=self.blocks,events=self.events)
        self.inputs=updated;self.proofs=();self.dirty();self.fill()

    def configure_weekly(self):
        self.require_accepted_result()
        self.ensure_team_saved()
        label,ok=QInputDialog.getItem(self,'Automatische BK/WL-Termine','Welche Wochen sollen berücksichtigt werden?',('Alle Kalenderwochen einschließlich Monatsrändern – mit Nachbarmonaten abstimmen','Nur volle Montag–Sonntag-Wochen im Monat'),0,False)
        if not ok:return
        from .automatic_weekly import automatic_weekly
        from .plan_import import selected_events
        # Bereits zugeteilte Tage beim Einrichten eines Wochenprofils erhalten.
        weekly={e.id for e in self.inputs.events if e.service.code in {'BK','WL'}}
        source=replace(self.inputs,optional_ids=self.inputs.optional_ids-({b.id for b in self.blocks}&weekly))
        updated=automatic_weekly(source,snapshots=self.store.month_snapshots(self.inputs.year,self.inputs.month),full_weeks_only=label.startswith('Nur'))
        assigned={b.id for b in self.blocks}
        # Innerhalb weiter geprüfter Quoten bleiben frühere Datumsoptionen auch
        # für eine spätere automatische Berechnung frei; nur diese Anzeige fixieren.
        restored={e.id for e in updated.events if e.service.code in {'BK','WL'} and e.id in assigned & self.inputs.optional_ids
                  and sum(q.code==e.service.code and q.dates.includes(e.attendance.start_day) for q in updated.quotas)==1}
        updated=replace(updated,optional_ids=updated.optional_ids|restored)
        selection=replace(updated,optional_ids=updated.optional_ids-(assigned&weekly))
        events=selected_events(selection,self.events or ()) if self.events is not None else None
        if events is not None:
            core,calendar=verify_for_planning(updated,self.blocks,active_events=events)
            messages=tuple(i.message for i in core.issues+calendar.issues)
            if messages:
                if not self.confirm_override(messages):return
                updated=replace(updated,manual_override=True,override_notes=messages)
        self.store.save_workspace(updated,self.profile,self.blocks,events,expected_revision=self.store.input_revision)
        self.inputs,self.events=updated,events;self.proofs=();self.dirty();self.fill()

    def import_sheet(self):
        self.ensure_team_saved()
        path,_=QFileDialog.getOpenFileName(self,'Termine, Dienstplan oder Wünsche importieren','','Excel / CSV (*.xlsx *.csv)')
        if not path:return
        mode,ok=QInputDialog.getItem(self,'Dateiinhalt','Bei einer ursprünglichen Monatstabelle:',('Dienstplan (X = kein Dienst)','Wünsche (gelbes X = Freiwunsch)'),0,False)
        if not ok:return
        from .spreadsheets import read_import
        rows,mapping,notes=read_import(path,source_kind='wishes' if mode.startswith('Wünsche') else 'plan')
        self.store.save_sheet_stage(rows,mapping,notes);self.resume_sheet()

    def resume_sheet(self):
        self.ensure_team_saved()
        stage=self.store.sheet_stage()
        if stage is None:raise ValueError('Noch kein Tabellenimport vorgemerkt.')
        from .import_ui import import_dialog
        import_dialog(self,stage['rows'],stage['mapping'],stage['notes'])

    def export_grid(self):
        self.ensure_team_saved()
        blocks,events,_=self.displayed_result()
        if events is None:raise ValueError('Zuerst einen Plan erstellen oder importieren.')
        path,_=QFileDialog.getSaveFileName(self,'Neue Monatsübersicht als Excel','','Excel (*.xlsx)')
        if path:
            from .spreadsheets import export_month_grid
            export_month_grid(path,self.inputs,self.profile,blocks,events)

    def export(self):
        self.ensure_team_saved()
        blocks,events,proofs=self.displayed_result()
        if events is None:raise ValueError('Zuerst einen geprüften Entwurf erstellen oder manuell zuteilen.')
        path,_=QFileDialog.getSaveFileName(self,'Vorschlag als neues Exportpaket exportieren' if self.pending else 'Neues vollständiges Exportpaket','','ZIP (*.zip)')
        if path:export_package(path,self.inputs,self.profile,blocks,events,proofs=proofs)

    def confirm(self):
        self.require_accepted_result()
        self.ensure_team_saved()
        if self.events is None:raise ValueError('Zuerst einen Dienstplan erstellen oder importieren.')
        missing=self.missing_leave_entries()
        if missing:
            from .leave import monthly_leave_rows
            messages=tuple(m for r in monthly_leave_rows(self.inputs.people,self.inputs.absences,self.inputs.year,self.inputs.month) for m in r.diagnostics)
            if QMessageBox.question(self,'Urlaubstage auswählen','Für mindestens einen Urlaub fehlt die Tagesauswahl. Pro Urlaubstag zählen die gültigen Wochenstunden ÷ 5. Jetzt ergänzen?\n\n'+'\n'.join(messages),QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.Yes)==QMessageBox.StandardButton.Yes:self.repair_leave()
            return
        existing=self.store.confirmed_month(self.inputs.year,self.inputs.month)
        if existing is not None:
            self.refresh_results();return
        core,calendar=verify(self.inputs,self.blocks,active_events=self.events)
        messages=tuple(i.message for i in core.issues+calendar.issues)+tuple(f'{id}: {n} offene Plätze' for id,n in core.open_slots)+self.inputs.unchecked+calendar.unchecked+self.inputs.override_notes
        from .presentation import hours_text
        rows=hours_rows(self.inputs.people,self.blocks+self.inputs.boundary,self.inputs.absences,self.inputs.year,self.inputs.month,accounts=self.profile.accounts,target_profile=self.profile.target_profile,month_profile=self.profile.month_profile)
        messages+=tuple(f'{r.person_id}: Abweichung vom Arbeitsziel {hours_text(r.deviation)} h' for r in rows if r.credits_known and r.deviation)
        for _,old in self.store.confirmations():
            for q in self.inputs.quotas:
                chosen=sorted(e.id for e in self.events if e.service.code==q.code and q.dates.includes(e.attendance.start_day))
                if q.id in old.get('quota_reservations',{}) and old['quota_reservations'][q.id]!=chosen:messages+=(f'Bestätigte Randwochenbindung {q.id} widerspricht der neuen Terminwahl.',)
        if messages and not self.confirm_override(tuple(dict.fromkeys(messages)),confirmation=True):return
        id='calculation-confirmation/'+fingerprint((self.inputs,self.profile,self.blocks,self.events))
        self.store.confirm(id,self.inputs,self.blocks,self.events,accounts=self.profile.accounts,wish_policy=self.profile.wish_policy,
                           fairness_policy=self.profile.fairness_policy,target_profile=self.profile.target_profile,month_profile=self.profile.month_profile,expected_revision=self.store.input_revision,synthetic=True,allow_violations=bool(messages))
        self.refresh_results()

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.cancel();self.worker.finished.connect(self.close);event.ignore();return
        self.store.close();super().closeEvent(event)
