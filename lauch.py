#! /usr/bin/env python
# coding=utf-8

import paramiko
from lib import logUtils
import sys,time


def get_now_time():
    timeArray = time.localtime()
    return time.strftime("%Y-%m-%d %H:%M:%S", timeArray)


def update_errorlog(log):
    print(log)
    # logstr = logUtils.logutil(mission_id)
    # # print(log.replace('\n', ''))
    # log = log.replace("'", "\\'")
    #
    # sql = "UPDATE %s set errorlog=CONCAT(errorlog, '%s') where id=%d;" % (database_image, log, mission_id)
    #
    # cursor.execute(sql)
    # data = cursor.fetchone()
    # logstr.log_info(str(mission_id) + "\t" + log)
    # try:
    #     db.commit()
    #     print 'insert success'
    # except:
    #     logstr.log_debug("error")
    # return data


def startsh(remote_host, remote_user, remote_pwd, cmds):
    """启动脚本"""
    stderr = ''
    try:
        update_errorlog("[%s] Start script \n" % get_now_time())
        # 创建ssh客户端
        client = paramiko.SSHClient()
        # 第一次ssh远程时会提示输入yes或者no
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # 密码方式远程连接
        client.connect(remote_host, 22, username=remote_user, password=remote_pwd, timeout=20)
        # 互信方式远程连接
        # key_file = paramiko.RSAKey.from_private_key_file("/root/.ssh/id_rsa")
        # ssh.connect(sys_ip, 22, username=username, pkey=key_file, timeout=20)
        # 执行命令
        stdin, stdout, stderr = client.exec_command(cmds, timeout=3600)
        # 获取命令执行结果,返回的数据是一个list
        out = stdout.readlines()
        err = stderr.readlines()

        return out,err
    except Exception as e:
        print(e)
        update_errorlog("[%s] Start script error ,error info:%s \n" % (get_now_time(), stderr.readlines()))
        sys.exit()
    finally:
        client.close()


if __name__ == '__main__':
    ip = "10.138.10.70"
    user = "root"
    pwd = 'sogourank@2016'
    remote_path = '/search/odin/daemon/gongyl/'
    script = 'a.py'

    cmds_test = "python " + remote_path + "%s" % (script)
    print(cmds_test)
    test_result = startsh(ip, user, pwd, cmds_test)

