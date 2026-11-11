"""Verständliche lokale Datumswahl für Urlaub und Freiwünsche."""
from datetime import date,datetime,time,timedelta
from fractions import Fraction

from PySide6.QtCore import Qt,QDate,QTime
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QHBoxLayout,QLabel,QComboBox,
    QDateEdit,QTimeEdit,QCheckBox,QTableWidget,QTableWidgetItem,QPushButton,QLineEdit)

from .errors import DomainError
from .time import Interval,day_segments,local_instant,midnight,vienna
from .presentation import contract_text,hours_text
from .accounting import round_minutes

WEEKDAYS=('Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag')
KINDS=(('Urlaub','urlaub'),('Einzelner Freiwunsch','freiwunschtag'),('Freies Wochenende gewünscht','wochenendwunsch'))


def qdate(day):return QDate(day.year,day.month,day.day)


class AbsenceDialog(QDialog):
    """Ein ausdrücklich gewählter Urlaubszeitraum rechnet jeden Kalendertag an."""
    def __init__(self,window,old=None):
        super().__init__(window);self.window=window;self.old=old;self._updating=False
        self.setWindowTitle('Urlaub oder Freiwunsch bearbeiten' if old else 'Urlaub oder Freiwunsch hinzufügen')
        self.resize(760,650)
        layout=QVBoxLayout(self);form=QFormLayout();self.form=form;layout.addLayout(form)
        self.person=QComboBox();self.person.setObjectName('absence_person')
        for p in window.inputs.people:self.person.addItem(f'{p.name} ({p.id})',p.id)
        if old:self.person.setCurrentIndex(self.person.findData(old.person_id));self.person.setEnabled(False)
        self.kind=QComboBox();self.kind.setObjectName('absence_kind')
        for text,key in KINDS:self.kind.addItem(text,key)
        self.kind.setCurrentIndex(self.kind.findData(old.kind if old else 'freiwunschtag'))
        first=date(window.inputs.year,window.inputs.month,1)
        start=old.span.start.astimezone(vienna()) if old else datetime.combine(first,time())
        end=old.span.end.astimezone(vienna()) if old else datetime.combine(first+timedelta(days=1),time())
        whole=start.time()==time() and end.time()==time()
        self.all_day=QCheckBox('Ganztägig');self.all_day.setObjectName('absence_all_day');self.all_day.setChecked(whole)
        self.first=QDateEdit(qdate(start.date()));self.first.setObjectName('absence_start_date')
        self.last=QDateEdit(qdate(end.date()-timedelta(days=1) if whole else end.date()));self.last.setObjectName('absence_end_date')
        for field in (self.first,self.last):field.setDisplayFormat('dd.MM.yyyy');field.setCalendarPopup(True)
        self.start_time=QTimeEdit(QTime(start.hour,start.minute));self.start_time.setObjectName('absence_start_time')
        self.end_time=QTimeEdit(QTime(end.hour,end.minute));self.end_time.setObjectName('absence_end_time')
        self.start_fold=QComboBox();self.end_fold=QComboBox()
        for field in (self.start_fold,self.end_fold):
            field.addItem('Zeitumstellung: eindeutige Zeit',None);field.addItem('Herbst: erste Uhrzeit',0);field.addItem('Herbst: zweite Uhrzeit',1)
        if old and not whole:
            for moment,field in ((start,self.start_fold),(end,self.end_fold)):
                naive=moment.replace(tzinfo=None)
                try:local_instant(naive)
                except DomainError:field.setCurrentIndex(field.findData(moment.fold))
        self.end_label=QLabel()
        form.addRow('Person',self.person);form.addRow('Eintrag',self.kind);form.addRow('',self.all_day)
        form.addRow('Erster Tag',self.first);form.addRow(self.end_label,self.last)
        form.addRow('Beginn',self.start_time);form.addRow('Ende',self.end_time)
        form.addRow('Beginn bei Zeitumstellung',self.start_fold);form.addRow('Ende bei Zeitumstellung',self.end_fold)
        self.help=QLabel();self.help.setWordWrap(True);layout.addWidget(self.help)
        self.days=QTableWidget();self.days.setObjectName('leave_credit_days');self.days.setColumnCount(4)
        self.days.setHorizontalHeaderLabels(('Anrechnen','Urlaubstag','Wochenstunden','Gutschrift (h)'));layout.addWidget(self.days)
        self.selection_bar=QHBoxLayout();layout.addLayout(self.selection_bar)
        self.select_all=QPushButton('Alle angezeigten Tage auswählen');self.select_none=QPushButton('Auswahl entfernen')
        self.selection_bar.addWidget(self.select_all);self.selection_bar.addWidget(self.select_none)
        self.total=QLabel();self.total.setObjectName('leave_credit_total');self.total.setWordWrap(True);layout.addWidget(self.total)
        self.comment=QLineEdit(old.comment if old else '');self.comment.setObjectName('absence_comment');form.addRow('Kommentar (optional)',self.comment)
        self.save=QPushButton('Eintrag speichern');self.save.setObjectName('absence_save');cancel=QPushButton('Abbrechen')
        buttons=QHBoxLayout();buttons.addWidget(self.save);buttons.addWidget(cancel);layout.addLayout(buttons);cancel.clicked.connect(self.reject)
        for field in (self.first,self.last):field.dateChanged.connect(self.rebuild)
        self.all_day.toggled.connect(self.rebuild);self.kind.currentIndexChanged.connect(self.rebuild);self.person.currentIndexChanged.connect(self.rebuild)
        for field in (self.start_time,self.end_time):field.timeChanged.connect(self.rebuild)
        for field in (self.start_fold,self.end_fold):field.currentIndexChanged.connect(self.rebuild)
        self.days.itemChanged.connect(self.update_total)
        self.select_all.clicked.connect(lambda:self.set_days(True));self.select_none.clicked.connect(lambda:self.set_days(False))
        self._initial_days=old.credit_days if old else frozenset();self.rebuild();self._initial_days=None

    def span(self):
        start=self.first.date().toPython();end=self.last.date().toPython()
        if self.all_day.isChecked():return Interval(midnight(start),midnight(end+timedelta(days=1)))
        return Interval(local_instant(datetime.combine(start,self.start_time.time().toPython()),fold=self.start_fold.currentData()),
                        local_instant(datetime.combine(end,self.end_time.time().toPython()),fold=self.end_fold.currentData()))

    def selected_days(self):
        return frozenset(self.days.item(row,0).data(Qt.ItemDataRole.UserRole) for row in range(self.days.rowCount())
                         if self.days.item(row,0).checkState()==Qt.CheckState.Checked)

    def rebuild(self,*_):
        if self._updating:return
        self._updating=True
        selected=self.selected_days() if self._initial_days is None else self._initial_days
        whole=self.all_day.isChecked();leave=self.kind.currentData()=='urlaub'
        for field in (self.start_time,self.end_time,self.start_fold,self.end_fold):self.form.setRowVisible(field,not whole)
        self.end_label.setText('Letzter Tag (einschließlich)' if whole else 'Enddatum (Endzeit nicht enthalten)')
        for field in (self.start_time,self.end_time,self.start_fold,self.end_fold):field.setEnabled(not whole)
        self.help.setText('Jeder Tag im gewählten Urlaubszeitraum zählt als ein Urlaubstag, auch Samstag, Sonntag und Feiertag. Pro Tag gilt: an diesem Tag gültige Wochenstunden ÷ 5. Beim Speichern wird die gesamte angezeigte Tagesmenge übernommen.' if leave else
                          'Ganztägig gilt der Zeitraum vom ersten bis einschließlich letzten Tag. Bei Uhrzeiten zählt das Ende nicht mehr zum Zeitraum. Zeiten gelten für Wien.')
        self.days.setVisible(leave);self.select_all.setVisible(False);self.select_none.setVisible(False)
        self.days.setRowCount(0)
        self._span_error=''
        try:
            span=self.span();days=tuple(d for d,_ in day_segments(span))
            if len(days)>366:raise DomainError('Bitte den Eintrag in Zeiträume von höchstens einem Jahr aufteilen.')
            person=next(p for p in self.window.inputs.people if p.id==self.person.currentData())
            for i,day in enumerate(days):
                self.days.insertRow(i);check=QTableWidgetItem();check.setFlags(Qt.ItemFlag.ItemIsEnabled)
                check.setData(Qt.ItemDataRole.UserRole,day);check.setCheckState(Qt.CheckState.Checked if leave or day in selected else Qt.CheckState.Unchecked)
                self.days.setItem(i,0,check)
                try:
                    hours=person.contracts.at(day).weekly_hours
                    value=contract_text(hours/5);weekly=contract_text(hours)
                except DomainError:value='Vertrag fehlt';weekly='Vertrag fehlt'
                for j,value in enumerate((day.strftime('%d.%m.%Y')+' · '+WEEKDAYS[day.weekday()],weekly,value),1):
                    item=QTableWidgetItem(value);item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable);self.days.setItem(i,j,item)
            self.days.resizeColumnsToContents()
        except (DomainError,ValueError) as exc:self._span_error=str(exc)
        self._updating=False;self.update_total()

    def set_days(self,checked):
        for row in range(self.days.rowCount()):self.days.item(row,0).setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def update_total(self,*_):
        if self._updating:return
        leave=self.kind.currentData()=='urlaub';selected=self.selected_days()
        error=self._span_error
        totals={}
        if leave and selected:
            person=next(p for p in self.window.inputs.people if p.id==self.person.currentData())
            try:
                for day in selected:
                    if not person.employment.dates.includes(day):raise DomainError('Ein ausgewählter Urlaubstag liegt außerhalb der Beschäftigung.')
                    key=day.strftime('%Y-%m');totals[key]=totals.get(key,Fraction(0))+person.contracts.at(day).weekly_hours*60/5
            except DomainError as exc:error=str(exc)
        if error:text=error
        elif leave and not selected:text='Bitte mindestens einen Urlaubstag ankreuzen. Erst dann kann die Stundengutschrift berechnet werden.'
        elif leave:text=f'{len(selected)} ausgewählte Urlaubstage · Gutschrift {hours_text(sum(round_minutes(value) for value in totals.values()))} h (bei Monatsgrenzen je Monat gerundet)'
        else:text='Der Eintrag wird vor dem Speichern geprüft. Wünsche können durch nötige Dienstbesetzung übergangen werden.'
        self.total.setText(text);self.save.setEnabled(not error and (not leave or bool(selected)))

    def fields(self):
        span=self.span();leave=self.kind.currentData()=='urlaub';selected=self.selected_days()
        if leave and not selected:raise DomainError('Bitte die anrechenbaren Urlaubstage auswählen.')
        return self.person.currentData(),self.kind.currentData(),span.start.astimezone(vienna()).isoformat(),span.end.astimezone(vienna()).isoformat(),'|'.join(map(str,sorted(selected))) if leave else '',self.comment.text()
