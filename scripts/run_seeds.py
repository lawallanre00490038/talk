"""Run seeds from the command line.

Usage:
    cd /path/to/lagtalk_backend
    python -m scripts.run_seeds
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from seeds.seed_data import seed_all


if __name__ == "__main__":
    asyncio.run(seed_all())
