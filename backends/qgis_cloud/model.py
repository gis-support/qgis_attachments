from qgis_attachments.backends.base.baseModel import AttachmentsAbstractModel, AttachmentItem
from qgis.PyQt.QtCore import Qt, QAbstractTableModel, QModelIndex, QFileInfo
from qgis.PyQt.QtWidgets import QFileIconProvider

icons_db = QFileIconProvider()

class CloudAttachmentItem(AttachmentItem):
    """Klasa dzedzicząca po AttachmentItem, uwzględnia id obiektów w Cloud"""
    def __init__(self, value):
        super(CloudAttachmentItem, self).__init__(value[1])
        self.cloud_id = value[0]

    def serialize(self):
        return self.cloud_id