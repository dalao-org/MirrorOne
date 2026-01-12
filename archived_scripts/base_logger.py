import logging

logger = logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s -> %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S')
