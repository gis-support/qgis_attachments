from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtCore import QDir, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import QgsApplication
from qgis_attachments.backends.base.baseBackend import BackendAbstract
from qgis_attachments.backends.layers.model import LayersModel
from qgis_attachments.backends.base.baseDelegates import OptionButton
from qgis.core import NULL
import subprocess
import tempfile
import sqlite3
import sys
import os

if sys.platform.startswith('linux'):
    #Wyszukanie systemowego menedżera plików
    from shutil import which
    for file_manager in ['nemo', 'nautilus', 'dolphin']:
        if which(file_manager):
            FILE_MANAGER = file_manager
            break
    else:
        FILE_MANAGER = 'xdg-open'

class LayersBackend(BackendAbstract):

    LABEL = 'Geopackage'
    DESCRIPTION = 'Przechowywanie załączników w geopaczce'

    def __init__(self, parent):
        super(LayersBackend, self).__init__([
            OptionButton(QgsApplication.getThemeIcon('/mIconFolder.svg'),
                lambda index, option='saveTemp': self.fileAction(index, option)
            ),
            OptionButton(QgsApplication.getThemeIcon('/mActionSharingExport.svg'),
                lambda index, option='saveToDir': self.fileAction(index, option)
            ),
        ], parent=parent)
        #Ikony są tymczasowo przekopiowane z backendu plików
        self.model = LayersModel(columns=['Opcje', 'Pliki'], separator=self.SEPARATOR)
        self.connection = None
        self.geopackage_path = self.parent.layer().dataProvider().dataSourceUri().split('|')[0]

    def setValue(self, value):
        """Parsowanie tekstu do listy załączników"""
        #Wyczyszczenie listy załączników
        self.model.clear()
        if value == NULL:
            return
        db_ids = value.split( self.SEPARATOR )
        #Wypełnienie lisy załączników
        values = self.getFilenames(db_ids)
        self.model.insertRows(values)

    def getFilenames(self, values):
        """Dodaje informacje o nazwach plików do listy id"""
        self.checkConnection()
        sql = """SELECT name FROM qgis_attachments WHERE id = {}"""
        values_filenames = []
        cursor = self.connection.cursor()
        for value in values:
            query_output = cursor.execute(sql.format(value)).fetchone()
            if len(query_output) > 0:
                values_filenames.append([value, query_output[0]])
        return values_filenames

    def checkConnection(self):
        """Sprawdza czy istnieje połączenie z bazą, tworzy je jeśli nie istnieje"""
        if not self.connection:
            self.connect()

    def addAttachment(self):
        """Dodaje załącznik"""
        if not self.geopackage_path.endswith('.gpkg'):
            self.parent.bar.pushCritical(
                'Błąd',
                'Wybrana warstwa nie znajduje się w geopaczce'
            )
            return
        self.connect()
        self.parent.widget.setFocus()
        files, _ = QFileDialog.getOpenFileNames(self.parent.widget, 'Wybierz załączniki')
        files_indexes = self.saveAttachments(files)
        result = self.model.insertRows(files_indexes, max_length=self.parent.field().length())
        return result

    def deleteAttachment(self):
        """Usuwa załącznik"""
        self.checkConnection()
        selected = self.parent.widget.tblAttachments.selectedIndexes()
        if len(selected) < 1:
            self.parent.bar.pushCritical(
                'Błąd',
                'Nie wybrano obiektów do usunięcia'
            )
            return
        index = selected[0]
        sql = """DELETE FROM qgis_attachments where id = {}"""
        cursor = self.connection.cursor()
        cursor.execute(sql.format(self.model.data(index, field='id')))
        self.connection.commit()
        self.model.removeRow(index.row())
        cursor.close()
        self.connection.close()

    def connect(self):
        """Tworzy połączenie z bazą danych i tabelę jeśli ta nie istnieje"""
        self.connection = sqlite3.connect(self.geopackage_path)
        sql = """CREATE TABLE IF NOT EXISTS qgis_attachments (
                id INTEGER PRIMARY KEY,
                name TEXT,
                data BLOB
            )"""
        self.connection.execute(sql)

    def saveAttachments(self, files_list):
        """Zapisuje załączniki i zwraca listę id"""
        self.checkConnection()
        sql = """INSERT INTO qgis_attachments (name, data) VALUES (?, ?)"""
        cursor = self.connection.cursor()
        ids = []
        for file in files_list:
            with open(file, 'rb') as f:
                name = os.path.basename(file)
                blob = f.read()
                cursor.execute(sql, (name, sqlite3.Binary(blob)))
                ids.append([str(cursor.lastrowid), name])
                self.connection.commit()
        cursor.close()
        return ids

    def fileAction(self, index, option):
        """Zapisuje plik do katalogu tymczasowego lub wskazanego przez użytkownika"""
        self.checkConnection()
        save_dir = ''
        if option == 'saveTemp':
            save_dir = tempfile.gettempdir()
        elif option == 'saveToDir':
            self.parent.widget.setFocus()
            save_dir = QFileDialog.getExistingDirectory(self.parent.widget, 'Wybierz folder')
        cursor = self.connection.cursor()
        sql = """SELECT name, data FROM qgis_attachments WHERE id = ?"""
        db_id = self.model.data(index)[0]
        file_name, file_data = cursor.execute(sql, db_id).fetchone()
        cursor.close()
        file_path = os.path.join(save_dir, file_name)
        with open(file_path, 'wb') as f:
            f.write(file_data)
        if sys.platform == 'win32':
            #Windows
            subprocess.call(f'explorer /select,"{file_path}"', shell=True)
        elif sys.platform.startswith('linux'):
            #Otworzenie katalogu w systemowym menedżerze plików na Linux
            subprocess.Popen( f'{FILE_MANAGER} {file_path}', shell=True )        
