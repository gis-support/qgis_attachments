import os

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