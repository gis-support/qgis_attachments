from qgis.PyQt.QtWidgets import QFileDialog, QApplication, QDialog
from qgis.PyQt.QtCore import QDir, QUrl, Qt
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import QgsApplication, NULL
from qgis_attachments.backends.base.baseBackend import BackendAbstract
from qgis_attachments.backends.base.baseModel import AttachmentsAbstractModel
from qgis_attachments.backends.layers.model import LayersAttachmentItem
from qgis_attachments.backends.base.baseDelegates import OptionButton
from qgis_attachments.translator import translate
from contextlib import contextmanager
import subprocess
import tempfile
import sqlite3
import os
from collections import defaultdict
from itertools import chain
import json

def nested_dict(func):
    return defaultdict( func )
dict_add = nested_dict(lambda: defaultdict(list) )
dict_delete = nested_dict(lambda: defaultdict(list) )

class AttachmentsBuffer:
    
    #Struktura klucz słowników: warstwa -> pole -> obiekt -> dane
    added = defaultdict( lambda:dict_add )
    deleted = defaultdict( lambda: dict_delete )

    def getFeatures(self, layer, field_id):
        """ Zwraca obiekty przestrzenne danej warstwy, które zostały zmodyfikowane """
        added = self.added.get( layer.id(), {} ).get( field_id, {} )
        deleted = self.deleted.get( layer.id(), {} ).get( field_id, {} )
        fids = set( chain(added.keys(), deleted.keys()))
        return { f.id():f for f in layer.getFeatures(list(fids)) }
    
    def clearLayer(self, layer_id, field_id):
        """ Czyszczenie bufora dla warstwy i pola """
        self.added[layer_id][field_id].clear()
        self.deleted[layer_id][field_id].clear()

buffer = AttachmentsBuffer()

class LayersBackend(BackendAbstract):

    LABEL = translate('LayersBackend', 'Geopaczka')
    NAME = 'layers'
    DESCRIPTION = translate('LayersBackend', 'Przechowuje załączniki w geopaczce.')

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
                columns=[translate('LayersBackend', 'Opcje'), translate('LayersBackend', 'Pliki')],
                separator=self.SEPARATOR,
                ItemClass=LayersAttachmentItem)
        self.geopackage_path = self.parent.layer().dataProvider().dataSourceUri().split('|')[0]
        self.parent.layer().beforeCommitChanges.connect( self.saveData )
        self.parent.layer().afterRollBack.connect( self.rollbackData )
    
    def __del__(self):
        self.parent.layer().beforeCommitChanges.disconnect( self.saveData )
        self.parent.layer().afterRollBack.disconnect( self.rollbackData )
    
    @contextmanager
    def connection(self):
        """ Połączenie z bazą sqlite """
        con = sqlite3.connect(self.geopackage_path)
        # Dodanie tabeli na załączniki, jeśli nie istnieje
        sql = """CREATE TABLE IF NOT EXISTS qgis_attachments (
                id INTEGER PRIMARY KEY,
                name TEXT,
                data BLOB
            )"""
        con.execute(sql)
        yield con
        con.close()

    #Ustawienia
    @staticmethod
    def isSupported(layer):
        return True if layer.dataProvider().dataSourceUri().split('|')[0].endswith('.gpkg') else False

    #Formularz
    def setValue(self, value):
        """Parsowanie tekstu do listy załączników"""
        #Wyczyszczenie listy załączników
        self.model.clear()
        if value == NULL:
            return
        db_ids = value.split( self.SEPARATOR )
        #Wypełnienie lisy załączników
        values = self.getFilenames(db_ids)
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
        return True

    def saveData(self):
        """ Zapis załączników """
        layer = self.sender()
        field_id = self.parent.fieldIdx()
        to_add = buffer.added[layer.id()][field_id]
        to_delete = buffer.deleted[layer.id()][field_id]
        deleted = []
        for fid, feature in buffer.getFeatures(layer, field_id).items():
            #Dodawane załączniki
            added = to_add.pop(fid)
            files = [ f[1] for f in added ]
            files_indexes = [ str(fid) for fid in self.saveAttachments(files) ]
            
            #Usuwanie załączniki
            deleted.extend( to_delete.pop(feature.id(), []) )
            if feature[field_id]:
                #Aktualne wartości z pominięciem dodanych i usuniętych załączników
                current_values = [ v for v in feature[field_id].split(self.SEPARATOR) if v!='-1' and v not in deleted ]
            else:
                # NULL
                current_values = []
            #Scalenie niezmienionych załączników i dodanych
            values = self.SEPARATOR.join( chain(current_values, files_indexes) ) or NULL
            #Zapisanie zmian w obiekcie
            layer.changeAttributeValue(feature.id(), field_id, values)

        #Czyszczenie ewentualnych pozostałości w buforze
        buffer.clearLayer( layer.id(), field_id )
        #Przeładowanie danych warstwy
        layer.reload()

        if not deleted:
            return
        #Skasowanie usuniętych załączników z bazy
        with self.connection() as connection:
            sql = """DELETE FROM qgis_attachments where id IN ({})""".format(','.join(deleted))
            connection.execute(sql)
            connection.commit()
    
    def rollbackData(self):
        """ Koniec edycji bez zapisanych zmian """
        layer = self.sender()
        buffer.clearLayer( layer.id(), self.parent.fieldIdx() )
        layer.reload()

    def saveAttachments(self, files_list):
        """Zapisuje załączniki i zwraca listę id"""
        with self.connection() as connection:
            sql = """INSERT INTO qgis_attachments (name, data) VALUES (?, ?)"""
            cursor = connection.cursor()
            ids = []
            for file in files_list:
                with open(file, 'rb') as f:
                    name = os.path.basename(file)
                    blob = f.read()
                    cursor.execute(sql, (name, sqlite3.Binary(blob)))
                    attachment_id = str(cursor.lastrowid)
                    ids.append(attachment_id)
            connection.commit()
            cursor.close()
        return ids

    def fileAction(self, index, option):
        """Zapisuje plik do katalogu tymczasowego lub wskazanego przez użytkownika"""

        def saveFile(save_dir, file_data, filename=None):
            """Funkcja pomocnicza do zapisu pliku we wskazanym miejscu"""
            path = os.path.join(save_dir, filename) if filename else save_dir
            try:
                with open(path, 'wb') as f:
                    f.write(file_data)
                return path
            except FileNotFoundError:
                #Anulowanie zapisywania
                return

        with self.connection() as connection:
            sql = """SELECT name, data FROM qgis_attachments WHERE id = {}"""
            item = self.model.data(index, Qt.UserRole)
            file_name, file_data = connection.execute(sql.format(item.id)).fetchone()

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
                    translate('LayersBackend', 'Sukces'),
                    '{} {}'.format(
                        translate('LayersBackend', 'Pomyślnie wyeksportowano plik'),
                        file_name
                    )
                )

    def getFilenames(self, values):
        """Dodaje informacje o nazwach plików do listy id"""
        sql = """SELECT name FROM qgis_attachments WHERE id = {}"""
        values_filenames = []
        with self.connection() as connection:
            for value in values:
                try:
                    query_output = connection.execute(sql.format(value)).fetchone()
                    if query_output is None:
                        query_output = connection.execute(sql.format(value)).fetchone()
                    elif len(query_output) > 0:
                        values_filenames.append([value, query_output[0]])
                except sqlite3.OperationalError:
                    #anulowanie wyboru załącznika, value jest puste
                    continue
        return values_filenames
