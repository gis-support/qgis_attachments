# coding: utf-8

from qgis.core import NULL

class BackendAbstract:
    """ Klasa bazowa dla różnych typów sterowników dla załączników """

    SEPARATOR = ';'
    DESCRIPTION = ''

    # KONFIGURACJA

    def config(self):
        return {}
    
    def setConfig(self, config):
        pass

    # FORMULARZ

    def value(self):
        """Konwersja danych z modelu do tekstu"""
        #Serializacja danych do tekstu
        value = self.model.serialize( self.SEPARATOR )
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