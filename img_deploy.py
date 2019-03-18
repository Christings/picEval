#! /usr/bin/env python
#coding=utf-8

import os
import sys
import select
import MySQLdb
import time,json
#import svnpkg
import subprocess
import asycommands
import psutil
#import do_scp
import hashlib
import signal
import Logger
from imgconf import *
from backports import configparser
import pymysql

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

def get_imagetaskinfo(mission_id):
    db = pymysql.connect(database_host, database_user, database_pass, database_data)
    cursor = db.cursor()

    sql = "SELECT svPath FROM %s where id='%d'" % ('picEval_imagetaskinfo', mission_id)

    cursor.execute(sql)
    data = cursor.fetchone()
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        print('查询image数据库失败！')
    return data


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
    Log.log("[%s]  Base: all modules restart successfully.\n" % get_now_time())
    for v in MOD_TEST:
        #path, restart_script, port
        ret=deploy_once(v[0],v[1],v[2])
        if ret != 0:
            return False
    Log.log("[%s]  Test: all modules restart successfully.\n" % get_now_time())
    return True
#return 1:  同步数据失败!
#return 2:  配置修改失败!
#return 3:  模块重启失败!
#return 0:  成功
def Deploy_all(mission_id):
    #mission_id=mission_id.replace('\n','')

    init_log(mission_id)

    data=get_imagetaskinfo(mission_id)
    deploy_dict=json.loads(data[0])

    #1.同步测试数据到部署环境
    ans=Sync_all(deploy_dict)
    if not ans:
        Log.log("[%s] There is a module which synchronize data failed.\n" % get_now_time())
        return 1
    #2.修改各个模块的配置
    ans=Modify_all()
    if not ans:
        Log.log("[%s] There is a module which change configuration failed.\n" % get_now_time())
        return 2
    #3.重启各个模块,并进行端口监听是否启动成功
    ans=Restart_all()
    if not ans:
        Log.log("[%s] There is a module which restart failed.\n" % get_now_time())
        return 3
    print('env_success')
    return 0
#return 1:  base语言切换失败!
#return 2:  test语言切换失败!
#return 0:  语言切换成功
def Switch_lang(from_lang,mission_id):
    init_log(mission_id)
    '''开始base环境的语言切换'''
    l_conf_b=lang_conf_b[from_lang]
    l_data_b=lang_data_b[from_lang]
    b_conf='/search/odin/test/offline/tf_ocr_daemon/conf'
    b_data='/search/odin/test/offline/tf_ocr_daemon/data'
    os.popen("rm -f %s %s" % (b_conf, b_data)) #删除软链
    os.popen("ln -s %s %s" % (l_conf_b, b_conf))#软链conf
    os.popen("ln -s %s %s" % (l_data_b, b_data))#软链data
    #改base新语言的配置
    conf=("/search/odin/test/offline/tf_ocr_daemon/conf/ocr.cfg",[('OCR\Network','"ListenAddress"','":4101"'),('OCR\GPU','DeviceCount','#2'),('OCR\GPU','GPU01','#6'),('OCR\GPU','GPU02','#6'),('OCR\Task','RecogTask_ThreadCount','#2')])
    Modify_conf(conf)
    #重启base新语言
    v=('/search/odin/test/offline/tf_ocr_daemon','restart_tf_ocr_daemon.sh',4101)
    ret=deploy_once(v[0],v[1],v[2])
    if ret != 0:
        Log.log("[%s] base language %s switch failed.\n" % (get_now_time(),from_lang))
        return 1
    Log.log("[%s] base language %s switch successfully.\n" % (get_now_time(),from_lang))

    '''开始test环境的语言切换'''
    l_conf_t=lang_conf_t[from_lang]
    l_data_t=lang_data_t[from_lang]
    t_conf='/search/odin/test/offline_t/tf_ocr_daemon/conf'
    t_data='/search/odin/test/offline_t/tf_ocr_daemon/data'
    os.popen("rm -f %s %s" % (t_conf, t_data))
    os.popen("ln -s %s %s" % (l_conf_t, t_conf))
    os.popen("ln -s %s %s" % (l_data_t, t_data))
    #改test新语言的配置
    conf=("/search/odin/test/offline_t/tf_ocr_daemon/conf/ocr.cfg",[('OCR\Network','"ListenAddress"','":6114"'),('OCR\GPU','DeviceCount','#2'),('OCR\GPU','GPU01','#6'),('OCR\GPU','GPU02','#6'),('OCR\Task','RecogTask_ThreadCount','#2')])
    Modify_conf(conf)
    #重启test新语言
    v=('/search/odin/test/offline_t/tf_ocr_daemon','restart_tf_ocr_daemon.sh',6114)
    ret=deploy_once(v[0],v[1],v[2])
    if ret != 0:
        Log.log("[%s] test language %s switch failed.\n" % (get_now_time(),from_lang))
        return 2
    Log.log("[%s]  test language %s switch successfully.\n" % (get_now_time(),from_lang))

    print('switch_langs')
    return 0   #切换语言成功

#示例调用如下：
# if __name__ == '__main__':
#     '''
#     src_host = "rsync.query001.web.djt.ted"
#     src_path = "odin/search/odin/daemon/norm_lquery01"
#     local_path = "/search/data2/tmp_data/"
#     Sync_data(src_host,src_path,local_path)
#     '''
#     #初始化10号任务的log
#     init_log(72)
#     deploy_dict={"deploy1":"/search/odin/test/testenv,10.141.177.27,/search/odin/test/offline/tf_ocr_daemon,"}
#     ret=Deploy_all(deploy_dict)
#     if ret != 0:
#         print("deploy_fail")
#         sys.exit(1)
#     #切换到特定的语种
#     #for from_lang in from_langs:
#     from_lang='en'
#     ret=Switch_lang(from_lang)
#     if ret !=0:
#         print("switch_fail")
#         sys.exit(2)
#     #打2000个图片请求后...再次循环执行下个语言
#
#     print("env_success")
#     sys.exit(0)


