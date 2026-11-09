"""Expliziter V2-Prüfbereich in der Altanwendung, keine produktive Umschaltung."""
from dataclasses import replace
from datetime import date
from pathlib import Path
from fractions import Fraction
from tempfile import TemporaryDirectory
from threading import Event as StopEvent

from PySide6.QtCore import QThread,Signal
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,
    QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QSpinBox,QComboBox,QLineEdit,QInputDialog)

from .catalog import CATALOG,event
from .contracts import Contract,Contracts,exact_hours
from .demo import technical_demo
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
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('V2-Prüfbereich – ausschließlich Testprofile');self.resize(1260,820)
        self.temporary=TemporaryDirectory(prefix='dienstplan-v2-pruefung-')
        self.store=V2Store(Path(self.temporary.name)/'test.sqlite3',create=True)
        self.inputs,self.profile,self.blocks=technical_demo();self.events=self.inputs.events
        self.proofs=();self.generation=0;self.worker=None;self.pending=None;self.batch=None;self.loading=False
        layout=QVBoxLayout(self)
        label=QLabel('V2-Testbereich: kein vollständiger Betriebsmonat, keine KV-/Tariffreigabe. Die normale Anwendung und ihre Datei bleiben getrennt.');label.setWordWrap(True);layout.addWidget(label)
        self.location=QLabel('Temporärer Teststand – für dauerhafte Aufbewahrung „Neue Testdatei“ wählen.');layout.addWidget(self.location)
        top=QHBoxLayout();layout.addLayout(top)
        for text,handler in (('Neue Testdatei',self.new_file),('Testdatei öffnen',self.open_file),('Testmonat wählen',self.new_month),('Arbeitsstand speichern',self.save),('Exportpaket',self.export),('Testmonat bestätigen',self.confirm)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));top.addWidget(button)
        self.tabs=QTabWidget();layout.addWidget(self.tabs)
        self.team=QTableWidget();self.tabs.addTab(self.team,'Team und Stundenkonten')
        self.team.cellChanged.connect(self.dirty)
        person_bar=QHBoxLayout();layout.addLayout(person_bar)
        for text,handler in (('Person ergänzen',self.add_person),('Beschäftigung, Verträge und Rechte bearbeiten',self.person_details)):
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
        term_layout.addWidget(QLabel('Pausen beim Ergänzen: explizites Testprofil, 30-Minuten-Startabstand im Dienst; geschützte Teamzeit bleibt frei von Pausen. R-Bewertung fehlt und erhält keine Arbeitskandidaten.'))
        self.tabs.addTab(term_page,'Termine und Rechte')
        import_page=QDialog();import_layout=QVBoxLayout(import_page);bar=QHBoxLayout();import_layout.addLayout(bar)
        bar.addWidget(QLabel('Explizites Testbudget pro Person: Einzeltage'))
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
        self.plan=QTableWidget();self.tabs.addTab(self.plan,'Dienstplan')
        self.hours=QTableWidget();self.tabs.addTab(self.hours,'Stundenprognose')
        self.distribution=QTableWidget();self.tabs.addTab(self.distribution,'Schichtverteilung')
        self.wishes=QTableWidget();self.tabs.addTab(self.wishes,'Freiwünsche')
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        bottom=QHBoxLayout();layout.addLayout(bottom);self.seconds=QSpinBox();self.seconds.setRange(1,600);self.seconds.setValue(20)
        bottom.addWidget(QLabel('Sekunden'));bottom.addWidget(self.seconds)
        self.calculate=QPushButton('Testplan berechnen');self.calculate.clicked.connect(lambda:self.guard(self.start));bottom.addWidget(self.calculate)
        self.stop=QPushButton('Abbrechen');self.stop.clicked.connect(self.cancel);self.stop.setEnabled(False);bottom.addWidget(self.stop)
        self.accept=QPushButton('Ergebnis übernehmen');self.accept.clicked.connect(lambda:self.guard(self.apply_result));self.accept.setEnabled(False);bottom.addWidget(self.accept)
        for text,handler in (('Zuteilung ändern',self.change_assignment),('Zuteilung entfernen',self.remove_assignment),('Fixierung umschalten',self.lock_assignment),('Alle manuellen Fixierungen lösen',self.unlock_all)):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,f=handler:self.guard(f));bottom.addWidget(button)
        self.fill()

    def guard(self,action):
        try:return action()
        except Exception as exc:QMessageBox.warning(self,'V2-Eingabe prüfen',str(exc))

    def dirty(self,*_):
        if not self.loading:self.generation+=1;self.pending=None;self.accept.setEnabled(False)

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
        self.table(self.team,('ID (fest)','Name','Wochenstunden (ein Vertrag)','Anfang min','Wunschende min','Beschäftigung [von, bis)','Rechte (Details)'),
                   [(p.id,p.name,str(p.contracts.versions[0].weekly_hours) if len(p.contracts.versions)==1 else 'mehrere Vertragsversionen',accounts[p.id].opening_minutes,accounts[p.id].desired_minutes,
                     f'{p.employment.dates.start} bis {p.employment.dates.end}',
                     '; '.join(f'{r.dates.start} bis {r.dates.end}: '+', '.join(sorted(r.codes))+'; Führerschein '+{True:'ja',False:'nein',None:'unbekannt'}[r.driving_license] for r in p.rights)) for p in self.inputs.people],True)
        from PySide6.QtCore import Qt
        for i in range(self.team.rowCount()):
            for j in (0,5,6):self.team.item(i,j).setFlags(self.team.item(i,j).flags()&~Qt.ItemFlag.ItemIsEditable)
            if len(self.inputs.people[i].contracts.versions)>1:self.team.item(i,2).setFlags(self.team.item(i,2).flags()&~Qt.ItemFlag.ItemIsEditable)
        self.table(self.term_table,('Termin','Beginn Wien','Ende Wien','Plätze','Feste Personen','W16-Grund'),[(e.id,e.attendance.start.astimezone(vienna()).isoformat(),e.attendance.end.astimezone(vienna()).isoformat(),e.service.staff or 'Teilnahme',','.join(e.fixed_people),e.replacement_reason) for e in self.inputs.events])
        self.day.setText(f'{self.inputs.year:04d}-{self.inputs.month:02d}-10')
        self.table(self.active,('ID','Person','Typ','Beginn','Ende','Gutschrifttage'),[(e.id,e.person_id,e.kind,e.span.start.astimezone(vienna()).isoformat(),e.span.end.astimezone(vienna()).isoformat(),','.join(map(str,sorted(e.credit_days)))) for e in self.inputs.absences])
        self.loading=False;self.refresh_results()

    def read_team(self):
        from .accounting import MonthAccount
        people=[];accounts=[]
        for i,p in enumerate(self.inputs.people):
            name=self.team.item(i,1).text();contracts=p.contracts
            if len(contracts.versions)==1:
                text=self.team.item(i,2).text().replace(',','.')
                value=exact_hours(Fraction(text)) if '/' in text else exact_hours(text)
                v=contracts.versions[0];contracts=Contracts(p.id,(replace(v,weekly_hours=value),))
            people.append(replace(p,name=name,contracts=contracts))
            accounts.append(MonthAccount(p.id,int(self.team.item(i,3).text()),int(self.team.item(i,4).text())))
        return replace(self.inputs,people=tuple(people)),replace(self.profile,accounts=tuple(accounts))

    def ensure_team_saved(self):
        if self.read_team()!=(self.inputs,self.profile):raise ValueError('Team- und Kontoeingaben zuerst mit „Arbeitsstand speichern“ übernehmen.')

    def clear_plan(self,confirm_only=False):
        if self.blocks and QMessageBox.question(self,'Entwurf nach Eingabeänderung','Diese Eingabe verwirft den angezeigten Entwurf. Gespeicherte Revisionen bleiben erhalten. Fortfahren?')!=QMessageBox.StandardButton.Yes:return False
        if confirm_only:return True
        self.blocks=();self.events=None;self.proofs=();self.dirty();return True

    def add_term(self):
        self.ensure_team_saved()
        day=date.fromisoformat(self.day.text());key=self.code.currentText()
        if (day.year,day.month)!=(self.inputs.year,self.inputs.month):raise ValueError('Termin muss im geöffneten Testmonat beginnen.')
        reason=''
        if key=='W16':reason,ok=QInputDialog.getText(self,'W16','Dokumentierter Ersatzgrund:');
        span=Interval.local(self.fk_start.text(),self.fk_end.text()) if key=='FK' else None
        term=event(key,day,people=tuple(v.strip() for v in self.fixed.text().split(',') if v.strip()),attendance=span,reason=reason)
        if any(e.id==term.id for e in self.inputs.events):raise ValueError('Dieser Termin existiert bereits.')
        candidates=[]
        for p in self.inputs.people:
            if p.eligibility_errors(term.service.code,term.attendance) or (term.fixed_people and p.id not in term.fixed_people) or key.startswith('R_'):continue
            candidates.extend(pause_candidates(term,p.id,policy=PausePolicy('Explizites UI-Testfenster',(term.attendance,),30)))
        if not self.clear_plan():return
        self.inputs=replace(self.inputs,events=self.inputs.events+(term,),candidates=self.inputs.candidates+tuple(candidates));self.fill()

    def remove_term(self):
        self.ensure_team_saved()
        row=self.term_table.currentRow()
        if row<0:return
        id=self.term_table.item(row,0).text()
        if not self.clear_plan():return
        self.inputs=replace(self.inputs,events=tuple(e for e in self.inputs.events if e.id!=id),candidates=tuple(b for b in self.inputs.candidates if b.id!=id),
                            locked=tuple(b for b in self.inputs.locked if b.id!=id),optional_ids=self.inputs.optional_ids-{id});self.fill()

    def refresh_results(self):
        events=self.events or self.inputs.events
        self.plan_rows=[];rows=[]
        for e in events:
            selected=[b for b in self.blocks if b.id==e.id]
            for i in range(max(e.service.staff or 0,len(selected))):
                b=selected[i] if i<len(selected) else None;self.plan_rows.append((e,b))
                rows.append((e.id,e.service.code,i+1,b.person_id if b else 'OFFEN',b.work_minutes if b else '',
                             'fixiert' if b in self.inputs.locked else '',
                             '; '.join(p.start.astimezone(vienna()).strftime('%d.%m. %H:%M')+'–'+p.end.astimezone(vienna()).strftime('%d.%m. %H:%M') for p in b.breaks) if b else ''))
        self.table(self.plan,('Termin','Dienst','Platz','Person','Arbeitsminuten','Fixierung','Konkrete Pause'),rows)
        hours=hours_rows(self.inputs.people,self.blocks+self.inputs.boundary,self.inputs.absences,self.inputs.year,self.inputs.month,accounts=self.profile.accounts,target_profile='S0',month_profile='M0')
        self.table(self.hours,('Person','Soll min','Anfang','Wunschende','Urlaub','Arbeitsziel','Geplant','Prognose Ende','Abweichung'),[(r.person_id,r.target,r.opening,r.desired,r.credits if r.credits_known else 'ungeklärt',r.goal if r.credits_known else 'ungeklärt',r.work,r.projected if r.credits_known else 'ungeklärt',r.deviation if r.credits_known else 'ungeklärt') for r in hours])
        distribution=shares(self.inputs.people,events,self.blocks,policy=self.profile.fairness_policy,absences=self.inputs.absences)
        self.table(self.distribution,('Person','Dienst','Anzahl','Minuten','Fairer Anteil Anzahl','Fairer Anteil Minuten'),[(r.person_id,r.code,r.count,r.work_minutes,str(r.expected_count),str(r.expected_minutes)) for r in distribution])
        wishes=wish_rows(self.inputs.people,self.inputs.absences,events,self.blocks+self.inputs.boundary,policy=self.profile.wish_policy,history=self.profile.history)
        self.table(self.wishes,('Person','Relevant','Erfüllt','Übergangen','Historisch','Kumuliert'),[(r.person_id,len(r.relevant),r.fulfilled_count,len(r.violated),len(r.historical),len(r.cumulative)) for r in wishes])
        if self.events is not None:
            core,calendar=verify(self.inputs,self.blocks,active_events=self.events)
            status=f'{sum(n for _,n in core.open_slots)} offene Plätze; {sum(p.proven and not p.conditional for p in self.proofs)} unbedingt bewiesene Zielstufen. '
            status+=' | '.join(i.message for i in core.issues+calendar.issues)
            status+=' | '+' | '.join(dict.fromkeys(self.inputs.unchecked+calendar.unchecked+self.profile.history.missing))
        else:status='Eingaben ohne berechneten Entwurf; Profile und Monatsvollständigkeit nicht produktiv freigegeben.'
        required=sum((e.service.staff or 0)*(e.attendance.minutes-(30 if e.attendance.minutes>360 else 0)) for e in events if e.service.code!='R')
        target=sum(max(0,r.goal) for r in hours) if all(r.credits_known for r in hours) else None
        status+=f' | Operativer Bedarf ohne ungeklärte R-Bewertung: {required} min; nicht negatives Arbeitsziel gesamt: '+(f'{target} min.' if target is not None else 'ungeklärt.')
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
        path,_=QFileDialog.getSaveFileName(self,'Neue getrennte V2-Testdatei','','SQLite (*.sqlite3)')
        if not path:return
        inputs,profile=self.read_team();new=V2Store(path,create=True)
        try:new.save_workspace(inputs,profile,self.blocks,self.events,expected_revision=0)
        except Exception:new.close();raise
        self.store.close();self.store=new;self.inputs,self.profile=inputs,profile;self.proofs=();self.location.setText(path);self.dirty();self.fill()

    def open_file(self):
        if self.worker and self.worker.isRunning():raise ValueError('Berechnung zuerst abbrechen.')
        path,_=QFileDialog.getOpenFileName(self,'Nur vorbereitete V2-Testdatei öffnen','','SQLite (*.sqlite3)')
        if not path:return
        new=V2Store(path)
        try:
            months=[r[0].removeprefix('workspace:') for r in new.connection.execute("SELECT key FROM v2_meta WHERE key LIKE 'workspace:%' ORDER BY key")]
            if not months:raise ValueError('Datei enthält noch keinen V2-Arbeitsstand.')
            month,ok=QInputDialog.getItem(self,'Testmonat','Monat wählen:',months,0,False)
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
        value,ok=QInputDialog.getText(self,'Testmonat wählen','Monat YYYY-MM (fehlender Monat wird als synthetisches Vier-Termine-Beispiel angelegt):')
        if not ok:return
        year,month=map(int,value.split('-'));date(year,month,1)
        loaded=self.store.load_workspace(year,month)
        if loaded:self.inputs,self.profile,self.blocks,self.events=loaded
        else:
            inputs,profile,_=technical_demo(year,month)
            records=self.store.confirmations();month_key=f'{year:04d}-{month:02d}'
            history=self.store.wish_history(month_key,policy=profile.wish_policy)
            earlier=[v for _,v in records if v['month']<month_key]
            from .accounting import MonthAccount
            balances={r['person_id']:r['projected'] for r in max(earlier,key=lambda v:v['month'])['hours']} if earlier else {}
            profile=replace(profile,history=history,historical_shares=historical_shares(records,start=profile.wish_policy.history_start,month=month_key),
                            accounts=tuple(MonthAccount(p.id,balances.get(p.id,0)) for p in inputs.people))
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
        self.table(contracts,('Von eingeschlossen','Bis ausgeschlossen','Wochenstunden'),[(str(c.dates.start),str(c.dates.end),str(c.weekly_hours)) for c in person.contracts.versions] if person else [('', '', '')],True)
        self.table(rights,('Von eingeschlossen','Bis ausgeschlossen','Erlaubte Kürzel mit Leerzeichen','Führerschein ja/nein/unbekannt'),[(str(r.dates.start),str(r.dates.end),' '.join(sorted(r.codes)),{True:'ja',False:'nein',None:'unbekannt'}[r.driving_license]) for r in person.rights] if person else [('', '', '', 'unbekannt')],True)
        for label,table in (('Vertragsversionen',contracts),('Berechtigungsversionen',rights)):
            box.addWidget(QLabel(label));box.addWidget(table);bar=QHBoxLayout();box.addLayout(bar)
            add=QPushButton('Version ergänzen');remove=QPushButton('Gewählte Version entfernen');bar.addWidget(add);bar.addWidget(remove)
            def append(t=table):
                row=t.rowCount();t.insertRow(row)
                for col in range(t.columnCount()):t.setItem(row,col,QTableWidgetItem(''))
            add.clicked.connect(lambda checked=False,f=append:f())
            remove.clicked.connect(lambda checked=False,t=table:t.removeRow(t.currentRow()) if t.currentRow()>=0 else None)
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
                if not set(codes.split())<={t.code for t in CATALOG}:raise ValueError('Unbekanntes Dienstkürzel in Berechtigungen.')
                permissions.append(Eligibility(DateRange(date.fromisoformat(a),date.fromisoformat(z)),frozenset(codes.split()),{'ja':True,'nein':False,'unbekannt':None}[driver]))
            updated=Person(pid,name.text(),Employment(pid,DateRange(date.fromisoformat(start.text()),date.fromisoformat(end.text()))),Contracts(pid,tuple(versions)),tuple(permissions))
            # Benötigte Soll-Verträge vollständig prüfen, bevor der alte Entwurf entfällt.
            from .accounting import s0_target
            s0_target(updated.contracts,updated.employment,self.inputs.year,self.inputs.month,profile='S0')
            if not self.clear_plan(confirm_only=True):return
            people=tuple(updated if p.id==pid else p for p in self.inputs.people) if person else self.inputs.people+(updated,)
            candidates=tuple(c for c in self.inputs.candidates if c.person_id!=pid)
            for term in self.inputs.events:
                if updated.eligibility_errors(term.service.code,term.attendance) or term.service.code=='R' or (term.fixed_people and pid not in term.fixed_people):continue
                candidates+=pause_candidates(term,pid,policy=PausePolicy('Explizites UI-Testfenster',(term.attendance,),30))
            inputs=replace(self.inputs,people=people,candidates=candidates)
            profile=self.profile if person else replace(self.profile,accounts=self.profile.accounts+(MonthAccount(pid,0),))
            self.store.save_workspace(inputs,profile,expected_revision=self.store.input_revision)
            self.inputs,self.profile,self.blocks,self.events=inputs,profile,(),None;self.proofs=();self.dirty();self.fill();dialog.accept()
        commit.clicked.connect(lambda:self.guard(apply));dialog.resize(950,700);dialog.exec()

    def start(self):
        if self.worker and self.worker.isRunning():return
        if self.save() is False:return
        token=(self.generation,self.store.input_revision,self.inputs.fingerprint,fingerprint(self.profile))
        self.worker=Worker(self.inputs,self.profile,self.blocks,self.events,self.seconds.value(),token,self)
        self.worker.completed.connect(self.on_worker_completed);self.worker.failed.connect(lambda error:self.status.setText('Berechnung fehlgeschlagen: '+error))
        self.worker.finished.connect(lambda:(self.calculate.setEnabled(True),self.stop.setEnabled(False)))
        self.calculate.setEnabled(False);self.stop.setEnabled(True);self.status.setText('Berechnung läuft; Eingabeänderungen machen das Ergebnis veraltet.');self.worker.start()

    def on_worker_completed(self,result,token):
        current=(self.generation,self.store.input_revision,self.inputs.fingerprint,fingerprint(self.profile))
        if current!=token:self.status.setText('Eingaben geändert: Ergebnis veraltet und nicht übernommen.');return
        if result.status in {'unknown','cancelled','infeasible','invalid'}:
            self.status.setText('Noch kein gültiges Ergebnis / Vorgabenkonflikt: '+result.status+'; '+'; '.join(i.message for i in result.issues));return
        self.pending=(result,token);self.accept.setEnabled(True)
        self.status.setText('Prüfbares Ergebnis bereit. '+('Alle gewählten Testzielstufen bewiesen.' if result.global_optimal else 'Kein vollständiger Optimalitätsnachweis.')+' Bitte ausdrücklich übernehmen.')

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
        row=self.plan.currentRow()
        if row<0:raise ValueError('Zuerst eine Planzeile wählen.')
        return self.plan_rows[row]

    def manual(self,blocks,locked=None):
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
        if self.events is None:raise ValueError('Zuerst einen geprüften Entwurf erstellen oder manuell zuteilen.')
        path,_=QFileDialog.getSaveFileName(self,'Neues vollständiges Exportpaket','','ZIP (*.zip)')
        if path:export_package(path,self.inputs,self.profile,self.blocks,self.events,proofs=self.proofs)

    def confirm(self):
        self.ensure_team_saved()
        if self.events is None:raise ValueError('Zuerst einen geprüften Entwurf erstellen.')
        id='test-confirmation/'+fingerprint((self.inputs,self.profile,self.blocks,self.events))
        self.store.confirm(id,self.inputs,self.blocks,self.events,accounts=self.profile.accounts,wish_policy=self.profile.wish_policy,
                           fairness_policy=self.profile.fairness_policy,target_profile='S0',month_profile='M0',expected_revision=self.store.input_revision,synthetic=True)
        self.status.setText('Unveränderlicher synthetischer Testmonat bestätigt; keine produktive V2-Freigabe.')

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.cancel();self.worker.finished.connect(self.close);event.ignore();return
        self.store.close();self.temporary.cleanup();super().closeEvent(event)
