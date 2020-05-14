from qgis.PyQt.QtWidgets import QFileDialog, QApplication, QDialog
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
import os

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
        self.model = LayersModel(columns=['Opcje', 'Pliki'], separator=self.SEPARATOR)
        self.connection = None
        self.featureActionDlg = None
        self.newFeatureAdded = None
        self.newFeatureIds = []
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

    def featureActionDlgAccepted(self):
        self.newFeatureAdded = None
        self.newFeatureIds = []
        self.featureActionDlg = None

    def featureActionDlgRejected(self):
        cursor = self.connection.cursor()
        for id in self.newFeatureIds:
            cursor.execute(f"""DELETE FROM qgis_attachments WHERE id = {int(id)}""")
        self.connection.commit()
        cursor.close()
        self.newFeatureIds = []

    def getFilenames(self, values):
        """Dodaje informacje o nazwach plików do listy id"""
        self.checkConnection()
        sql = """SELECT name FROM qgis_attachments WHERE id = {}"""
        values_filenames = []
        cursor = self.connection.cursor()
        for value in values:
            try:
                query_output = cursor.execute(sql.format(value)).fetchone()
            except sqlite3.OperationalError:
                query_output = None
            if query_output is None:
                return []
            elif len(query_output) > 0:
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
        #Czyszczenie wpisów w bazie, jeśli tworzenie nowego obiektu nie zostanie zatwierdzone
        if not self.featureActionDlg:
            self.featureActionDlg = self.isFeatureActionDlgOpened()
            if self.featureActionDlg:
                self.newFeatureAdded = True
                self.featureActionDlg.rejected.connect(self.featureActionDlgRejected)
                self.featureActionDlg.accepted.connect(self.featureActionDlgAccepted)
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
                attachment_id = str(cursor.lastrowid)
                if self.newFeatureAdded:
                    self.newFeatureIds.append(attachment_id)
                ids.append([attachment_id, name])
                self.connection.commit()
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

        self.checkConnection()
        save_dir = ''
        sql = """SELECT name, data FROM qgis_attachments WHERE id = {}"""
        cursor = self.connection.cursor()
        file_name, file_data = cursor.execute(sql.format(self.model.data(index, field='id'))).fetchone()
        cursor.close()
        if option == 'saveTemp':
            path = tempfile.gettempdir()
            out_path = saveFile(path, file_data, file_name)
            QDesktopServices.openUrl(QUrl(f'file:///{QDir.toNativeSeparators(out_path)}'))
        elif option == 'saveToDir':
            self.parent.widget.setFocus()
            path, _ = QFileDialog.getSaveFileName()
            out_path = saveFile(path, file_data)
            if out_path:
                self.parent.bar.pushSuccess(
                    'Sukces',
                    f'Pomyślnie wyeksportowano plik {file_name}'
                )

    def isFeatureActionDlgOpened(self):
        """Sprawdza czy otwarte jest okno tworzenia nowego obiektu"""
        for obj in QApplication.instance().allWidgets():
            if self.parent.layer().name() in obj.objectName() and isinstance(obj, QDialog): 
                return obj
        return False
