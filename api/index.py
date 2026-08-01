import os
import sys

# Ensure root directory and backend directory are in sys.path for Vercel Serverless Function
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.main import app
