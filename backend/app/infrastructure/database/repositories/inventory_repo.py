"""Compatibility facade for inventory repository helpers.

The implementation is split by inventory subdomain under
``repositories.inventory``. Keep importing this module from services/routers
so existing callers do not need to change while the repository remains
maintainable.
"""

from .inventory.documents import *
from .inventory.identifiers import *
from .inventory.locations import *
from .inventory.outbounds import *
from .inventory.overview import *
from .inventory.receipts import *
from .inventory.stock_mutations import *
