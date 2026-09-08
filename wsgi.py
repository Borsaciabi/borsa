import sys
import os

# PythonAnywhere WSGI Yapılandırması
# Bu dosya PythonAnywhere dashboard > Web > WSGI configuration file olarak ayarlanır

project_home = '/home/hayatadair/borsa'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Çalışma dizinini ayarla
os.chdir(project_home)

# Ortam değişkenlerini ayarla
os.environ.setdefault('PYTHONPATH', project_home)

from app import app as application
