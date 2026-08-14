"""Replaceable source adapters for fund data."""

from app.crawlers.base import BaseCrawler
from app.crawlers.fipiran import FipiranCrawler
from app.crawlers.parser import DataParser

__all__ = ["BaseCrawler", "DataParser", "FipiranCrawler"]
