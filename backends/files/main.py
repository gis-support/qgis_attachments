# coding: utf-8

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtCore import QDir, QFileInfo, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import QgsApplication
from qgis.gui import QgsFileWidget
from qgis_attachments.backends.base.baseBackend import BackendAbstract
from qgis_attachments.backends.files.model import FilesModel
from qgis_attachments.backends.base.baseDelegates import OptionButton
from pathlib import Path
import sys

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
        self.model = FilesModel(columns=['Opcje', 'Pliki'], separator=self.SEPARATOR)

    # KONFIGURACJA

    def createConfigWidget(self):
        """ Utworzenie kontrolki z kofiguracją """
        ui_path = Path(__file__).parent.joinpath('config.ui')
        self.configWidget = uic.loadUi(str(ui_path))
        self.configWidget.fwDirectory.setStorageMode( QgsFileWidget.GetDirectory )
        return self.configWidget
    
    def config(self):
        """Zapis ustawień konfiguracji"""
        if self.configWidget.gbRelativePaths.isChecked():
            if self.configWidget.rbRelativeProject.isChecked():
                relative_mode = QgsFileWidget.RelativeProject
            else:
                relative_mode = QgsFileWidget.RelativeDefaultPath
        else:
            relative_mode = QgsFileWidget.Absolute
        return {
            'relative_mode': relative_mode,
            'relative_directory': self.configWidget.fwDirectory.filePath()
        }

    def setConfig(self, config):
        """Odczyt ustawień i dostosowanie GUI"""
        relative_mode = config.get('relative_mode', QgsFileWidget.Absolute)
        self.configWidget.gbRelativePaths.setChecked( relative_mode!=QgsFileWidget.Absolute )
        self.configWidget.rbRelativeProject.setChecked( relative_mode==QgsFileWidget.RelativeProject )
        self.configWidget.rbRelativeDirectory.setChecked( relative_mode==QgsFileWidget.RelativeDefaultPath )
        self.configWidget.fwDirectory.setFilePath( config.get('relative_directory', '') )
    
    def warnings(self, layer, fieldIdx):
        """ Zwraca dodatkowe informacje o ograniczecniach wskazanego pola """
        field = layer.fields().field( fieldIdx )
        warnings = []
        if field.length()>0:
            warnings.append( f'Wskazane pole może przechowywać do {field.length()} znaków co ogranicza liczbę przechowywanych załączników.' )
        return warnings

    # FORMULARZ
    
    def addAttachment(self, parent):
        """Dodanie nowego załącznika
        Zwraca True w przypadku powodzenia lub False jeśli dodawanie się nie powiodło"""
        files, _ = QFileDialog.getOpenFileNames(parent.widget, 'Wybierz załączniki')
        config = parent.config()
        relative_mode = config.get('relative_mode', QgsFileWidget.Absolute)
        if relative_mode!=QgsFileWidget.Absolute:
            #Jeśli użytkownik wskazał zapis ścieżek relatywnych to konwertujemy pełne ścieżki
            relative_path = QDir( QgsProject.instance().absolutePath() )
            if relative_mode==QgsFileWidget.RelativeDefaultPath:
                relative_path = QDir( config.get('relative_directory', relative_path) )
            _files = []
            for file_path in files:
                _files.append( QDir.toNativeSeparators( relative_path.relativeFilePath(file_path) ) )
            files = _files
        else:
            #Zajęcie się ukośnikami (w zasadzie dotyczy tylko Windows)
            files = [ QDir.toNativeSeparators(f) for f in files ]
        result = self.model.insertRows(files, max_length=parent.field().length())
        if not result:
            #Nie dodano załączników ponieważ przekroczono max długość pola
            field = parent.field()
            parent.widget.bar.pushCritical( 'Błąd',
                f'Nie można dodać załączników, przekroczono maksymalną długość znaków ({field.length()}).')
        return result
    
    def deleteAttachment(self, parent):
        """Usunięcie zaznaczonych załączników"""
        selected = parent.widget.tblAttachments.selectedIndexes()
        if not selected:
            return
        rows = [ index.row() for index in selected ]
        self.model.removeRow(rows[0])
    
    def getAbsoluteFilePath(self, file_path, config):
        """ Zwraca pełną ścieżkę do pliku """
        file_path = QFileInfo( file_path )
        relative_mode = config.get('relative_mode', QgsFileWidget.Absolute)
        #Sprawdzenie czy ścieżka jest relatywna i czy są ustawione odpowiednie opcje
        if file_path.isRelative() and relative_mode != QgsFileWidget.Absolute:
            relative_path = QDir( QgsProject.instance().absolutePath() )
            if relative_mode==QgsFileWidget.RelativeDefaultPath:
                relative_path = QDir( config.get('relative_directory', relative_path) )
            file_path = QFileInfo( QDir(relative_path), file_path.filePath() )
        return file_path

    def openFolder(self, index, editor):
        """ Otworzenie katalogu z plikiem """
        file_path = self.getAbsoluteFilePath( index.data(), editor.config )
        if not file_path.exists():
            #Katalog nie istnieje
            editor.bar.pushCritical( 'Błąd', f"Plik '{file_path.absoluteFilePath()}' nie istnieje." )
            return
        if sys.platform == 'win32':
            #Windows
            subprocess.call(f'explorer /select,"{QDir.toNativeSeparators(file_path.absoluteFilePath())}"', shell=True)
        else:
            #Otworzenie katalogu w systemowym menedżerze plików
            QDesktopServices.openUrl( QUrl(f'file:///{file_path.dir().path()}') )

    def openFile(self, index, editor):
        """ Otworzenie pliku w domyslnej aplikacji """
        file_path = self.getAbsoluteFilePath( index.data(), editor.config )
        if not file_path.exists():
            #Plik nie istenieje
            editor.bar.pushCritical( 'Błąd', f"Plik '{file_path.absoluteFilePath()}' nie istnieje." )
            return
        #Uruchomienie pliku w domyślnej aplikacji
        QDesktopServices.openUrl( QUrl(f'file:///{file_path.absoluteFilePath()}') )
