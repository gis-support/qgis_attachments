# coding: utf-8

from qgis.PyQt.QtCore import Qt, QAbstractTableModel, QModelIndex

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
    
    def __init__(self, items=[], columns=['Załącznik'], parent=None):
        super(AttachmentsAbstractModel, self).__init__(parent)
        self.items = items
        self.columns = columns
    
    def rowCount(self, parent=QModelIndex()):
        return len(self.items)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)
    
    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section]
    
    def data(self, index, role):
        if not index.isValid():
            return
        item = self.items[index.row()]
        if role == Qt.DisplayRole:
            return item.value
        elif role == Qt.UserRole:
            return item
    
    def insertRows(self, rows, position=None, parent=QModelIndex()):
        if position is None:
            position = self.rowCount()
        self.beginInsertRows(parent, position, position + len(rows) - 1)
        for i, item in enumerate(rows):
            self.items.insert(position+i, AttachmentItem(item))
        self.endInsertRows()
    
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
    
    def serialize(self, separator):
        """ Konwersja listy załączników do tekstu, który można zapisać w tabeli atrybutów """
        return separator.join( item.serialize() for item in self.items )