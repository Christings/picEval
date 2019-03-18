# -*-coding:utf-8-*-
import logging
from datetime import datetime


class logutil():
    fname = ''

    def __init__(self, id):
        self.fname = datetime.now().strftime('%m%d%H%M%S') + '-' + str(id)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s : %(levelname)s  %(message)s',
            datefmt='%Y-%m-%d %A %H:%M:%S',
            filename='log/log-' + self.fname,
            filemode='a')

    def log_info(self, loginfo):
        logging.info(loginfo)

    def log_debug(self, loginfo):
        logging.debug(loginfo)

    def log_warning(self, loginfo):
        logging.warning(loginfo)

    def log_error(self, loginfo):
        logging.error(loginfo)

    def log_critical(self, loginfo):
        logging.critical(loginfo)


if __name__ == "__main__":
    #    console_out('logging.log')
    log_input = logutil()
    log_input.log_info('aaaaaaaaaa')
