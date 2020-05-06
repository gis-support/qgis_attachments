from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtCore import QDir
from qgis_attachments.backends.base.baseBackend import BackendAbstract
from qgis_attachments.backends.layers.model import LayersModel
from qgis.utils import iface
import sqlite3
import os

class LayersBackend(BackendAbstract):

    LABEL = 'Geopackage'
    DESCRIPTION = 'Przechowywanie załączników w geopaczce'

    def __init__(self, parent):
        super(LayersBackend, self).__init__(parent=parent)
        #TODO kolumna opcji
        self.model = LayersModel(columns=['Pliki'], separator=self.SEPARATOR)
        self.connection = None

    def addAttachment(self):
        geopackage = iface.activeLayer().dataProvider().dataSourceUri().split('|')[0]
        if not geopackage.endswith('.gpkg'):
            self.parent.bar.pushCritical(
                'Błąd',
                'Wybrana warstwa nie znajduje się w geopaczce'
            )
            return
        if not self.connection:
            self.connectAndCreateTable(geopackage)
        files, _ = QFileDialog.getOpenFileNames(self.parent.widget, 'Wybierz załączniki')
        files_indexes = self.saveAttachments(files)
        result = self.model.insertRows(files_indexes, max_length=self.parent.field().length())
        return result

    def connectAndCreateTable(self, geopackage_path):
        """Tworzy tabelę do przechowywania załączników"""
        self.connection = sqlite3.connect(geopackage_path)
        sql = """CREATE TABLE IF NOT EXISTS qgis_attachments (
                id INTEGER PRIMARY KEY,
                name TEXT,
                data BLOB
            )"""
        self.connection.execute(sql)

    def saveAttachments(self, files_list):
        sql = """INSERT INTO qgis_attachments (name, data) VALUES (?, ?)"""
        cursor = self.connection.cursor()
        ids = []
        for file in files_list:
            with open(file, 'rb') as f:
                name = os.path.basename(file)
                blob = f.read()
                cursor.execute(sql, (name, sqlite3.Binary(blob)))
                ids.append(str(cursor.lastrowid))
        cursor.close()
        return ids
