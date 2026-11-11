"""Lokale Excel-/CSV-Bediengrenze. Formeln werden niemals ausgeführt."""
import calendar
import csv
from datetime import date, datetime
from pathlib import Path
from hashlib import sha256
import io

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .errors import DomainError
from .time import vienna,day_segments,Interval,midnight

COLUMNS=('quelle','person_ref','person_id','datum','art','dienst','fixiert','beginn','ende','gutschrifttage','kommentar','pause_von','pause_bis','budgetmonat')
WEEKDAYS=('Mo','Di','Mi','Do','Fr','Sa','So')
YELLOW='FFFFFF00'


def _text(value):
    if value is None:return ''
    if isinstance(value,(datetime,date)):return value.isoformat()
    return str(value).strip()


def _field_text(key,value):
    if isinstance(value,(datetime,date)):
        if key=='budgetmonat':return value.strftime('%Y-%m')
        if key in {'datum','gutschrifttage'}:return value.date().isoformat() if isinstance(value,datetime) else value.isoformat()
    return _text(value)


def read_import(path, *, source_kind='plan'):
    """Normformat oder die konkrete anonymisierte Person×Datum-Tabellenform."""
    path=Path(path)
    if path.stat().st_size>16*1024*1024:raise DomainError('Datei ist zu groß (höchstens 16 MiB).')
    if path.suffix.lower()=='.csv':
        text=path.read_text(encoding='utf-8-sig')
        if not text.strip():raise DomainError('Die Importdatei ist leer.')
        reader=csv.DictReader(io.StringIO(text),delimiter=';' if text.splitlines()[0].count(';') else ',',strict=True)
        try:
            fields=reader.fieldnames or ()
            if not set(COLUMNS[:11])<=set(fields) or len(fields)!=len(set(fields)):raise DomainError('CSV benötigt eindeutige dokumentierte Importspalten.')
            rows=[]
            for r in reader:
                if None in r or any(v is None for v in r.values()):raise DomainError(f'CSV-Zeile {reader.line_num}: Spaltenzahl stimmt nicht mit der Kopfzeile überein.')
                if len(rows)>=20000:raise DomainError('Höchstens 20.000 Importzeilen zulässig.')
                rows.append({k:_text(r.get(k)) for k in COLUMNS})
        except csv.Error as exc:raise DomainError(f'CSV-Zeile {reader.line_num} kann nicht gelesen werden: {exc}') from exc
        return tuple(rows),{},()
    if path.suffix.lower()!='.xlsx':raise DomainError('Bitte XLSX oder CSV verwenden.')
    if path.stat().st_size>16*1024*1024:raise DomainError('Excel-Datei ist zu groß (höchstens 16 MiB).')
    import zipfile
    with zipfile.ZipFile(path) as archive:
        if sum(i.file_size for i in archive.infolist())>64*1024*1024:raise DomainError('Entpackte Excel-Datei ist zu groß.')
    book=load_workbook(path,data_only=False,keep_links=False)
    try:
        if any(s.max_row>20000 or s.max_column>64 for s in book):raise DomainError('Zu viele Zeilen oder Spalten für einen Monatsimport.')
        mapping={};rows=[];notes=[]
        if 'Personen' in book:
            for ref,pid,*_ in book['Personen'].iter_rows(min_row=2,values_only=True):
                if ref:
                    if _text(ref) in mapping:raise DomainError('Doppelte Personenreferenz in der Zuordnung.')
                    mapping[_text(ref)]=_text(pid)
        if 'Import' in book:
            sheet=book['Import'];header=[_text(c.value) for c in sheet[1]]
            if len(header)!=len(set(header)) or not set(COLUMNS[:11])<=set(header):raise DomainError('Importblatt benötigt eindeutige dokumentierte Spalten.')
            for line in sheet.iter_rows(min_row=2):
                if not any(c.value is not None for c in line):continue
                if any(c.data_type=='f' for c in line):raise DomainError(f'Zeile {line[0].row}: Formeln sind im Importblatt nicht erlaubt.')
                item={k:_field_text(k,line[header.index(k)].value) if k in header else '' for k in COLUMNS}
                item['person_id']=mapping.get(item['person_ref'],'') or item['person_id']
                rows.append(item)
            return tuple(rows),mapping,tuple(notes)
        sheet=book.active
        # Vorlagen verwenden externe Formeln in der Datumskopfzeile. Ausschließlich
        # gespeicherte Cachewerte lesen, niemals Verknüpfungen öffnen/rechnen.
        cached=load_workbook(path,data_only=True,keep_links=False)
        try:
            head=cached[sheet.title][1]
            days={c.column:c.value.date() if isinstance(c.value,datetime) else c.value for c in head if isinstance(c.value,(datetime,date))}
        finally:cached.close()
        if len(set(days.values()))!=len(days):raise DomainError('Doppelte Datumsüberschriften.')
        if not days:raise DomainError('Keine Datumsüberschriften gefunden. Bitte die Importvorlage verwenden.')
        for line in sheet.iter_rows(min_row=4):
            ref=f'Zeile {line[0].row}'
            for cell in line:
                if cell.column not in days or cell.value is None:continue
                if cell.data_type=='f':raise DomainError(f'{cell.coordinate}: Formel nicht als Eingabe zugelassen.')
                code=_text(cell.value).upper();day=days[cell.column]
                color=cell.fill.fgColor
                if source_kind=='wishes' and ((color.type=='theme' and color.theme==9) or (color.type=='rgb' and str(color.rgb).upper()[-6:] in {'00FF00','92D050','70AD47'})):continue
                kind='dienst'
                if code=='NH':notes.append(f'{cell.coordinate}: NH wie beauftragt ignoriert.');continue
                if code=='X':
                    if source_kind=='plan':continue  # Plan-X bedeutet kein Dienst, kein erfundener Wunsch.
                    color=cell.fill.fgColor
                    if color.type!='rgb' or str(color.rgb).upper()[-6:]!='FFFF00':continue
                    kind='freiwunschtag';code=''
                elif code=='U':kind='urlaub'
                mapping.setdefault(ref,'')
                if code=='KC10' and day.weekday()==3:
                    code='KCT10';notes.append(f'{cell.coordinate}: Donnerstag als KCT10 bis 17:30 übernommen.')
                row=dict(zip(COLUMNS,(f'{sheet.title}!{cell.coordinate}',ref,'',day.isoformat(),kind,code,'ja','','',day.isoformat() if kind=='urlaub' else '', 'Aus Originaltabelle übernommen')))
                rows.append(row)
        return tuple(rows),mapping,tuple(notes)
    finally:book.close()


def _safe(value):
    return _text(value)


def _save(book,path):
    # Zelltyp ausdrücklich Text: auch IDs/Namen mit = oder + bleiben Daten.
    for sheet in book:
        for row in sheet:
            for cell in row:
                if isinstance(cell.value,str):cell.data_type='s'
    import os,tempfile
    handle,temporary=tempfile.mkstemp(prefix='.dienstplan-excel-',suffix='.xlsx',dir=path.parent)
    os.close(handle)
    try:
        book.save(temporary)
        with open(temporary,'r+b') as stream:os.fsync(stream.fileno())
        os.link(temporary,path)
    finally:
        book.close();Path(temporary).unlink(missing_ok=True)


def _decorate(sheet,freeze='C3'):
    sheet.freeze_panes=freeze;sheet.sheet_view.showGridLines=False
    sheet.sheet_properties.pageSetUpPr.fitToPage=True
    sheet.page_setup.orientation='landscape';sheet.page_setup.paperSize=sheet.PAPERSIZE_A3
    sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=0
    sheet.print_options.horizontalCentered=True
    for row in sheet:
        for cell in row:
            cell.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
    sheet.print_title_rows='1:2'


def write_import_template(path, rows, mapping, notes=()):
    path=Path(path)
    if path.exists():raise FileExistsError(path)
    book=Workbook();sheet=book.active;sheet.title='Import';sheet.append(COLUMNS)
    for r in rows:sheet.append([_safe(r.get(k,'')) for k in COLUMNS])
    sheet.auto_filter.ref=sheet.dimensions;sheet.freeze_panes='D2'
    for col in range(1,len(COLUMNS)+1):sheet.column_dimensions[get_column_letter(col)].width=20
    people=book.create_sheet('Personen');people.append(('person_ref','person_id','Hinweis'))
    for ref,pid in mapping.items():people.append((_safe(ref),_safe(pid),'Hier dieselbe stabile ID wie in der App eintragen.'))
    people.column_dimensions['A'].width=20;people.column_dimensions['B'].width=22;people.column_dimensions['C'].width=65
    hints=book.create_sheet('Hinweise')
    for line in ('Nur im Blatt Personen die IDs ergänzen; Importzeilen werden zentral zugeordnet.',
                 'art: dienst (mit Person = Zuteilung, ohne Person = Termin), termin, freiwunschtag, urlaub, ignorieren.',
                 'Fixierte Dienste: fixiert=ja. Pausen werden automatisch gewählt.',
                 'Unbekannte Kürzel, R-Zeitfenster und Regelkonflikte in der Vorschau korrigieren; kein fehlerhafter Teilimport.',
                 'Jedes U-Datum zählt als ein Urlaubstag mit gültigen Wochenstunden ÷ 5, auch am Wochenende/Feiertag. Mehrtägige Urlaubseinträge benötigen ihre konkret markierten Tage.',
                 'Bisherige Donnerstag-/Wunschbudgetregeln gelten bis zu ihrer ausdrücklichen Änderung.',*notes):hints.append((_safe(line),))
    hints.column_dimensions['A'].width=115
    for tab in book:
        for cell in tab[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='31566F')
    _save(book,path)


def export_month_grid(path,inputs,profile,blocks,events):
    """Excel-Personenzeilen und Datums-/Wochentagsspalten wie in der Vorlage."""
    path=Path(path)
    if path.exists():raise FileExistsError(path)
    book=Workbook();sheet=book.active;sheet.title='Monatsübersicht'
    days=[date(inputs.year,inputs.month,n) for n in range(1,calendar.monthrange(inputs.year,inputs.month)[1]+1)]
    sheet.append(['ID','Name']+days);sheet.append(['','Wochentag']+[WEEKDAYS[d.weekday()] for d in days])
    for person in inputs.people:
        values=[]
        for day in days:
            codes=[b.code for b in blocks if b.person_id==person.id and b.attendance.start_day==day]
            wishes=[e for e in inputs.absences if e.person_id==person.id and any(d==day for d,_ in day_segments(e.span))]
            values.append('\n'.join(codes) if codes else 'U' if any(e.kind=='urlaub' for e in wishes) else 'X' if wishes else '')
        sheet.append([_safe(person.id),_safe(person.name)]+values)
    sheet.column_dimensions['A'].width=15;sheet.column_dimensions['B'].width=25
    for j,day in enumerate(days,3):
        sheet.column_dimensions[get_column_letter(j)].width=7
        for row in sheet:
            cell=row[j-1]
            if row[0].row==1:cell.number_format='DD.MM.'
            if row[0].row<=2:cell.fill=PatternFill('solid',fgColor='31566F');cell.font=Font(color='FFFFFF',bold=True)
            elif cell.value=='X':cell.fill=PatternFill('solid',fgColor='FFF2CC')
            elif day.weekday()>=5:cell.fill=PatternFill('solid',fgColor='E7EEF5')
    sheet.row_dimensions[1].height=26
    for row in range(3,sheet.max_row+1):sheet.row_dimensions[row].height=30
    _decorate(sheet)
    # Vollständige Einzelzeilen und zentrale IDs machen auch diesen Export reimportierbar.
    import_sheet=book.create_sheet('Import');import_sheet.append(COLUMNS)
    for b in blocks:
        if (b.attendance.start_day.year,b.attendance.start_day.month)!=(inputs.year,inputs.month):continue
        term=next(e for e in events if e.id==b.id)
        import_sheet.append([_safe(v) for v in (b.id,b.person_id,b.person_id,b.attendance.start_day.isoformat(),'dienst',term.service.key,'ja' if b in inputs.locked else 'nein',b.attendance.start.astimezone(vienna()).isoformat(),b.attendance.end.astimezone(vienna()).isoformat(),'', 'Exportierter Dienst',b.breaks[0].start.astimezone(vienna()).isoformat() if b.breaks else '',b.breaks[0].end.astimezone(vienna()).isoformat() if b.breaks else '')])
    month_span=Interval(midnight(days[0]),midnight(date(inputs.year+int(inputs.month==12),inputs.month%12+1,1)))
    for entry in inputs.absences:
        if not entry.span.overlaps(month_span):continue
        import_sheet.append([_safe(v) for v in (entry.id,entry.person_id,entry.person_id,entry.span.start.astimezone(vienna()).date().isoformat(),entry.kind,'','',entry.span.start.astimezone(vienna()).isoformat(),entry.span.end.astimezone(vienna()).isoformat(),'|'.join(map(str,sorted(entry.credit_days))),entry.comment,'','',entry.budget_month or '')])
    people=book.create_sheet('Personen');people.append(('person_ref','person_id'))
    for p in inputs.people:people.append((_safe(p.id),_safe(p.id)))
    from .solver import verify
    core,calendar_report=verify(inputs,blocks,active_events=events)
    warnings=book.create_sheet('Regelmeldungen');warnings.append(('Status','Meldung'))
    warnings.append(('REGELÜBERSTEUERUNG' if inputs.manual_override else 'Prüfung','Kein Regelkonformitätsnachweis' if inputs.manual_override else 'Regelprüfung'))
    for message in dict.fromkeys(inputs.override_notes+tuple(i.message for i in core.issues+calendar_report.issues)):warnings.append(('Verstoß',_safe(message)))
    opened=book.create_sheet('Offene Plätze');opened.append(('Datum','Wochentag','Dienst','Offene Plätze'))
    for e in events:
        missing=(e.service.staff or 0)-sum(b.id==e.id for b in blocks)
        if missing>0:opened.append((e.attendance.start_day.isoformat(),WEEKDAYS[e.attendance.start_day.weekday()],e.service.key,missing))
    from .reporting import hours_rows
    hours=book.create_sheet('Stunden');hours.append(('ID','Soll h','Anfang h','Wunschende h','Urlaub h','Arbeitsziel h','Geplant h','Prognose Ende h'))
    from .presentation import hours_text
    for r in hours_rows(inputs.people,blocks,inputs.absences,inputs.year,inputs.month,accounts=profile.accounts,target_profile=profile.target_profile,month_profile=profile.month_profile):
        hours.append([_safe(r.person_id)]+[hours_text(v) if r.credits_known or i in (0,1,2,5) else 'ungeklärt' for i,v in enumerate((r.target,r.opening,r.desired,r.credits,r.goal,r.work,r.projected))])
    metadata=book.create_sheet('Hinweise');metadata.append(('Planprognose, keine Ist-Zeit oder Tarifabrechnung. Freiwünsche X sind übergehbar; U ist Urlaub. Offene Plätze separat prüfen.',))
    metadata.append(('Nicht mit einem bestätigten Monatsstand gleichsetzen. Arbeitsstand/Prüfmanifest für vollständige technische Sicherung separat exportieren.',))
    _save(book,path)
