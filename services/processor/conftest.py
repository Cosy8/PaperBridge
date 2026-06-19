"""Put the service root on sys.path so `import app` resolves when pytest is
invoked from the repo root (CI) or from this directory."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
