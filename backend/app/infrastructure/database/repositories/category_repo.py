"""Compatibility facade for category repository helpers.

Category data access is split by subdomain under ``repositories.category``.
Existing services can keep importing ``category_repo`` unchanged.
"""

from .category.audit_redirects import *
from .category.crud import *
from .category.identifier_policy import *
from .category.metrics import *
from .category.tree import *
