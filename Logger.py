#! /usr/bin/env python
import MySQLdb

class Logger:
    def __init__(self, db, mission_id):
        self.db = db
        self.cursor = db.cursor()
        self.mission_id = mission_id

    def log(self, log):
        # print log.replace('\n', '')
        log = log.replace("'", "\\'")
        sql = "UPDATE picEval_imagetaskinfo set errorlog=CONCAT(errorlog, '%s') where id=%d;" % (log, self.mission_id)
        self.cursor.execute(sql)
        data = self.cursor.fetchone()
        try:
            self.db.commit()
        except:
            print "error"
        return data