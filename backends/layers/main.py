#coding: utf-8

from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtCore import QDir, QUrl, Qt
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import QgsApplication, NULL
from qgis_attachments.backends.base.baseBackend import BackendAbstract
from qgis_attachments.backends.base.baseModel import AttachmentsAbstractModel
from qgis_attachments.backends.layers.model import LayersAttachmentItem
from qgis_attachments.backends.layers.buffer import AttachmentsBuffer
from qgis_attachments.backends.base.baseDelegates import OptionButton
from qgis_attachments.backends.layers.sqlite_driver import SQLiteDriver
from qgis_attachments.backends.utils import saveFile
from qgis_attachments.translator import translate
import tempfile
import os
from collections import defaultdict
from itertools import chain
import json

translate_ = lambda msg: translate('LayersBackend', msg)

class LayersBackend(BackendAbstract):

    LABEL = translate_('Geopaczka')
    NAME = 'layers'
    DESCRIPTION = translate_('Przechowuje załączniki w geopaczce.')

    def __init__(self, parent):
        super(LayersBackend, self).__init__([
            OptionButton(QgsApplication.getThemeIcon('mActionFileNew.svg'),
                lambda index, option='saveTemp': self.fileAction(index, option)
            ),
            OptionButton(QgsApplication.getThemeIcon('/mActionSharingExport.svg'),
                lambda index, option='saveToDir': self.fileAction(index, option)
            ),
        ], parent=parent)
        self.model = AttachmentsAbstractModel(
                columns=[translate_('Opcje'), translate_('Pliki')],
                separator=self.SEPARATOR,
                ItemClass=LayersAttachmentItem)
        self.geopackage_path = self.parent.layer().dataProvider().dataSourceUri().split('|')[0]
        buffer.registerLayer( self.parent.layer() )

    #Ustawienia
    @staticmethod
    def isSupported(layer):
        return True if layer.dataProvider().dataSourceUri().split('|')[0].endswith('.gpkg') else False
    
    # FORMATOWANIE TEKSTU
    @classmethod
    def representValue(cls, layer, fieldIndex, config, cache, value):
        layer_path = layer.dataProvider().dataSourceUri().split('|')[0]
        values = value.split(cls.SEPARATOR)
        added_count = values.count('-1')
        filenames = SQLiteDriver.fetchAttachments(layer_path, values, with_ids=False)
        filenames.extend( [translate_('Nowy załącznik')]*added_count )
        return cls.SEPARATOR.join(filenames)

    #Formularz
    def setValue(self, value):
        """Parsowanie tekstu do listy załączników"""
        #Wyczyszczenie listy załączników
        self.model.clear()
        if value == NULL:
            return
        db_ids = value.split( self.SEPARATOR )
        #Wypełnienie lisy załączników
        values = SQLiteDriver.fetchAttachments( self.geopackage_path, db_ids )
        layer = self.parent.layer()
        feature = self.getFeature()
        self.model.insertRows(values)
        #Dodane i niezapisane załączniki
        items = buffer.added[layer.id()][self.parent.fieldIdx()][feature.id()]
        self.model.insertRows( items, max_length=self.parent.field().length())

    def addAttachment(self):
        """Dodaje załącznik"""
        self.parent.widget.setFocus()
        files, _ = QFileDialog.getOpenFileNames(self.parent.widget, 'Wybierz załączniki')
        
        feature = self.getFeature()

        #Nowy załącznik, niezapisane załączniki mają id -1
        items = [ ['-1', f] for f in files ]
        buffer.added[self.parent.layer().id()][self.parent.fieldIdx()][feature.id()].extend( items )
        result = self.model.insertRows( items, max_length=self.parent.field().length())

        return result

    def deleteAttachment(self):
        """Usuwa załącznik"""
        selected = self.parent.widget.tblAttachments.selectedIndexes()
        if len(selected) < 1:
            return
        index = selected[0]
        item = self.model.data(index, Qt.UserRole)
        item.to_delete = True
        self.parent.widget.tblAttachments.model().dataChanged.emit( index, index )
        value_to_delete = item.id
        self.model.removeRow(index.row())

        feature = self.getFeature()
        buffer.deleted[self.parent.layer().id()][self.parent.fieldIdx()][feature.id()].append( value_to_delete )
        added = buffer.added[self.parent.layer().id()][self.parent.fieldIdx()][feature.id()]
        #Sprawdzenie czy usunięty załącznik nie znajduje się na liście dodawanych załączników
        item_to_delete = [value_to_delete, item.value]
        if item_to_delete in added:
            added.pop(added.index(item_to_delete))
        return True

    def fileAction(self, index, option):
        """Zapisuje plik do katalogu tymczasowego lub wskazanego przez użytkownika"""
        item = self.model.data(index, Qt.UserRole)
        file_name, file_data = SQLiteDriver.fetchAttachment( self.geopackage_path, item.id )
        if file_name is None or file_data is None:
            return
        save_dir = ''
        if option == 'saveTemp':
            path = tempfile.gettempdir()
            out_path = saveFile(path, file_data, file_name)
            QDesktopServices.openUrl(QUrl(f'file:///{QDir.toNativeSeparators(out_path)}'))
        elif option == 'saveToDir':
            self.parent.widget.setFocus()
            path, _ = QFileDialog.getSaveFileName(directory=file_name)
            out_path = saveFile(path, file_data)
            if out_path:
                self.parent.bar.pushSuccess(
                    translate_('Sukces'),
                    '{} {}'.format(
                        translate_('Pomyślnie wyeksportowano plik'),
                        file_name
                    )
                )

#Stworzenie instancji bufora edycyjnego załączników
buffer = AttachmentsBuffer(LayersBackend.SEPARATOR)