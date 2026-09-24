"""Shared Altitude core package initialization."""

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # Allows dependency-light static/unit checks.
    load_dotenv = None


# Load local configuration before any core submodule reads environment values.
if load_dotenv is not None:
    load_dotenv()
