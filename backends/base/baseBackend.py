# coding: utf-8

from qgis.PyQt.QtCore import QObject
from qgis.core import NULL
from qgis.gui import QgsAttributeEditorContext
from qgis_attachments.backends.base.baseDelegates import OptionButtonsDelegate

class BackendAbstract(QObject):
    """ Klasa bazowa dla różnych typów sterowników dla załączników """

    SEPARATOR = ';'
    DESCRIPTION = ''

    def __init__(self, options=[], options_column=0, parent=None):
        super(BackendAbstract, self).__init__(parent)
        #Lista opcji dla załącznika
        self.options = options
        #W której kolumnie mają znaleźć się opcje
        self.options_column = options_column
        self.parent = parent

    # KONFIGURACJA

    def createConfigWidget(self):
        return

    def config(self):
        return {}
    
    def setConfig(self, config):
        pass

    @staticmethod
    def isSupported(layer):
        """ Sprawdza czy dana warstwa jest wspierana przez sterownik """
        return True

    def warnings(self, layer, fieldIdx):
        return []

    # FORMULARZ

    def value(self):
        """Konwersja danych z modelu do tekstu"""
        #Serializacja danych do tekstu
        value = self.model.serialize()
        if not value:
            #Brak załączników
            return NULL
        return value

    def setValue(self, value):
        """Parsowanie tekstu do listy załączników"""
        #Wyczyszczenie listy załączników
        self.model.clear()
        if value == NULL:
            return
        values = value.split( self.SEPARATOR )
        #Wypełnienie lisy załączników
        self.model.insertRows(values)
    
    def setOptions(self):
        """ Ustawienie dodatkowych opcji dla załączników w podanej kolumnie """
        if self.options:
            table = self.parent.widget.tblAttachments
            buttons = OptionButtonsDelegate(self.options)
            table.setItemDelegateForColumn(self.options_column, buttons)
            column_width = buttons.columnWidth()
            table.setColumnWidth(self.options_column, column_width)
            table.horizontalHeader().setMinimumSectionSize( column_width )
    
    def getFeature(self):
        """ Zwraca edytowany obiekt przestrzenny """
        if self.parent.context().formMode()==QgsAttributeEditorContext.Popup:
            return self.parent.context().formFeature()
        return self.parent.formFeature()
