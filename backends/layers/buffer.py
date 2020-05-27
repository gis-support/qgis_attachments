# coding: utf-8

from qgis_attachments.backends.layers.sqlite_driver import SQLiteDriver
from qgis.PyQt.QtCore import QObject
from qgis.core import NULL, QgsProject
import os
from collections import defaultdict
from itertools import chain

def nested_dict(func):
    return defaultdict( func )
dict_add = nested_dict(lambda: defaultdict(list) )
dict_delete = nested_dict(lambda: defaultdict(list) )

class AttachmentsBuffer(QObject):
    
    #Struktura klucz słowników: warstwa -> pole -> obiekt -> dane
    added = defaultdict( lambda:dict_add )
    deleted = defaultdict( lambda: dict_delete )
    registered_layers = set()

    def __init__(self, separator):
        super(AttachmentsBuffer, self).__init__()
        QgsProject.instance().layerRemoved.connect(self.clearLayer)
        self.SEPARATOR = separator

    def getFeatures(self, layer, field_id):
        """ Zwraca obiekty przestrzenne danej warstwy, które zostały zmodyfikowane """
        added = self.added.get( layer.id(), {} ).get( field_id, {} )
        deleted = self.deleted.get( layer.id(), {} ).get( field_id, {} )
        fids = set( chain(added.keys(), deleted.keys()))
        return { f.id():f for f in layer.getFeatures(list(fids)) }
    
    def clearLayer(self, layer_id, field_id=None):
        """ Czyszczenie bufora dla warstwy i pola """
        if field_id is None:
            self.added[layer_id].clear()
            self.deleted[layer_id].clear()
        else:
            self.added[layer_id][field_id].clear()
            self.deleted[layer_id][field_id].clear()
    
    def registerLayer(self, layer):
        """ Zarejestrowanie warstwy """
        if layer.id() not in self.registered_layers:
            self.registered_layers.add(layer.id())
            layer.beforeCommitChanges.connect(self.beforeCommitChanges)
            layer.afterRollBack.connect( self.afterRollBack )
    
    # Sygnały warstw

    def beforeCommitChanges(self):
        """ Zapis załączników """
        layer = self.sender()
        gpkg_path = layer.dataProvider().dataSourceUri().split('|')[0]
        # field_id = self.parent.fieldIdx()
        # print( json.dumps(buffer.added))
        to_add_fields = self.added[layer.id()]#[field_id]
        to_delete_fields = self.deleted[layer.id()]#[field_id]
        deleted = []
        for field_id, to_add in to_add_fields.items():
            to_delete = to_delete_fields[field_id]
            for fid, feature in self.getFeatures(layer, field_id).items():
                #Dodawane załączniki
                added = to_add.pop(fid)
                files = [ f[1] for f in added ]
                files_indexes = [ str(fid) for fid in SQLiteDriver.insertAttachments(gpkg_path, files) ]
                
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
            self.clearLayer( layer.id(), field_id )
        #Przeładowanie danych warstwy
        layer.reload()

        if not deleted:
            return
        #Skasowanie usuniętych załączników z bazy
        SQLiteDriver.deleteAttachments( gpkg_path, deleted )
    
    def afterRollBack(self):
        """ Koniec edycji bez zapisanych zmian """
        layer = self.sender()
        self.clearLayer( layer.id() )
        layer.reload()