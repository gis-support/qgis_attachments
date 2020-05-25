from qgis_attachments.backends.base.baseModel import AttachmentsAbstractModel, AttachmentItem
from qgis.PyQt.QtCore import Qt, QAbstractTableModel, QModelIndex, QFileInfo
from qgis.PyQt.QtWidgets import QFileIconProvider

icons_db = QFileIconProvider()

class LayersAttachmentItem(AttachmentItem):
    """Klasa dzedzicząca po AttachmentItem, uwzględnia id obiektów w bazie danych"""
    def __init__(self, value):
        super(LayersAttachmentItem, self).__init__(value[1])
        self.id = value[0]

    def serialize(self):
        return self.id
