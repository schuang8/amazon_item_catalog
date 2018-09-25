import sys

sys.path.insert(0, '/var/www/html/amazon_item_catalog/')

from project import app as application


application.debug=True
