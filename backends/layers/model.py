from qgis_attachments.backends.base.baseModel import AttachmentsAbstractModel, AttachmentItem
from qgis.PyQt.QtCore import Qt, QAbstractTableModel, QModelIndex, QFileInfo
from qgis.PyQt.QtWidgets import QFileIconProvider

icons_db = QFileIconProvider()

class LayersAttachmentItem(AttachmentItem):
    """Klasa dzedzicząca po AttachmentItem, uwzględnia id obiektów w bazie danych"""
    def __init__(self, value, id):
        super(LayersAttachmentItem, self).__init__(value)
        self.deserialize( value )
        self.id = id

    def serialize(self):
        return self.id

class LayersModel(AttachmentsAbstractModel):

    def data(self, index, role=Qt.DisplayRole, field='value'):
        if not index.isValid():
            return
        item = self.items[index.row()]
        if role == Qt.DisplayRole:
            if field == 'value':
                #Wyświetlany tekst
                return item.value
            elif field == 'id':
                #Identyfikator z bazy
                return item.id
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
            self.items.insert(position+i, LayersAttachmentItem(item[1], item[0]))
        #Sprawdzamy czy nie została przekroczona max ilośc znaków w polu
        if max_length>0 and len(self.serialize())>max_length:
            del self.items[position:position+len(rows)]
            return False
        self.endInsertRows()
        return True
