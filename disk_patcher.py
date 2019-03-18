#! /usr/bin/env python
# coding=utf-8

# import MySQLdb
import time
import pymysql
from lib import logUtils

# status：任务的状态（0:未开始；1:已分配；2正在运行；3:出错停止；4:已完成；5:任务取消；6:准备取消；7:端口评测的状态）

# database_host = "127.0.0.1"
database_host = "10.141.21.129"
database_data = "evalplatform"
database_table = "picEval_imagetaskinfo"
database_user = "root"
database_pass = "noSafeNoWork@2019"

server_nodes = ['10.141.21.129']


def check_new_task(cursor):
    cursor.execute("SELECT id FROM {_table} where status=0 ORDER BY start_time limit 1".format(_table=database_table))
    data = cursor.fetchone()
    if data == None:
        return -1
    return data[0]


def get_node(cursor):
    # cursor.execute("select runningIP from {_table} where status=2 or status=1".format(_table=database_table))
    cursor.execute("select svIP from {_table} where status=2 or status=1".format(_table=database_table))
    data = cursor.fetchall()
    used_ip = []
    for ip in data:
        used_ip.append(ip[0])
    for node in server_nodes:
        if node not in used_ip:
            return node
    return ""


def do_mission(mission_id, ip, db):
    cursor = db.cursor()
    # sql = "UPDATE {_table} set runningIP='{_ip}', status=1 where id={_mission_id}".format(_table=database_table, _ip=ip,
    sql = "UPDATE {_table} set svIP='{_ip}', status=1 where id={_mission_id}".format(_table=database_table, _ip=ip,
                                                                                          _mission_id=mission_id)
    try:
        cursor.execute(sql)
        db.commit()
    except:
        db.rollback()
        return 1
    return 0


def main():
    log_info = logUtils.logutil('qo')
    while True:
        db = pymysql.connect(database_host, database_user, database_pass, database_data)
        cursor = db.cursor()
        mission_id = check_new_task(cursor)
        if mission_id is -1:
            time.sleep(1)
            log_info.log_info('There is no task')
            continue
        ip = get_node(cursor)
        print(ip)
        log_info.log_info('getnodeip' + ip)
        if ip is "":
            time.sleep(30)
            log_info.log_info("new task %d, but all servers are busy" % mission_id)
            continue
        log_info.log_info("task %d will run on %s" % (mission_id, ip))
        ret = do_mission(mission_id, ip, db)
        log_info.log_info("return:%d" % ret)


# db = MySQLdb.connect(database_host,database_user,database_pass,database_data)
# cursor = db.cursor()
# cursor.execute("SELECT runningIP FROM AutoQPS where status=0 ORDER BY create_time")
# data = cursor.fetchall()
# print data

if __name__ == '__main__':
    main()
