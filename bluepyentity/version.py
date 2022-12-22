"""version"""
from pkg_resources import get_distribution

VERSION = get_distribution("bluepyentity").version
__version__ = VERSION
