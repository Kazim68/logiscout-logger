import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logiscout_logger import init, get_logger
from custom import books


logger = get_logger("billing")

logger.info("Payment started")
logger.debug("debugging log")

books()
