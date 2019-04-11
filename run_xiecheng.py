#! /usr/bin/env python
# coding=utf-8

import requests
import base64
import os, sys, json, time, random
from multiprocessing import Pool
import pymysql
from lib import logUtils
import lauch
from Editdistance import *
import aiohttp
import asyncio
import writer
from imgconf1 import *


all=0


# ocr接口：http://10.143.52.35:10098/v4/ocr/json
# 参数：lang，image=base64串
# 英文：en
# 中文：zh-CHS
# 日文：ja
# 韩文：ko
# 俄文：ru
# 法文：fr
# 西班牙文：es
# 德文：de
# 葡萄牙：pt
# 意大利：it
#
# 翻译回帖接口：http://api.image.sogou/v1/open/ocr_translate.json
# 参数：from、to、image、result_type=image

db = pymysql.connect(database_host, database_user, database_pass, database_data)
cursor = db.cursor()

sem = asyncio.Semaphore(3)  # 信号量，控制协程数，防止抓取过快
mission_id = int(sys.argv[1])
url_ocr_test = "http://10.141.177.27:30000/v1/ocr/basic.json"
url_pic_test = "http://10.141.177.27:3111/v1/ocr_translate.json"

url_ocr_base = "http://10.141.177.27:32013/v1/ocr/basic.json"
url_pic_base = "http://10.141.177.27:5124/v1/ocr_translate.json"

def get_now_time():
    timeArray = time.localtime()
    return time.strftime("%Y-%m-%d %H:%M:%S", timeArray)

def update_errorlog(log):
    logstr = logUtils.logutil(mission_id)
    # print(log.replace('\n', ''))
    log = log.replace("'", "\\'")

    sql = "UPDATE %s set errorlog=CONCAT(errorlog, '%s') where id=%d;" % (database_image, log, mission_id)

    cursor.execute(sql)
    data = cursor.fetchone()
    logstr.log_info(str(mission_id) + "\t" + log)
    try:
        db.commit()
    except:
        logstr.log_debug("update_errorlog failed.")
    return data

def set_pid(pid):
    sql = "UPDATE %s set pid='%s' where id=%d" % (database_image, pid, mission_id)
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        update_errorlog("[%s] Insert pid failed. \n" % (get_now_time()))
    return 0

def set_startStatus(status):
    sql = "UPDATE %s set status=%d, start_time='%s' where id=%d" % (database_image, status, get_now_time(), mission_id)
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        update_errorlog("[%s] update task status failed, the status code is [%d]. \n" % (get_now_time(), status))
    return 0

def set_endStatus(status):
    sql = "UPDATE %s set status=%d, end_time='%s' where id=%d" % (database_image, status, get_now_time(), mission_id)
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        update_errorlog("[%s] update task status failed, the status code is [%d]. \n" % (get_now_time(), status))
    return 0

def get_imagetaskinfo():
    sql = "SELECT svIp, langs, env_type, status ,svPath FROM %s where id='%d'" % (database_image, mission_id)
    cursor.execute(sql)
    data = cursor.fetchone()
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        update_errorlog("[%s] Query table imagetaskinfo failed. \n" % (get_now_time()))

    return data

def update_imageTaskInfo(sum_num, finished, failed, img_diff_count, text_diff_count, text_base_count, path):
    sql_image = "UPDATE %s set sum_num='%d',finished='%d',failed = '%d',img_diff_count='%d',text_diff_count = '%d',text_base_count = '%d' ,path='%s' where id=%d" % (
        database_image, sum_num, finished, failed, img_diff_count, text_diff_count, text_base_count, path, mission_id)

    try:
        cursor.execute(sql_image)
        db.commit()
        print('插入成功！')
    except Exception as e:
        pass
    return 0

def insert_resultInfo(rankInfo,result,testImg,basepath,testpath,test_issuccess,base_issuccess,filename):
    sql_result = "INSERT INTO  %s(taskid_id,rankInfo,result,testImg,basepath,testpath,test_status,base_status,filename) values('%d','%d','%s','%s','%s','%s','%d','%d','%s')" % (
                            database_result, mission_id, rankInfo, pymysql.escape_string(result), testImg, basepath,
                            testpath, test_issuccess, base_issuccess, filename)
    try:
        cursor.execute(sql_result)
        db.commit()
    except Exception as e:
        pass
    return 0

def imageTobase64(path):
    with open(path, 'rb') as f:
        image = base64.b64encode(f.read())
        image = image.decode('utf-8')
        return image

def launch_env():
    set_startStatus(2)

    db_data = get_imagetaskinfo()
    svIP = db_data[0]
    langs = db_data[1]
    env_type = db_data[2]
    status = db_data[3]
    svPath = db_data[4]

    remote_path = '/search/odin/test/gongyanli/picEval/'

    parameters = json.loads(svPath)
    for k, v in parameters.items():
        update_errorlog("[%s] send parameters: [%s]---[%s]. \n" % (get_now_time(), k, v))

    # ssh登录，启动环境
    # cmds_base1 = "python " + remote_path + "%s %d" % ('start.py', mission_id)
    # out1, err1 = lauch.startsh(ip, user, pwd, cmds_base1)
    out1 = 'env_success'

    if out1:
        # out1 = out1[-1].strip('\n').strip("'")

        if out1 == 'env_success':
            update_errorlog("[%s] SSH: launch environment successfully. \n" % (get_now_time()))

            for lang in langs.split(','):
                temp = lang.split('_')
                from_langs = temp[0]
                to_langs = temp[1]

                # ssh登录，切换语言
                # cmds_base2 = "python " + remote_path + "%s %s %d" % ('switch_lang.py', from_langs, mission_id)
                # out2, err2 = lauch.startsh(ip, user, pwd, cmds_base2)
                # out2 = out2[-1].strip('\n').strip("'")

                out2 = 'switch_langs'

                if out2 == 'switch_langs':
                    update_errorlog("[%s] Switch Language [%s] successfully. \n" % (get_now_time(), lang))
                    return 1
                else:
                    update_errorlog("[%s] Switch Language [%s] failed. \n" % (get_now_time(), lang))
                    set_endStatus(3)
        else:
            update_errorlog("[%s] SSH: launch environment failed. \n" % (get_now_time()))
            set_endStatus(3)
    else:
        update_errorlog("[%s] SSH: The environment dont return [env_success]. \n" % (get_now_time()))
        set_endStatus(3)

    #return 0

async def get_img(from_langs, to_langs, base64image, isStorePathExists, storePath):
    params_img = {
        'from': from_langs,
        'to': to_langs,
        'image': base64image,
        'result_type': 'text_image'
    }
    base_path=''
    test_path=''

    # resp = requests.post('http://api.image.sogou/v1/open/ocr_translate.json', data=params_img)
    async with aiohttp.ClientSession() as session:
        async with session.request('POST',url_pic_base,data=params_img,timeout=500) as resp_base,session.request('POST',url_pic_test,data=params_img,timeout=800) as resp_test:
            time.sleep(5)
            img_base = await resp_base.json(content_type=None)  # 直接获取到bytes
            img_test = await resp_test.json(content_type=None)  # 直接获取到bytes

            await writer.saveJson(img_base, isStorePathExists + 'base_imgtrans.json')
            await writer.saveJson(img_test, isStorePathExists + 'test_imgtrans.json')

    if img_base['success'] == int(1):
        pic_base = img_base['pic']
        pic_base = base64.b64decode(pic_base)

        base_path = storePath + 'base.jpg'

        await writer.saveImg(pic_base, isStorePathExists + 'base.jpg')

    if img_test['success'] == int(1):
        pic_test = img_test['pic']
        pic_test = base64.b64decode(pic_test)

        test_path = storePath + 'base.jpg'

        await writer.saveImg(pic_test, isStorePathExists + 'test.jpg')

    return base_path,test_path



async def get_html(all,filename, finished, failed, from_langs, to_langs, langs, img_diff_count, text_diff_count,text_base_count):
    start=time.time()
    with(await sem):
        # async with是异步上下文管理器

        isStorePathExists = rootpath + dest_secpath + str(mission_id) + '/' + langs + '/' + filename + '/'
        storePath = dest_secpath + str(mission_id) + '/' + langs + '/' + filename + '/'

        testImg = origin_secpath + from_langs + '/' + filename

        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
        }
        base64image = imageTobase64(rootpath + origin_secpath + from_langs + '/' + filename)
        params_ocr = {
            'lang': from_langs,
            'image': base64image,
            'direction_detect': 'true'
        }

        if not os.path.exists(isStorePathExists):
            os.makedirs(isStorePathExists)

        async with aiohttp.ClientSession() as session:  # 获取session

            # resp_test = requests.post(url_ocr_test, data=params_ocr, headers=headers)
            # resp_base = requests.post(url_ocr_base, data=params_ocr, headers=headers)

            async with session.request('POST', url_ocr_base, data=params_ocr,
                                       headers=headers,timeout=500) as resp_base, session.request('POST', url_ocr_test,
                                                                                      data=params_ocr,
                                                                                      headers=headers,timeout=800) as resp_test:  # 提出请求

                time.sleep(5)
                ocr_base = await resp_base.json(content_type=None)  # 直接获取到bytes
                ocr_test = await resp_test.json(content_type=None)  # 直接获取到bytes
                # htmls.append(html)
                await writer.saveJson(ocr_base, isStorePathExists + 'base_ocr.json')
                await writer.saveJson(ocr_test, isStorePathExists + 'test_ocr.json')
                # print('异步获取%s下的html.' % url)

            test_issuccess = ocr_base['success']
            base_issuccess = ocr_test['success']

            if (test_issuccess == int(1) & base_issuccess == int(1)):
                all=all+1
                print('all',all)
                finished += 1

                distance_data = json.loads(ReturnRes(ocr_test, ocr_base))

                if distance_data['img_diff_count'] != int(0):
                    img_diff_count += 1

                text_diff_count += distance_data['text_diff_count']
                text_base_count += distance_data['text_base_count']

                rankInfo = distance_data['sum_distance']
                result = json.dumps(distance_data['result'])

                basepath,testpath=await get_img(from_langs, to_langs, base64image, isStorePathExists, storePath)

                insert_resultInfo(rankInfo, result, testImg, basepath, testpath, test_issuccess,base_issuccess, filename)

            else:
                failed += 1

                insert_resultInfo(rankInfo=0, result='null', testImg=testImg, basepath='null', testpath='null', test_issuccess=0,base_issuccess=0, filename=filename)

            end=time.time()
            print('end-start:',end-start)

            update_errorlog("[%s] Time: [%s] \n" % (get_now_time(), end-start))
            return finished, failed, img_diff_count, text_base_count, text_diff_count


'''
协程调用方，请求网页
'''

async def main_get_html():
    global all

    sum_num = 0

    failed=0
    finished=0
    img_diff_count=0
    text_diff_count=0
    text_base_count=0

    db_data = get_imagetaskinfo()
    svIP = db_data[0]
    langs = db_data[1]
    env_type = db_data[2]
    status = db_data[3]
    svPath = db_data[4]

    remote_path = '/search/odin/test/gongyanli/picEval/'

    lang = langs.split('_')
    from_langs = lang[0]
    to_langs = lang[1]

    sum_num += len(os.listdir(rootpath + origin_secpath + from_langs + '/'))
    path = rootpath + dest_secpath + str(mission_id)

    # loop = asyncio.get_event_loop()           # 获取事件循环

    tasks = [get_html(all,filename, finished, failed, from_langs, to_langs, langs, img_diff_count, text_diff_count,
                      text_base_count) for filename in
             os.listdir(rootpath + origin_secpath + from_langs + '/')]  # 把所有任务放到一个列表中
    # loop.run_until_complete(asyncio.wait(tasks)) # 激活协程
    # loop.close()  # 关闭事件循环
    results = []
    for next_to_complete in asyncio.as_completed(tasks):
        answer = await  next_to_complete
        finished = finished + answer[0]
        failed = failed + answer[1]
        img_diff_count = img_diff_count + answer[2]
        text_diff_count = text_diff_count + answer[2]
        text_base_count = text_base_count + answer[2]

        if (finished % 10) == 1:
            print('finish',finished)
            update_imageTaskInfo(sum_num, finished, failed, img_diff_count, text_diff_count, text_base_count, path)

    update_imageTaskInfo(sum_num, finished, failed, img_diff_count, text_diff_count, text_base_count, path)
    print('final and failed:',finished,failed)

    if sum_num==(finished+failed):
        set_endStatus(4)
        update_errorlog("[%s] Env deploy: The post [%s] has been completed. \n" % (get_now_time(), lang))

    # print('aa {}'.format(answer))
    # results.append(answer)

    # print('fin', finished)
    # print('bb {}'.format(results))
    return results


def get():
    coroutine = main_get_html()
    # task=asyncio.ensure_future(coroutine)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(coroutine)
    loop.close()


if __name__ == '__main__':

    start_time = time.time()
    pid = os.getpid()
    set_pid(pid)
    # post_ocr()
    isLaunch = launch_env()
    print(type(isLaunch))
    if isLaunch == int(1):
        get()
    else:
        sys.exit()

    end_time = time.time()
    update_errorlog("[%s] Time [%s]. \n" % (get_now_time(),end_time-start_time))

