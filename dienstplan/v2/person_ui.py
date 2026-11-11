"""Kalenderzellen für inklusive, deutsch angezeigte Vertragszeiträume."""
from datetime import date,datetime
from PySide6.QtCore import QDate,QLocale,Qt
from PySide6.QtWidgets import QDateEdit,QComboBox,QStyledItemDelegate


def displayed_date(day):return f'{day.day:02d}.{day.month:02d}.{day.year:04d}'


def parsed_date(text):
    value=text.strip()
    for format in ('%d.%m.%Y','%Y-%m-%d'):
        try:return datetime.strptime(value,format).date()
        except ValueError:pass
    raise ValueError('Bitte ein Datum über den Kalender auswählen, zum Beispiel 31.12.2026.')


def date_edit(day=None,name=''):
    field=QDateEdit();field.setObjectName(name);field.setLocale(QLocale('de_AT'));field.setCalendarPopup(True)
    field.setDateRange(QDate(1,1,1),QDate(9999,12,30));field.setDisplayFormat('dd.MM.yyyy')
    field.setSpecialValueText('Datum auswählen')
    field.setDate(QDate(day.year,day.month,day.day) if day else field.minimumDate())
    return field


class InclusiveDateDelegate(QStyledItemDelegate):
    def createEditor(self,parent,option,index):
        field=date_edit();field.setParent(parent);return field

    def setEditorData(self,editor,index):
        text=index.data(Qt.ItemDataRole.EditRole) or ''
        if text:
            value=parsed_date(text);editor.setDate(QDate(value.year,value.month,value.day))

    def setModelData(self,editor,model,index):
        if editor.date()==editor.minimumDate():return
        model.setData(index,displayed_date(editor.date().toPython()),Qt.ItemDataRole.EditRole)


class DriverDelegate(QStyledItemDelegate):
    def createEditor(self,parent,option,index):
        field=QComboBox(parent);field.addItems(('unbekannt','ja','nein'));return field

    def setEditorData(self,editor,index):editor.setCurrentText(index.data(Qt.ItemDataRole.EditRole) or 'unbekannt')
    def setModelData(self,editor,model,index):model.setData(index,editor.currentText(),Qt.ItemDataRole.EditRole)
