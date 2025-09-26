# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

# docs/conf.py
import os, sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(".."))

os.environ.setdefault("SPHINX_BUILD", "1")

root_doc = "index"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

autodoc_mock_imports = [
    "sqlalchemy",
    "alembic",
    "fastapi",
    "uvicorn",
    "pydantic",
    "redis",
    "jose",
    "passlib",
    "fastapi_mail",
    "dotenv",
    "cloudinary",
    "email_validator",
    "src.cloudinary_service",
    "src.cache.redis_client",
    "src.emailer",
    "src.conf.config",
]

autodoc_typehints = "description"

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

html_static_path = []
