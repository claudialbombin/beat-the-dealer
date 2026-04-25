"""
Pytest configuration for the Blackjack Monte Carlo Solver tests.
Adds the src directory to the Python path so test modules can import
from the source files directly.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
