# coding: utf-8

from qgis.PyQt.QtCore import Qt, QAbstractTableModel, QModelIndex, QFileInfo
from qgis.PyQt.QtWidgets import QFileIconProvider

icons_db = QFileIconProvider()

class AttachmentItem:
    """ Klasa reprezentująca pojedynczy załącznik na liście """

    def __init__(self, value):
        self.deserialize( value )
    
    def deserialize(self, value):
        """ Konwersja tekstu na dane załącznika """
        self.value = value
    
    def serialize(self):
        """ Konwersja klasy na tekst do zapisu w tabeli atrybutów """
        return self.value

class AttachmentsAbstractModel(QAbstractTableModel):
    """ Bazowy model dla listy załączników """
    
    def __init__(self, items=[], columns=['Załącznik'], separator=';', parent=None):
        super(AttachmentsAbstractModel, self).__init__(parent)
        self.items = items
        self.columns = columns
        self.separator = separator
    
    def rowCount(self, parent=QModelIndex()):
        return len(self.items)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)
    
    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section]
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return
        item = self.items[index.row()]
        if role == Qt.DisplayRole:
            #Wyświetlany tekst
            return item.value
        elif role == Qt.DecorationRole:
            icon = icons_db.icon( QFileInfo(item.value) )
            return icon
        elif role == Qt.UserRole:
            return item
    
    def insertRows(self, rows, position=None, parent=QModelIndex(), max_length=-1):
        if position is None:
            position = self.rowCount()
        self.beginInsertRows(parent, position, position + len(rows) - 1)
        for i, item in enumerate(rows):
            self.items.insert(position+i, AttachmentItem(item))
        #Sprawdzamy czy nie została przekroczona max ilośc znaków w polu
        if max_length>0 and len(self.serialize())>max_length:
            del self.items[position:position+len(rows)]
            return False
        self.endInsertRows()
        return True
    
    def insertRow(self, data, position=None, parent=QModelIndex()):
        if position is None:
            position = self.rowCount()
        self.insertRows([ data ], position)
    
    def clear(self, parent=QModelIndex()):
        self.beginRemoveRows(parent, 0, self.rowCount()-1)
        self.items = []
        self.endRemoveRows()
    
    def removeRows(self, row=0, count=None, parent=QModelIndex()):
        if count==None:
            count = len(self.items)
        self.beginRemoveRows(parent, row, row+count-1)
        del self.items[row:count+row]
        self.endRemoveRows()
    
    def removeRow(self, row):
        self.removeRows(row, 1)
    
    def serialize(self):
        """ Konwersja listy załączników do tekstu, który można zapisać w tabeli atrybutów """
        return self.separator.join( item.serialize() for item in self.items )