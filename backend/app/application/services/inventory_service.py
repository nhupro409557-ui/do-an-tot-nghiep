"""Compatibility facade for inventory application service helpers.

Inventory service logic is split by subdomain under ``services.inventory``.
Existing routers and services can keep importing ``inventory_service`` while
new code can work in the smaller modules directly.
"""

from .inventory.common import *
from .inventory.documents import *
from .inventory.identifiers import *
from .inventory.outbounds import *
from .inventory.overview import *
from .inventory.receipts import *
