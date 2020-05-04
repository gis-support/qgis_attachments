# coding: utf-8

from qgis.PyQt.QtCore import Qt, QLocale, QFileInfo
from qgis_attachments.backends.base.baseModel import AttachmentsAbstractModel

class FilesModel(AttachmentsAbstractModel):
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return
        item = self.items[index.row()]
        if role == Qt.ToolTipRole:
            #Dodatkowe informacje o pliku w formie podpowiedzi
            if index.column()!=1:
                return
            file_info = QFileInfo(item.value)
            size = QLocale().formattedDataSize( file_info.size(), format=QLocale.DataSizeTraditionalFormat )
            return f'Rozmiar: {size}'
        return super(FilesModel, self).data(index, role)