"""Shared Altitude core package initialization."""

from dotenv import load_dotenv


# Load local configuration before any core submodule reads environment values.
load_dotenv()
