#! /usr/bin/env python
#coding=utf-8

import os
import sys
import select
import MySQLdb
import time
#import svnpkg
import subprocess
import asycommands
import psutil
#import do_scp
import hashlib
import signal
import Logger
from imgconf import *
import configparser

#################################################
###
### config import from conf.py
###
#################################################

#################################################

proc_list = []
asycmd_list = []
Log=None

class MyConfigParser(configparser.ConfigParser):
    def __init__(self, defaults=None):
        configparser.ConfigParser.__init__(self, defaults=defaults)
    def optionxform(self, optionstr):
        return optionstr

def init_log(mission_id):
    global Log
    db = MySQLdb.connect(database_host,database_user,database_pass,database_data)
    mission_id = int(mission_id)
    Log = Logger.Logger(db, mission_id)

def get_now_time():
    timeArray = time.localtime()
    return  time.strftime("%Y-%m-%d %H:%M:%S", timeArray)

def lanch(path, start_script, port, log):
# rules: start_script must put pid in `PID` file: echo $! > PID
# return a tuple(retcode, pid)

    pid = -1
    asycmd = asycommands.TrAsyCommands(timeout=30)
    asycmd_list.append(asycmd)
    child = subprocess.Popen(['/bin/sh', start_script], shell=False, cwd = path, stderr = subprocess.PIPE)
    child.wait()
    if (child.returncode != 0):
        log.append(child.stderr.read())
        return (-1, pid)
    for iotype, line in asycmd.execute_with_data(['/bin/cat', path + "/PID"], shell=False):
        if (iotype == 1 and line != ""):
            try:
                pid = int(line)
            except:
                continue
    if (pid == -1):
        return (-2, pid)
    proc = None
    try:
        proc = psutil.Process(pid)
    except:
        log.append("process %d is not alive" % pid)
        return (-3, pid)
    if (port is -1):
        return (0, pid)
    is_alive = True
    start_time = 0
    proc_list.append(pid)
    while is_alive:
        try:
            conn_list = proc.connections()
        except:
            is_alive = False
            break
        listened = False
        for conn in conn_list:
            if (conn.status == "LISTEN" or conn.status == "NONE") and conn.laddr[1] == port:
                listened = True
                break
        if listened:
            break
        time.sleep(1)
        start_time += 1
    if not is_alive:
        log.append("process start failed")
        proc_list.remove(pid)
        return (-3, pid)
    return (start_time, pid)
#def qps_once(path, qps_result, err_name = "err_qps"):
def deploy_once(path, start_script, port):
    log = []
    log.append(path)
    log.append(start_script)
    log.append(port)
    if (path == ""):
        return 0
    #log_file = path + "/client_application/" + err_name
    asycmd = asycommands.TrAsyCommands(timeout=120)
    asycmd_list.append(asycmd)
    interval_time = 10*60
    # Start Query
    (ret, pid) = lanch(path , start_script, port, log)
    if (ret < 0):
        time.sleep(0.5)
        up_log = ""
        for line in log:
            up_log += "[%s] %s\n" % (get_now_time(), line)
        Log.log("%s\n" % up_log)
        '''
        up_log = ""
        for iotype, line in asycmd.execute_with_data(['/bin/tail', '-50', log_file], shell=False):
            up_log += line + '\n'
        Log.log(up_log.decode('gbk').encode('utf-8'))
        '''
        return -1
    Log.log("[%s] query start ok, use %d s\n" % (get_now_time(), ret))
    # Start OK

    return 0

def Sync_data(online_host,online_path,local_tmp_data_path):

    ####
    #update data
    ####
    Log.log("[%s] Update data\n" % get_now_time())
    rsync_path = online_path
    if (rsync_path[0:1] == "/"):
        rsync_path = rsync_path[1:]
    if (rsync_path[len(rsync_path)-1:] != "/"):
        rsync_path = rsync_path + "/"
    arg2 = local_tmp_data_path
    if (local_tmp_data_path[len(local_tmp_data_path)-1:] != "/"):
        arg2 = local_tmp_data_path + "/"

    arg = "%s::%s" % (online_host, rsync_path)
    stdlog = ""
    errlog = ""
    asycmd = asycommands.TrAsyCommands(timeout=30*60)
    asycmd_list.append(asycmd)
    #for iotype, line in asycmd.execute_with_data(['rsync', '-ravl', arg, arg2], shell=False):
    for iotype, line in asycmd.execute_with_data(['rsync', '-ravl', arg, arg2], shell=False):
        if (iotype is 1):
            stdlog += line + '\n'
            print line
        elif (iotype is 2):
            errlog += line + '\n'
    if (asycmd.return_code() != 0):
        Log.log("[%s] Update data Error\n" % get_now_time())
        Log.log(errlog)
        return 1

    Log.log("[%s] Update data success\n" % get_now_time())
    return 0

#return True:  Sync data success!
#return False: Sync data failed!
def Sync_all(deploy_dic):
    Log.log("[%s] start!\n" % get_now_time())
    for k,v in deploy_dic.items():
        arr=v.split(',')
        if len(arr) >= 3:
            src_host=arr[1]
            src_path=arr[2]
            local_path=arr[0]
            if src_host != '' and src_path != '':
                ret=Sync_data(src_host,src_path,local_path)
                if ret != 0:
                    return False
    return True
def Modify_conf(one):
    config = MyConfigParser()
    #config.read("ini", encoding="utf-8")
    #config.set("db", "db_port", "69")  #修改db_port的值为69
    #config.write(open("ini", "w"))
    file=one[0]
    if not os.path.exists(file):
        raise RuntimeError("no config file:"+file+" exit")
    config.read(file, encoding="utf-8")
    if file.endswith('tf_ocr_daemon/conf/ocr.cfg'):
        config.remove_section('OCR\GPU')
        config.add_section('OCR\GPU')
    t_list=one[1]
    for v in t_list:
        sec=v[0]
        opt=v[1]
        val=v[2]
        config.set(sec, opt, val)
    config.write(open(file, "w"),space_around_delimiters=False)

def Modify_all():
    try:
        for v in CONF_BASE:
            Modify_conf(v)
        for v in CONF_TEST:
            Modify_conf(v)
    except Exception, e:
        Log.log("[%s] modify some config error[%s]\n" % (get_now_time(),e))
        return False
    return True

def Restart_all():
    for v in MOD_BASE:
        #path, restart_script, port
        ret=deploy_once(v[0],v[1],v[2])
        if ret != 0:
            return False
    Log.log("[%s]  base所有模块重启成功!\n" % get_now_time())
    for v in MOD_TEST:
        #path, restart_script, port
        ret=deploy_once(v[0],v[1],v[2])
        if ret != 0:
            return False
    Log.log("[%s]  Test所有模块重启成功!\n" % get_now_time())
    return True
#return 1:  同步数据失败!
#return 2:  配置修改失败!
#return 3:  模块重启失败!
#return 0:  成功
def Deploy_all(deploy_dict,mission_id):
    init_log(mission_id)

    #1.同步测试数据到部署环境
    ans=Sync_all(deploy_dict)
    if not ans:
        Log.log("[%s] 有模块同步数据失败!\n" % get_now_time())
        return 1
    #2.修改各个模块的配置
    ans=Modify_all()
    if not ans:
        Log.log("[%s] 有模块配置修改失败!\n" % get_now_time())
        return 2
    #3.重启各个模块,并进行端口监听是否启动成功
    ans=Restart_all()
    if not ans:
        Log.log("[%s] 有模块重启失败!\n" % get_now_time())
        return 3
    print('env_success')
    return 0


if __name__ == "__main__":
    deploy_dict = sys.argv[1]
    mission_id = int(sys.argv[2])
    ret = Deploy_all(deploy_dict, mission_id)