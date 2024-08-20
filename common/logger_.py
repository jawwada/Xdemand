import logging
import os

def get_logger():
    # Create a logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)  # set logger level

    # Create a file handler and set level to debug
    # create directory and file if not exist
    if not os.path.exists('logging_logs'):
        os.makedirs('logging_logs')
    # create file
    open('logging_logs/test_model.log', 'a').close()

    file_handler = logging.FileHandler('logging_logs/test_model.log')
    file_handler.setLevel(logging.DEBUG)

    # Create a console handler and set level to debug
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = get_logger()