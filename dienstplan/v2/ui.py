"""Einzige Desktop-Oberfläche mit dauerhaftem lokalen Monatsarbeitsstand."""
from dataclasses import replace
from datetime import date
from pathlib import Path
from fractions import Fraction
from threading import Event as StopEvent

from PySide6.QtCore import QThread,Signal
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,
    QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QSpinBox,QComboBox,QLineEdit,QInputDialog,
    QListWidget,QListWidgetItem,QDialogButtonBox,QWidget)

from .catalog import CATALOG,event
from .contracts import Contract,Contracts,exact_hours
from .application import standard_month, service_candidates, OPEN_PROFILE, SELECTED_PROFILE
from .presentation import hours_text, hours_minutes, contract_text
from .entries import WishBudget,preview,correct
from .exporting import export_package
from .history import historical_shares
from .objectives import evaluate
from .pauses import PausePolicy,pause_candidates
from .persistence import V2Store
from .reporting import hours_rows,shares
from .serialization import fingerprint
from .solver import solve_feasibility,verify
from .time import Interval,vienna
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
            self.events=self.inputs.events if initial else None
            self.store.save_workspace(self.inputs,self.profile,self.blocks,self.events,expected_revision=self.store.input_revision)
        self.proofs=();self.generation=0;self.worker=None;self.pending=None;self.batch=None;self.loading=False
        layout=QVBoxLayout(self)
        label=QLabel('1. Monat wählen  →  2. Personen erfassen  →  3. Dienste prüfen  →  4. Urlaub und Wünsche  →  5. Dienstplan erstellen');label.setWordWrap(True);layout.addWidget(label)
        from ..build_info import build_label
        self.build_identity=QLabel(build_label());self.build_identity.setWordWrap(True);layout.addWidget(self.build_identity)
        self.location=QLabel(str(database));layout.addWidget(self.location)
        top=QHBoxLayout();layout.addLayout(top)
        for text,handler in (('Neue Datei',self.new_file),('Datei öffnen',self.open_file),('Monat wählen',self.new_month),('Arbeitsstand speichern',self.save),('Exportpaket',self.export),('Monat bestätigen',self.confirm)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));top.addWidget(button)
        self.month_label=QLabel();layout.addWidget(self.month_label)
        self.tabs=QTabWidget();layout.addWidget(self.tabs)
        settings_page=QWidget();settings_box=QVBoxLayout(settings_page)
        settings_box.addWidget(QLabel('Der vollständige Standardkatalog ist bereits eingerichtet. Tägliche Dienste und Donnerstagsvarianten stehen automatisch im Monat.'))
        self.catalog_table=QTableWidget();settings_box.addWidget(self.catalog_table)
        self.month_notes=QLabel();self.month_notes.setWordWrap(True);settings_box.addWidget(self.month_notes)
        settings_box.addWidget(QLabel('Rechenannahmen für Stundenprognose und Optimierung (keine Tarif- oder Rechtsfreigabe):'))
        self.calculation_profile=QComboBox();self.calculation_profile.addItems(['Bitte Rechenprofil ausdrücklich auswählen', 'S0/M0/E0 – technisches Rechenprofil (siehe Hinweise)']);settings_box.addWidget(self.calculation_profile)
        settings_box.addWidget(QLabel('S0: Summe der gültigen Wochenstunden / 7 je Beschäftigungstag. M0: tatsächliche Arbeit im Kalendermonat. E0: benannte Zielreihenfolge. Offene betriebliche Profile bleiben ungeprüft.'))
        self.calculation_profile.currentIndexChanged.connect(self.select_calculation_profile)
        self.tabs.addTab(settings_page,'Dienste und Planungsangaben')
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
        for text,handler in (('Termin ergänzen',self.add_term),('Termin entfernen',self.remove_term)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));row.addWidget(button)
        term_layout.addWidget(QLabel('Pausen: 0,5 h bei Anwesenheit über 6 h; geschützte Teamzeit bleibt frei. Reserve ohne Bewertungsprofil bleibt offen.'))
        self.tabs.addTab(term_page,'Monatstermine')
        import_page=QDialog();import_layout=QVBoxLayout(import_page);bar=QHBoxLayout();import_layout.addLayout(bar)
        bar.addWidget(QLabel('Wunschbudget pro Person (ausdrücklich festlegen): Einzeltage'))
        self.day_budget=QSpinBox();self.day_budget.setRange(0,31);self.day_budget.setValue(2);bar.addWidget(self.day_budget)
        bar.addWidget(QLabel('Wochenenden'));self.weekend_budget=QSpinBox();self.weekend_budget.setRange(0,5);self.weekend_budget.setValue(1);bar.addWidget(self.weekend_budget)
        for text,handler in (('CSV vormerken',self.import_csv),('Gesamten Stapel prüfen und übernehmen',self.promote),('Vormerkung verwerfen',self.discard)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));bar.addWidget(button)
        self.corrections=QTableWidget();import_layout.addWidget(self.corrections)
        self.import_status=QLabel('CSV-Format 2; unzulässige Donnerstagsanteile bleiben bearbeitbar vorgemerkt.');self.import_status.setWordWrap(True);import_layout.addWidget(self.import_status)
        self.active=QTableWidget();import_layout.addWidget(self.active);self.tabs.addTab(import_page,'Urlaub, Wünsche und Korrekturen')
        active_bar=QHBoxLayout();import_layout.addLayout(active_bar)
        for text,handler in (('Eintrag manuell vormerken',self.manual_entry),('Aktiven Eintrag bearbeiten',self.edit_entry),('Aktiven Eintrag löschen',self.delete_entry)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));active_bar.addWidget(button)
        plan_page=QWidget();plan_box=QVBoxLayout(plan_page)
        self.plan_state=QLabel();self.plan_state.setWordWrap(True);plan_box.addWidget(self.plan_state)
        self.discard_preview=QPushButton('Vorschlag verwerfen und bisherigen Plan anzeigen')
        self.discard_preview.clicked.connect(self.discard_result);plan_box.addWidget(self.discard_preview)
        self.plan=QTableWidget();plan_box.addWidget(self.plan);self.tabs.addTab(plan_page,'Dienstplan')
        self.hours=QTableWidget();self.tabs.addTab(self.hours,'Stundenprognose')
        self.distribution=QTableWidget();self.tabs.addTab(self.distribution,'Schichtverteilung')
        self.wishes=QTableWidget();self.tabs.addTab(self.wishes,'Freiwünsche')
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        bottom=QHBoxLayout();layout.addLayout(bottom);self.seconds=QSpinBox();self.seconds.setRange(1,600);self.seconds.setValue(60)
        bottom.addWidget(QLabel('Sekunden'));bottom.addWidget(self.seconds)
        self.calculate=QPushButton('Dienstplan erstellen');self.calculate.clicked.connect(lambda:self.guard(self.start));bottom.addWidget(self.calculate)
        self.stop=QPushButton('Abbrechen');self.stop.clicked.connect(self.cancel);self.stop.setEnabled(False);bottom.addWidget(self.stop)
        self.accept=QPushButton('Ergebnis übernehmen');self.accept.clicked.connect(lambda:self.guard(self.apply_result));self.accept.setEnabled(False);bottom.addWidget(self.accept)
        manual_bar=QHBoxLayout();plan_box.addLayout(manual_bar)
        for text,handler in (('Zuteilung ändern',self.change_assignment),('Zuteilung entfernen',self.remove_assignment),('Fixierung umschalten',self.lock_assignment),('Alle manuellen Fixierungen lösen',self.unlock_all)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));manual_bar.addWidget(button)
        for label in self.findChildren(QLabel):label.setWordWrap(True)
        self.fill();self.tabs.setCurrentWidget(team_page)
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
        self.table(self.team,('ID (fest)','Name','Wochenstunden (ein Vertrag)','Anfang (h)','Wunschende (h)','Beschäftigung [von, bis)','Ausgeschlossene Dienste'),
                   [(p.id,p.name,contract_text(p.contracts.versions[0].weekly_hours) if len(p.contracts.versions)==1 else 'mehrere Vertragsversionen',hours_text(accounts[p.id].opening_minutes),hours_text(accounts[p.id].desired_minutes),
                     f'{p.employment.dates.start} bis {p.employment.dates.end}',
                     '; '.join(f'{r.dates.start} bis {r.dates.end}: '+(', '.join(sorted(r.excluded_codes)) or 'keine')+'; Führerschein '+{True:'ja',False:'nein',None:'unbekannt'}[r.driving_license] for r in p.rights)) for p in self.inputs.people],True)
        from PySide6.QtCore import Qt
        for i in range(self.team.rowCount()):
            for j in (0,5,6):self.team.item(i,j).setFlags(self.team.item(i,j).flags()&~Qt.ItemFlag.ItemIsEditable)
            if len(self.inputs.people[i].contracts.versions)>1:self.team.item(i,2).setFlags(self.team.item(i,2).flags()&~Qt.ItemFlag.ItemIsEditable)
        self.table(self.term_table,('Termin','Beginn Wien','Ende Wien','Plätze','Feste Personen','W16-Grund'),[(e.id,e.attendance.start.astimezone(vienna()).isoformat(),e.attendance.end.astimezone(vienna()).isoformat(),e.service.staff or 'Teilnahme',','.join(e.fixed_people),e.replacement_reason) for e in self.inputs.events])
        self.month_label.setText(f'Monat {self.inputs.month:02d}/{self.inputs.year} · {len(self.inputs.people)} Personen · Änderungen mit „Arbeitsstand speichern“ sichern')
        self.calculation_profile.setCurrentIndex(0 if self.inputs.profile_label==OPEN_PROFILE else 1)
        recurring={'T':'jeden Donnerstag','TS':'ausgewählte Donnerstage','KC10':'täglich außer Donnerstag','KC16':'täglich außer Donnerstag','W17':'täglich außer Donnerstag','KCT10':'jeden Donnerstag','KCT':'jeden Donnerstag','TW':'jeden Donnerstag','W16':'begründeter Ersatz für W17','WL':'automatisch nach bestätigtem Wochenprofil','BK':'automatisch nach bestätigtem Wochenprofil','LB':'14-tägig ab Referenzdatum; feste Personen','VN':'feste Tage und Personen','INT':'2 feste Termine im Monat','N17':'1 fester Termin und Person; Führerschein','R':'24.12.–06.01.; Bewertung fehlt','FK':'individuelle Zeit und feste Person'}
        def times(t):
            if t.start is None:return 'individuell'
            return f'{t.start:%H:%M}–{t.end:%H:%M}'+(' (Folgetag)' if t.end<=t.start else '')
        self.table(self.catalog_table,('Dienst','Uhrzeit Wien','Personen','Auftreten / notwendige Angaben'),[(t.key,times(t),t.staff or 'Teilnahme',recurring[t.code]) for t in CATALOG])
        self.month_notes.setText('Noch benötigte Angaben: '+' | '.join(self.inputs.unchecked))
        self.day.setText(f'{self.inputs.year:04d}-{self.inputs.month:02d}-10')
        self.table(self.active,('ID','Person','Typ','Beginn','Ende','Gutschrifttage'),[(e.id,e.person_id,e.kind,e.span.start.astimezone(vienna()).isoformat(),e.span.end.astimezone(vienna()).isoformat(),','.join(map(str,sorted(e.credit_days)))) for e in self.inputs.absences])
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
        label=self.inputs.profile_label
        if label in (OPEN_PROFILE,SELECTED_PROFILE):label=SELECTED_PROFILE if self.calculation_profile.currentIndex() else OPEN_PROFILE
        return replace(self.inputs,people=tuple(people),profile_label=label),replace(self.profile,accounts=tuple(accounts))

    def ensure_team_saved(self):
        if self.read_team()!=(self.inputs,self.profile):raise ValueError('Team- und Kontoeingaben zuerst mit „Arbeitsstand speichern“ übernehmen.')

    def clear_plan(self,confirm_only=False):
        if self.blocks and QMessageBox.question(self,'Entwurf nach Eingabeänderung','Diese Eingabe verwirft den angezeigten Entwurf. Gespeicherte Revisionen bleiben erhalten. Fortfahren?')!=QMessageBox.StandardButton.Yes:return False
        if confirm_only:return True
        self.blocks=();self.events=None;self.proofs=();self.dirty();return True

    def add_term(self):
        self.ensure_team_saved()
        day=date.fromisoformat(self.day.text());key=self.code.currentText()
        if (day.year,day.month)!=(self.inputs.year,self.inputs.month):raise ValueError('Termin muss im geöffneten Monat beginnen.')
        reason=''
        if key=='W16':
            reason,ok=QInputDialog.getText(self,'W16','Dokumentierter Ersatzgrund:')
            if not ok:return
        span=Interval.local(self.fk_start.text(),self.fk_end.text()) if key=='FK' else None
        term=event(key,day,people=tuple(v.strip() for v in self.fixed.text().split(',') if v.strip()),attendance=span,reason=reason)
        if any(e.id==term.id for e in self.inputs.events):raise ValueError('Dieser Termin existiert bereits.')
        replaced={'TS':{'T'},'T':{'TS'},'W16':{'W17'},'W17':{'W16'}}.get(key,set())
        removed={e.id for e in self.inputs.events if e.attendance.start_day==day and e.service.key in replaced}
        additions=[term]
        if key in {'T','TS'}:
            for old in self.inputs.events:
                if old.attendance.start_day==day and old.service.code=='LB':
                    removed.add(old.id)
                    additions.append(event('LB_TS' if key=='TS' else 'LB',day,people=old.fixed_people))
        candidates=service_candidates(additions,self.inputs.people)
        if not self.clear_plan():return
        self.inputs=replace(self.inputs,events=tuple(e for e in self.inputs.events if e.id not in removed)+tuple(additions),
                            candidates=tuple(b for b in self.inputs.candidates if b.id not in removed)+candidates,
                            locked=tuple(b for b in self.inputs.locked if b.id not in removed),optional_ids=self.inputs.optional_ids-removed)
        self.fill()

    def remove_term(self):
        self.ensure_team_saved()
        row=self.term_table.currentRow()
        if row<0:return
        id=self.term_table.item(row,0).text()
        if not self.clear_plan():return
        self.inputs=replace(self.inputs,events=tuple(e for e in self.inputs.events if e.id!=id),candidates=tuple(b for b in self.inputs.candidates if b.id!=id),
                            locked=tuple(b for b in self.inputs.locked if b.id!=id),optional_ids=self.inputs.optional_ids-{id});self.fill()

    def refresh_results(self):
        blocks,active_events,proofs=self.displayed_result()
        events=self.inputs.events if active_events is None else active_events
        preview=self.pending is not None
        self.plan_state.setText('BERECHNETER VORSCHLAG – noch nicht gespeichert. Zum Behalten „Ergebnis übernehmen“ wählen. Der bisherige Plan bleibt bis dahin erhalten.' if preview else
                               'Gespeicherter Plan / Entwurf.' if active_events is not None else 'Noch kein berechneter Plan. Angezeigt werden die vorgesehenen Plätze.')
        self.discard_preview.setVisible(preview)
        names={p.id:f'{p.name} ({p.id})' for p in self.inputs.people}
        self.plan_rows=[];rows=[]
        for e in events:
            selected=[b for b in blocks if b.id==e.id]
            for i in range(max(e.service.staff or 0,len(selected))):
                b=selected[i] if i<len(selected) else None;self.plan_rows.append((e,b))
                rows.append((e.id,e.service.code,i+1,names.get(b.person_id,b.person_id) if b else 'OFFEN',hours_text(b.work_minutes) if b else '',
                             'fixiert' if b in self.inputs.locked else '',
                             '; '.join(p.start.astimezone(vienna()).strftime('%d.%m. %H:%M')+'–'+p.end.astimezone(vienna()).strftime('%d.%m. %H:%M') for p in b.breaks) if b else ''))
        self.table(self.plan,('Termin','Dienst','Platz','Person','Arbeitsstunden (h)','Fixierung','Konkrete Pause'),rows)
        hours=hours_rows(self.inputs.people,blocks+self.inputs.boundary,self.inputs.absences,self.inputs.year,self.inputs.month,accounts=self.profile.accounts,target_profile='S0',month_profile='M0')
        profile_selected=self.calculation_profile.currentIndex()==1
        self.table(self.hours,('Person','Monatssoll (h)','Anfang (h)','Wunschende (h)','Urlaub (h)','Arbeitsziel (h)','Geplant (h)','Prognose Ende (h)','Abweichung (h)'),[(r.person_id,hours_text(r.target) if profile_selected else 'Profil wählen',hours_text(r.opening),hours_text(r.desired),hours_text(r.credits) if r.credits_known and profile_selected else 'ungeklärt',hours_text(r.goal) if r.credits_known and profile_selected else 'ungeklärt',hours_text(r.work),hours_text(r.projected) if r.credits_known and profile_selected else 'ungeklärt',hours_text(r.deviation) if r.credits_known and profile_selected else 'ungeklärt') for r in hours])
        distribution=shares(self.inputs.people,events,blocks,policy=self.profile.fairness_policy,absences=self.inputs.absences)
        self.table(self.distribution,('Person','Dienst','Anzahl','Stunden (h)','Fairer Anteil Anzahl','Fairer Anteil (h)'),[(r.person_id,r.code,r.count,hours_text(r.work_minutes),contract_text(r.expected_count),hours_text(r.expected_minutes)) for r in distribution])
        wishes=wish_rows(self.inputs.people,self.inputs.absences,events,blocks+self.inputs.boundary,policy=self.profile.wish_policy,history=self.profile.history)
        self.table(self.wishes,('Person','Relevant','Erfüllt','Übergangen','Historisch','Kumuliert'),[(r.person_id,len(r.relevant),r.fulfilled_count,len(r.violated),len(r.historical),len(r.cumulative)) for r in wishes])
        if active_events is not None:
            core,calendar=verify(self.inputs,blocks,active_events=active_events)
            status=('VORSCHAU – noch nicht übernommen. ' if preview else '')+f'{len(blocks)} Zuteilungen; {sum(n for _,n in core.open_slots)} offene Plätze; {sum(p.proven and not p.conditional for p in proofs)} unbedingt bewiesene Zielstufen. '
            status+=' | '.join(i.message for i in core.issues+calendar.issues)
            status+=' | '+' | '.join(dict.fromkeys(self.inputs.unchecked+calendar.unchecked+self.profile.history.missing))
        else:status='Noch kein berechneter Entwurf. Offene Planungsangaben siehe „Dienste und Planungsangaben“.'
        required=sum((e.service.staff or 0)*(e.attendance.minutes-(30 if e.attendance.minutes>360 else 0)) for e in events if e.service.code!='R')
        target=sum(max(0,r.goal) for r in hours) if all(r.credits_known for r in hours) else None
        status+=f' | Operativer Bedarf ohne ungeklärte R-Bewertung: {hours_text(required)} h; nicht negatives Arbeitsziel gesamt: '+(f'{hours_text(target)} h.' if target is not None else 'ungeklärt.')
        self.status.setText(status)

    def save(self):
        inputs,profile=self.read_team()
        changed=(inputs,profile)!=(self.inputs,self.profile)
        if changed and not self.clear_plan(confirm_only=True):return False
        blocks=() if changed else self.blocks;events=None if changed else self.events
        self.store.save_workspace(inputs,profile,blocks,events,expected_revision=self.store.input_revision)
        self.inputs,self.profile,self.blocks,self.events=inputs,profile,blocks,events
        if changed:self.proofs=()
        self.fill();return True

    def new_file(self):
        if self.worker and self.worker.isRunning():raise ValueError('Berechnung zuerst abbrechen.')
        path,_=QFileDialog.getSaveFileName(self,'Neue Dienstplandatei','','SQLite (*.sqlite3)')
        if not path:return
        inputs,profile=self.read_team();new=V2Store(path,create=True)
        try:new.save_workspace(inputs,profile,self.blocks,self.events,expected_revision=0)
        except Exception:new.close();raise
        self.store.close();self.store=new;self.inputs,self.profile=inputs,profile;self.proofs=();self.location.setText(path);self.dirty();self.fill()

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
        from .contracts import DateRange,Employment
        from .people import Eligibility,Person
        from .accounting import MonthAccount
        dialog=QDialog(self);dialog.setWindowTitle('Zeitgültige Personendaten – Ende jeweils ausgeschlossen');box=QVBoxLayout(dialog)
        name=QLineEdit(person.name if person else '');start=QLineEdit(str(person.employment.dates.start) if person else '')
        end=QLineEdit(str(person.employment.dates.end) if person else '')
        for label,widget in (('Name',name),('Beschäftigung erster Tag YYYY-MM-DD',start),('Beschäftigung Ende ausgeschlossen YYYY-MM-DD',end)):
            box.addWidget(QLabel(label));box.addWidget(widget)
        contracts=QTableWidget();rights=QTableWidget()
        self.table(contracts,('Von eingeschlossen','Bis ausgeschlossen','Wochenstunden'),[(str(c.dates.start),str(c.dates.end),contract_text(c.weekly_hours)) for c in person.contracts.versions] if person else [('', '', '')],True)
        self.table(rights,('Von eingeschlossen','Bis ausgeschlossen','Ausgeschlossene Dienste (Leerzeichen)','Führerschein ja/nein/unbekannt'),[(str(r.dates.start),str(r.dates.end),' '.join(sorted(r.excluded_codes)),{True:'ja',False:'nein',None:'unbekannt'}[r.driving_license]) for r in person.rights] if person else [('', '', '', 'unbekannt')],True)
        for label,table in (('Vertragsversionen',contracts),('Zeitgültige Dienstausschlüsse – leer bedeutet keine Ausschlüsse',rights)):
            box.addWidget(QLabel(label));box.addWidget(table);bar=QHBoxLayout();box.addLayout(bar)
            add=QPushButton('Version ergänzen');remove=QPushButton('Gewählte Version entfernen');bar.addWidget(add);bar.addWidget(remove)
            def append(t=table):
                row=t.rowCount();t.insertRow(row)
                for col in range(t.columnCount()):t.setItem(row,col,QTableWidgetItem(''))
            add.clicked.connect(lambda checked=False,f=append:f())
            remove.clicked.connect(lambda checked=False,t=table:t.removeRow(t.currentRow()) if t.currentRow()>=0 else None)
        choose=QPushButton('Ausgeschlossene Dienste auswählen');box.addWidget(choose)
        def choose_exclusions():
            row=rights.currentRow()
            if row<0:row=0
            if rights.rowCount()==0:raise ValueError('Zuerst eine Ausschlussversion ergänzen.')
            selected=self.choose_exclusions(rights.item(row,2).text().split())
            if selected is not None:rights.item(row,2).setText(' '.join(sorted(selected)))
        choose.clicked.connect(lambda:self.guard(choose_exclusions))
        commit=QPushButton('Personendaten prüfen und übernehmen');box.addWidget(commit)
        def apply():
            pid=person.id if person else new_id
            def values(table,row):return [table.item(row,col).text().strip() for col in range(table.columnCount())]
            versions=[];permissions=[]
            for i in range(contracts.rowCount()):
                a,z,w=values(contracts,i);versions.append(Contract(pid,DateRange(date.fromisoformat(a),date.fromisoformat(z)),exact_hours(Fraction(w.replace(',','.')))))
            for i in range(rights.rowCount()):
                a,z,codes,driver=values(rights,i)
                if driver not in {'ja','nein','unbekannt'}:raise ValueError('Führerschein ausdrücklich ja, nein oder unbekannt.')
                if not set(codes.split())<={t.code for t in CATALOG}:raise ValueError('Unbekanntes Dienstkürzel bei ausgeschlossenen Diensten.')
                permissions.append(Eligibility.from_exclusions(DateRange(date.fromisoformat(a),date.fromisoformat(z)),frozenset(codes.split()),{'ja':True,'nein':False,'unbekannt':None}[driver]))
            updated=Person(pid,name.text(),Employment(pid,DateRange(date.fromisoformat(start.text()),date.fromisoformat(end.text()))),Contracts(pid,tuple(versions)),tuple(permissions))
            # Benötigte Soll-Verträge vollständig prüfen, bevor der alte Entwurf entfällt.
            from .accounting import s0_target
            s0_target(updated.contracts,updated.employment,self.inputs.year,self.inputs.month,profile='S0')
            if not self.clear_plan(confirm_only=True):return
            people=tuple(updated if p.id==pid else p for p in self.inputs.people) if person else self.inputs.people+(updated,)
            candidates=tuple(c for c in self.inputs.candidates if c.person_id!=pid)
            for term in self.inputs.events:
                if updated.eligibility_errors(term.service.code,term.attendance) or term.service.code=='R' or (term.fixed_people and pid not in term.fixed_people):continue
                candidates+=pause_candidates(term,pid,policy=PausePolicy('Pausenraster 0,5 h; Abdeckung ungeklärt',(term.attendance,),30))
            from .calendar_rules import dates
            current=DateRange(date(self.inputs.year,self.inputs.month,1),date(self.inputs.year+int(self.inputs.month==12),self.inputs.month%12+1,1))
            known=self.inputs.known_days|frozenset((pid,d) for d in dates(current))
            inputs=replace(self.inputs,people=people,candidates=candidates,known_days=known)
            profile=self.profile if person else replace(self.profile,accounts=self.profile.accounts+(MonthAccount(pid,0),))
            self.store.save_workspace(inputs,profile,expected_revision=self.store.input_revision)
            self.inputs,self.profile,self.blocks,self.events=inputs,profile,(),None;self.proofs=();self.dirty();self.fill();dialog.accept()
        commit.clicked.connect(lambda:self.guard(apply));dialog.resize(950,700);dialog.exec()

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
        if self.calculation_profile.currentIndex()==0:raise ValueError('Unter „Dienste und Planungsangaben“ ein Rechenprofil ausdrücklich auswählen. Offene Fachprofile werden dadurch nicht freigegeben.')
        if self.save() is False:return
        self.discard_result()
        token=(self.generation,self.store.input_revision,self.inputs.fingerprint,fingerprint(self.profile))
        events=self.events if self.events is not None else (self.inputs.events if not self.inputs.optional_ids else None)
        self.worker=Worker(self.inputs,self.profile,self.blocks,events,self.seconds.value(),token,self)
        self.worker.completed.connect(self.on_worker_completed);self.worker.failed.connect(lambda error:self.status.setText('Berechnung fehlgeschlagen: '+error))
        self.worker.finished.connect(lambda:(self.calculate.setEnabled(True),self.stop.setEnabled(False)))
        self.calculate.setEnabled(False);self.stop.setEnabled(True);self.status.setText('Berechnung läuft; Eingabeänderungen machen das Ergebnis veraltet.');self.worker.start()

    def on_worker_completed(self,result,token):
        current=(self.generation,self.store.input_revision,self.inputs.fingerprint,fingerprint(self.profile))
        if current!=token:self.status.setText('Eingaben geändert: Ergebnis veraltet und nicht übernommen.');return
        if result.status in {'unknown','cancelled','infeasible','invalid'}:
            self.status.setText('Noch kein gültiges Ergebnis / Vorgabenkonflikt: '+result.status+'; '+'; '.join(i.message for i in result.issues));return
        core,calendar=verify(self.inputs,result.blocks,active_events=result.events)
        if not core.hard_ok or not calendar.hard_ok:
            self.status.setText('Berechneter Vorschlag verletzt verbindliche Regeln und wird nicht angezeigt.');return
        self.pending=(result,token);self.accept.setEnabled(True)
        self.refresh_results();self.tabs.setCurrentWidget(self.plan.parentWidget())
        self.status.setText(self.status.text()+' '+('Alle gewählten Zielstufen bewiesen.' if result.global_optimal else 'Kein vollständiger Optimalitätsnachweis.')+
                            (' Noch keine Person zugeteilt; Zeitlimit und Eingaben prüfen.' if not result.blocks else ''))

    def apply_result(self):
        if not self.pending:return
        result,token=self.pending
        if token!=(self.generation,self.store.input_revision,self.inputs.fingerprint,fingerprint(self.profile)):raise ValueError('Ergebnis ist veraltet.')
        core,calendar=verify(self.inputs,result.blocks,active_events=result.events)
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

    def manual(self,blocks,locked=None):
        self.require_accepted_result()
        self.ensure_team_saved()
        inputs=self.inputs if locked is None else replace(self.inputs,locked=tuple(locked))
        events=self.events or self.inputs.events
        core,calendar=verify(inputs,blocks,active_events=events)
        if not core.hard_ok or not calendar.hard_ok:raise ValueError('; '.join(i.message for i in core.issues+calendar.issues))
        self.store.save_workspace(inputs,self.profile,blocks,events,expected_revision=self.store.input_revision)
        self.inputs,self.blocks,self.events=inputs,tuple(blocks),events;self.proofs=();self.dirty();self.refresh_results()

    def change_assignment(self):
        term,old=self.selected();choices=[b for b in self.inputs.candidates if b.id==term.id]
        labels=[f'{b.person_id}: Pause '+('; '.join(p.start.astimezone(vienna()).strftime('%H:%M')+'–'+p.end.astimezone(vienna()).strftime('%H:%M') for p in b.breaks) or 'keine') for b in choices]
        if not labels:raise ValueError('Keine konkreten Kandidaten vorhanden; Rechte/Pausenprofile prüfen.')
        label,ok=QInputDialog.getItem(self,'Zuteilung','Person und konkrete Pause:',labels,0,False)
        if ok:self.manual(tuple(b for b in self.blocks if b!=old)+(choices[labels.index(label)],))

    def remove_assignment(self):
        _,old=self.selected()
        if old:self.manual(tuple(b for b in self.blocks if b!=old))

    def lock_assignment(self):
        _,old=self.selected()
        if old:self.manual(self.blocks,tuple(b for b in self.inputs.locked if b!=old) if old in self.inputs.locked else self.inputs.locked+(old,))

    def unlock_all(self):
        self.require_accepted_result()
        self.ensure_team_saved()
        inputs=replace(self.inputs,locked=())
        self.store.save_workspace(inputs,self.profile,self.blocks,self.events,expected_revision=self.store.input_revision)
        self.inputs=inputs;self.proofs=();self.dirty();self.refresh_results()

    def budgets(self):return {(p.id,f'{self.inputs.year:04d}-{self.inputs.month:02d}'):WishBudget(self.day_budget.value(),self.weekend_budget.value()) for p in self.inputs.people}

    def fill_batch(self):
        if not self.batch:self.corrections.setRowCount(0);return
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
        self.ensure_team_saved()
        for i,row in enumerate(self.batch.rows):
            changes={key:self.corrections.item(i,j+1).text() for j,key in enumerate(self.correction_fields)}
            self.batch=correct(self.batch,row.line,changes,existing=self.store.correction_existing('ui-current',self.inputs.absences),budgets=self.budgets(),month=f'{self.inputs.year:04d}-{self.inputs.month:02d}')
        self.store.save_correction('ui-current',self.batch);self.fill_batch()
        if not self.batch.ready:raise ValueError('Stapel bleibt zur Korrektur vorgemerkt; Fehler bitte vollständig beheben.')
        if not self.clear_plan(confirm_only=True):return
        self.inputs=self.store.apply_correction('ui-current',self.inputs,self.profile,budgets=self.budgets(),expected_revision=self.store.input_revision)
        self.blocks=();self.events=None;self.proofs=();self.dirty()
        self.batch=None;self.fill_batch();self.fill()

    def discard(self):
        self.store.discard_correction('ui-current');self.batch=None;self.fill_batch();self.import_status.setText('Vormerkung verworfen. Aktive Eingaben unverändert.')

    def selected_entry(self):
        row=self.active.currentRow()
        if row<0:raise ValueError('Zuerst einen aktiven Eintrag wählen.')
        id=self.active.item(row,0).text()
        return next(e for e in self.inputs.absences if e.id==id)

    def edit_entry(self):self.manual_entry(self.selected_entry())

    def manual_entry(self,old=None):
        import csv,io,uuid
        from .entries import HEADER
        self.ensure_team_saved()
        dialog=QDialog(self);dialog.setWindowTitle('Urlaub/Freiwunsch zur vollständigen Prüfung vormerken');box=QVBoxLayout(dialog)
        person=QComboBox()
        for p in self.inputs.people:person.addItem(f'{p.name} ({p.id})',p.id)
        if old:person.setCurrentIndex(person.findData(old.person_id));person.setEnabled(False)
        kind=QComboBox();kind.addItems(['urlaub','freiwunschtag','wochenendwunsch']);kind.setCurrentText(old.kind if old else 'freiwunschtag')
        start=QLineEdit(old.span.start.astimezone(vienna()).isoformat() if old else '')
        end=QLineEdit(old.span.end.astimezone(vienna()).isoformat() if old else '')
        credits=QLineEdit('|'.join(map(str,sorted(old.credit_days))) if old else '')
        comment=QLineEdit(old.comment if old else '')
        for label,widget in (('Person',person),('Art',kind),('Beginn ISO, z. B. 2026-11-11T00:00',start),('Ende ausgeschlossen, Datum und Uhrzeit',end),('Nur Urlaub: ausdrücklich anrechenbare Daten YYYY-MM-DD mit | trennen',credits),('Kommentar',comment)):
            box.addWidget(QLabel(label));box.addWidget(widget)
        save=QPushButton('Zur Korrektur/Übernahme vormerken');box.addWidget(save)
        def stage():
            output=io.StringIO();writer=csv.writer(output,delimiter=';');writer.writerow(HEADER)
            writer.writerow(('2',person.currentData(),str(uuid.uuid4()),kind.currentText(),start.text(),end.text(),credits.text(),comment.text()))
            existing=tuple(e for e in self.inputs.absences+self.store.entries() if old is None or e.id!=old.id)
            batch=preview(output.getvalue(),existing=existing,budgets=self.budgets(),month=f'{self.inputs.year:04d}-{self.inputs.month:02d}')
            self.store.save_correction('ui-current',batch,replaces=old.id if old else '')
            self.batch=batch;self.fill_batch();dialog.accept()
        save.clicked.connect(lambda:self.guard(stage));dialog.resize(720,450);dialog.exec()

    def delete_entry(self):
        self.ensure_team_saved();entry=self.selected_entry()
        if QMessageBox.question(self,'Aktiven Eintrag löschen','Diesen aktiven Eintrag löschen? Bestätigte historische Snapshots bleiben erhalten. Der aktuelle Entwurf wird verworfen.')!=QMessageBox.StandardButton.Yes:return
        updated=self.store.delete_entry(entry.id,self.inputs,self.profile,expected_revision=self.store.input_revision)
        self.inputs=updated;self.blocks=();self.events=None;self.proofs=();self.dirty();self.fill()

    def export(self):
        self.ensure_team_saved()
        blocks,events,proofs=self.displayed_result()
        if events is None:raise ValueError('Zuerst einen geprüften Entwurf erstellen oder manuell zuteilen.')
        path,_=QFileDialog.getSaveFileName(self,'Vorschlag als neues Exportpaket exportieren' if self.pending else 'Neues vollständiges Exportpaket','','ZIP (*.zip)')
        if path:export_package(path,self.inputs,self.profile,blocks,events,proofs=proofs)

    def confirm(self):
        self.require_accepted_result()
        self.ensure_team_saved()
        if self.events is None:raise ValueError('Zuerst einen geprüften Entwurf erstellen.')
        id='calculation-confirmation/'+fingerprint((self.inputs,self.profile,self.blocks,self.events))
        self.store.confirm(id,self.inputs,self.blocks,self.events,accounts=self.profile.accounts,wish_policy=self.profile.wish_policy,
                           fairness_policy=self.profile.fairness_policy,target_profile='S0',month_profile='M0',expected_revision=self.store.input_revision,synthetic=True)
        self.status.setText('Rechenstand unveränderlich bestätigt. Grundlage S0/M0/E0; offene Rechts- und Tarifprofile bleiben ungeprüft.')

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.cancel();self.worker.finished.connect(self.close);event.ignore();return
        self.store.close();super().closeEvent(event)
