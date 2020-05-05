# coding: utf-8

from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtGui import QCursor
from qgis.core import NULL, QgsProject, QgsApplication, Qgis
from qgis_attachments.backends.base.baseBackend import BackendAbstract
from qgis_attachments.backends.files.model import FilesModel
from qgis_attachments.backends.base.baseDelegates import OptionButton
from pathlib import Path
import os
import subprocess
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
        return self.configWidget
    
    def config(self):
        """Zapis ustawień konfiguracji"""
        return {'relative':self.configWidget.cbRelativePaths.isChecked()}

    def setConfig(self, config):
        """Odczyt ustawień i dostosowanie GUI"""
        self.configWidget.cbRelativePaths.setChecked( config.get('relative', False) )
    
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
        else:
            #Zajęcie się ukośnikami (w zasadzie dotyczy tylko Windows)
            files = [ str(Path(f)) for f in files ]
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

    def openFolder(self, index):
        """ Otworzenie katalogu z plikiem """
        file_path = Path(index.data())
        file_dir = file_path.parent
        #Dostęp do widgetu komunikacyjnego jest nieco skomplikowany, ale działa
        bar = QgsApplication.instance().widgetAt(QCursor().pos()).parent().parent().bar
        if not file_dir.exists():
            #Katalog nie istnieje
            bar.pushCritical( 'Błąd', f"Katalog '{file_dir}'' nie istnieje." )
            return
        if sys.platform == 'win32':
            #Windows
            #Konwersja ukośników na backslash
            subprocess.call(f'explorer /select,"{str(file_path)}"', shell=True)
        elif sys.platform.startswith('linux'):
            #Linux
            subprocess.call(['xdg-open', file_dir])
        # TODO: MacOS do przetestowania
        # elif sys.platform == 'darwin':
        #     subprocess.call(['open', '--', file_path])
        else:
            bar.pushCritical( 'Błąd', 'Nie można otworzyć folderu, niewspierany system operacyjny' )

    def openFile(self, index):
        """ Otworzenie pliku w domyslnej aplikacji """
        file_path = Path(index.data())
        #Dostęp do widgetu komunikacyjnego jest nieco skomplikowany, ale działa
        bar = QgsApplication.instance().widgetAt(QCursor().pos()).parent().parent().bar
        if not file_path.exists():
            #Plik nie istenieje
            bar.pushCritical( 'Błąd', f"Plik '{file_path} nie istnieje." )
            return
        if sys.platform == 'win32':
            #Windows
            os.startfile( file_path )
        elif sys.platform.startswith('linux'):
            #Linux
            subprocess.call(['xdg-open', file_path])
        # TODO: MacOS do przetestowania
        # elif sys.platform == 'darwin':
        #     subprocess.call(['open', '--', file_path])
        else:
            bar.pushCritical( 'Błąd', 'Nie można otworzyć pliku, niewspierany system operacyjny' )
