import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logiscout_logger import get_logger

logger = get_logger("books")

def books():
    logger.info("Fetching books from database")