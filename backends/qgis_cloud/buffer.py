# coding: utf-8
from qgis_attachments.backends.qgis_cloud.cloud_driver import CloudDriver
from qgis.PyQt.QtCore import QObject
from qgis.core import NULL, QgsProject, QgsFeatureRequest, QgsMapLayer, QgsMapLayerType
import os
from collections import defaultdict
from itertools import chain

def nested_dict(func):
    return defaultdict( func )

dict_add = nested_dict(lambda: defaultdict(list) )
dict_delete = nested_dict(lambda: defaultdict(list) )

class CloudBuffer(QObject):

    #Struktura klucz słowników: warstwa -> pole -> obiekt -> dane
    added = defaultdict( lambda:dict_add )
    deleted = defaultdict( lambda: dict_delete )

    def __init__(self, separator):
        super(CloudBuffer, self).__init__()
        self.SEPARATOR = separator
        self.config = {}
        QgsProject.instance().layerWasAdded[QgsMapLayer].connect(self.registerLayer)

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
        #Sprawdzamy czy warstwa ma pola obsługiuwane przez sterownik
        if layer.type() == QgsMapLayerType.VectorLayer:
            for index, _ in enumerate(layer.fields()):
                if self.supportedField(layer, index):
                    break
            else:
                # Brak zarejestrowanego pola dla cloud
                return
            layer.beforeCommitChanges.connect(self.beforeCommitChanges)
            layer.afterRollBack.connect( self.afterRollBack )
            layer.featureAdded.connect( self.featureAdded )
            layer.featureDeleted.connect( self.featureDeleted )

    def supportedField(self, layer, index):
        widget_setup = layer.editorWidgetSetup(index)
        return widget_setup.config().get('backend')=='cloud'

    # Sygnały warstw

    def featureAdded(self, fid):
        """ Dodanie nowego obiektu """
        #Ta metoda jest wywoływana zarówno po dodaniu obiektu do warstwy jak i w momencie zapisu
        #Nas interesuje pierwszy przypadek, kiedy ID obiektów jest ujemne
        if fid>0:
            return
        try:
            layer = self.sender()
            feature = layer.editBuffer().addedFeatures()[fid]
            added = self.added[layer.id()]
            for field_id in added:
                #Nowo utworzony obiekt ma ID 0, musimy je zamienić na docelowe ID obiektu (np. -1)
                data = added[field_id].pop(0, None)
                if data is None:
                    continue
                added[field_id][feature.id()] = data
        except KeyError:
            pass

    def beforeCommitChanges(self):
        """ Zapis załączników """
        layer = self.sender()
        to_add_fields = self.added[layer.id()]
        to_delete_fields = self.deleted[layer.id()]
        fields = set(to_add_fields.keys())
        fields.update( to_delete_fields.keys() )
        deleted = []
        token = self.backend.getApiToken(data=self.config)
        for field_id in fields:
            to_delete = to_delete_fields[field_id]
            to_add = to_add_fields[field_id]
            for fid, feature in self.getFeatures(layer, field_id).items():
                #Dodawane załączniki
                try:
                    added = to_add.pop(fid)
                except:
                    continue
                files = [ f[1] for f in added ]
                uploaded = CloudDriver.uploadAttachments(self.config['api_url'], token, files)
                files_indexes = [ str(fid) for fid in uploaded ]
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
            if to_delete and not deleted:
                #Jeśli usuwany jest obiekt warstwy
                for indexes in to_delete.values():
                    deleted.extend(indexes)
            #Czyszczenie ewentualnych pozostałości w buforze
            self.clearLayer( layer.id(), field_id )
        #Przeładowanie danych warstwy
        layer.reload()
        if not deleted:
            return
        #Skasowanie usuniętych załączników z bazy
        CloudDriver.deleteAttachments(self.config['api_url'], token, list(set(deleted)))

    def afterRollBack(self):
        """ Koniec edycji bez zapisanych zmian """
        layer = self.sender()
        self.clearLayer( layer.id() )
        layer.reload()

    def featureDeleted(self, fid):
        """ Usuwanie załączników po usunięciu obiektu warstwy """
        if fid > 0:
            layer = self.sender()
            deleted = self.deleted[layer.id()]
            for feature in layer.dataProvider().getFeatures(QgsFeatureRequest().setFilterFid(fid)):
                for index, _ in enumerate(feature.fields()):
                    if self.supportedField(layer, index):
                        value = feature.attribute(index)
                        if value is NULL:
                            continue
                        attachments = feature.attribute(index).split(self.SEPARATOR)
                        deleted[index][fid].extend(attachments)
