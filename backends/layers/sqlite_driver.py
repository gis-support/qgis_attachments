# coding: utf-8

from contextlib import contextmanager
import sqlite3
import os

class SQLiteDriver:

    """ Komunikacja z bazą SQLITE """

    @staticmethod
    @contextmanager
    def connection(geopackage_path):
        """ Połączenie z bazą sqlite """
        con = sqlite3.connect(geopackage_path)
        # Dodanie tabeli na załączniki, jeśli nie istnieje
        sql = """CREATE TABLE IF NOT EXISTS qgis_attachments (
                id INTEGER PRIMARY KEY,
                name TEXT,
                data BLOB
            )"""
        con.execute(sql)
        yield con
        con.close()
    
    @classmethod
    def fetchAttachment(cls, db_path, row_id):
        """ Pobranie pojedynczego załącznika """
        with cls.connection(db_path) as connection:
            if row_id == '-1':
                file_name, file_data = None, None
            else:
                sql = """SELECT name, data FROM qgis_attachments WHERE id = {}"""
                file_name, file_data = connection.execute(sql.format(row_id)).fetchone()
        return file_name, file_data
    
    @classmethod
    def fetchAttachments(cls, db_path, row_ids, with_ids=True):
        """ Pobranie listy załączników """
        sql = """SELECT name FROM qgis_attachments WHERE id = {}"""
        values_filenames = []
        with cls.connection(db_path) as connection:
            for row_id in row_ids:
                try:
                    query_output = connection.execute(sql.format(row_id)).fetchone()
                    if query_output is None:
                        query_output = connection.execute(sql.format(row_id)).fetchone()
                    elif len(query_output) > 0:
                        if with_ids:
                            values_filenames.append([row_id, query_output[0]])
                        else:
                            values_filenames.append(query_output[0])
                except sqlite3.OperationalError:
                    #anulowanie wyboru załącznika, value jest puste
                    continue
        return values_filenames
    
    @classmethod
    def insertAttachments(cls, db_path, files_list):
        """Zapisuje załączniki i zwraca listę id"""
        with cls.connection(db_path) as connection:
            sql = """INSERT INTO qgis_attachments (name, data) VALUES (?, ?)"""
            cursor = connection.cursor()
            ids = []
            for file in files_list:
                with open(file, 'rb') as f:
                    name = os.path.basename(file)
                    blob = f.read()
                    cursor.execute(sql, (name, sqlite3.Binary(blob)))
                    attachment_id = str(cursor.lastrowid)
                    ids.append(attachment_id)
            connection.commit()
            cursor.close()
        return ids
    
    @classmethod
    def deleteAttachments(cls, db_path, row_ids):
        """ Usunięcie załączników """
        with cls.connection(db_path) as connection:
            sql = """DELETE FROM qgis_attachments where id IN ({})""".format(','.join(row_ids))
            connection.execute(sql)
            connection.commit()