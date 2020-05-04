# coding: utf-8

from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.core import NULL, QgsProject, QgsApplication
from qgis_attachments.backends.base.baseBackend import BackendAbstract
from qgis_attachments.backends.files.model import FilesModel
from qgis_attachments.backends.base.baseDelegates import OptionButton
from pathlib import Path

class FilesBackend(BackendAbstract):
    """ Przechowuje ścieżki plików w tabeli atrybutów """

    #Nazwa wyświetlana na liście (unikalna)
    LABEL = 'Pliki'
    #Opis
    DESCRIPTION = 'Przechowuje ścieżki do plików z dysku lokalnego.'

    def __init__(self):
        super(FilesBackend, self).__init__([
            OptionButton(QgsApplication.getThemeIcon('/mIconFolder.svg'), self.openFolder),
            OptionButton(QgsApplication.getThemeIcon('/mIconFile.svg'), self.openFile),
        ])
        #Utworzenie modelu dla listy załączników
        self.model = FilesModel(columns=['Opcje', 'Pliki'])

    # KONFIGURACJA

    def createConfigWidget(self):
        """ Utworzenie kontrolki z kofiguracją """
        ui_path = Path(__file__).parent.joinpath('config.ui')
        self.configWidget = uic.loadUi(str(ui_path))
        return self.configWidget
    
    def config(self):
        """Zapis ustawień konfiguracji"""
        return {'relative':self.configWidget.cbRelativePaths.isChecked()}

    def setConfig(self, config):
        """Odczyt ustawień i dostosowanie GUI"""
        self.configWidget.cbRelativePaths.setChecked( config.get('relative', False) )

    # FORMULARZ
    
    def addAttachment(self, parent):
        """Dodanie nowego załącznika"""
        files, _ = QFileDialog.getOpenFileNames(parent.widget, 'Wybierz załączniki')
        if parent.config().get('relative', False):
            #Jeśli użytkownik wskazał zapis ściżek relatywnych to konwertujemy pełne ścieżki
            project_path = Path( QgsProject.instance().absolutePath() )
            _files = []
            for file_path in files:
                try:
                    _files.append( str(Path(file_path).relative_to(project_path)) )
                except ValueError:
                    #Konwersja nieudana, więc zapisujemy pełną ścieżkę
                    _files.append(file_path)
            files = _files
        self.model.insertRows(files)
    
    def deleteAttachment(self, parent):
        """Usunięcie zaznaczonych załączników"""
        selected = parent.widget.tblAttachments.selectedIndexes()
        if not selected:
            return
        rows = [ index.row() for index in selected ]
        self.model.removeRow(rows[0])

    def openFolder(self, index):
        print( 'openFolder' )
    
    def openFile(self, index):
        print( 'openFile' )
