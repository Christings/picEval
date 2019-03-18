#! /usr/bin/env python
# coding=utf-8

import requests
import base64
import os, sys, json,time
import pymysql
from lib import logUtils
import lauch
from imgconf1 import *
from Editdistance import *

# from picEval.models import ImageTaskInfo, ResultInfo


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


def set_status(status):
    sql = "UPDATE %s set status=%d, end_time='%s' where id=%d" % (database_image, status, get_now_time(), mission_id)
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        update_errorlog("[%s] update task status failed, the status code is [%d]. \n" % (get_now_time(), status))
    return 0


def get_imagetaskinfo():
    sql = "SELECT svIp, langs, env_type, status FROM %s where id='%d'" % (database_image, mission_id)
    cursor.execute(sql)
    data = cursor.fetchone()
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        update_errorlog("[%s] Query table imagetaskinfo failed. \n" % (get_now_time()))

    return data


def imageTobase64(path):
    with open(path, 'rb') as f:
        image = base64.b64encode(f.read())
        image = image.decode('utf-8')
        return image


def post_ocr():
    headers = {
        'Content-Type': "application/x-www-form-urlencoded",
    }

    sum_num = 0

    failed = 0
    finished = 0
    img_diff_count = 0
    text_diff_count = 0
    text_base_count = 0

    db_data = get_imagetaskinfo()
    svIP = db_data[0]
    langs = db_data[1]
    env_type = db_data[2]
    status = db_data[3]

    remote_path = '/search/odin/test/gongyanli/deploy/'

    # ssh登录，启动环境
    cmds_base1 = "python " + remote_path + "%s %d" % ('start.py', mission_id)
    out1, err1 = lauch.startsh(ip, user, pwd, cmds_base1)
    print(out1)
    print(err1)
    out1 = out1[-1].strip('\n').strip("'")

    if out1 == 'env_success':
        update_errorlog("[%s] SSH: lauch environment successfully. \n" % (get_now_time()))

        for lang in langs.split(','):
            temp = lang.split('_')
            from_langs = temp[0]
            to_langs = temp[1]


            # ssh登录，切换语言
            cmds_base2 = "python " + remote_path + "%s %s %d" % ('switch_lang.py', from_langs, mission_id)
            out2, err2 = lauch.startsh(ip, user, pwd, cmds_base2)
            out2 = out2[-1].strip('\n').strip("'")


            set_status(1)

            if out2 == 'switch_langs':
                update_errorlog("[%s] Switch Language [%s] successfully. \n" % (get_now_time(), lang))

                set_status(2)


                sum_num += len(os.listdir(rootpath + origin_secpath + lang + '/'))

                update_errorlog("[%s] Post is running. \n" % (get_now_time()))

                for filename in os.listdir(rootpath + origin_secpath + lang + '/'):
                    base64image = imageTobase64(rootpath + origin_secpath + lang + '/' + filename)
                    params_ocr = {
                        'lang': from_langs,
                        'image': base64image,
                    }
                    resp_test = requests.post(url_ocr_test, data=params_ocr, headers=headers)
                    resp_base = requests.post(url_ocr_base, data=params_ocr, headers=headers)

                    ocr_test = resp_test.json()
                    ocr_base = resp_base.json()

                    test_issuccess = ocr_test['success']
                    base_issuccess = ocr_base['success']

                    if (test_issuccess == int(1) & base_issuccess == int(1)):
                        finished += 1

                        # 计算距离
                        distance_data = json.loads(ReturnRes(ocr_test, ocr_base))

                        img_diff_count += distance_data['img_diff_count']
                        text_diff_count += distance_data['text_diff_count']
                        text_base_count += distance_data['text_base_count']

                        rankInfo = distance_data['sum_distance']
                        result = json.dumps(distance_data['result'])

                        test_Img1, testpath = post_image(lang, from_langs, to_langs, base64image,url_pic_test,filename, 'test')
                        test_Img2, basepath = post_image(lang, from_langs, to_langs, base64image,url_pic_base,filename, 'base')

                        sql_result = "INSERT INTO  %s(taskid_id,rankInfo,result,testImg,basepath,testpath,test_status,base_status,filename) values('%d','%d','%s','%s','%s','%s','%d','%d','%s')" % (
                            database_result, mission_id, rankInfo, pymysql.escape_string(result), test_Img1, basepath,
                            testpath, test_issuccess, base_issuccess, filename)

                        cursor.execute(sql_result)
                        db.commit()

                    else:
                        failed += 1

                sql_image = "UPDATE %s set end_time='%s', sum_num='%d',finished='%d',failed = '%d',img_diff_count='%d',text_diff_count = '%d',text_base_count = '%d',status=4 where id=%d" % (
                    database_image, get_now_time(), sum_num, finished, failed, img_diff_count, text_diff_count,
                    text_base_count,
                    mission_id)

                cursor.execute(sql_image)
                db.commit()

                status_data = get_imagetaskinfo()
                if status_data[3] == 4:
                    update_errorlog("[%s] Post [%s] has been completed. \n" % (get_now_time(), lang))
                    continue

            else:
                update_errorlog("[%s] Switch Language [%s] failed. \n" % (get_now_time(), lang))

    else:
        update_errorlog("[%s] SSH: lauch environment failed. \n" % (get_now_time()))
    return 0


def post_image(lang, from_langs, to_langs, base64image, url, filename, type):
    params_img = {
        'from': from_langs,
        'to': to_langs,
        'image': base64image,
        'result_type': 'image'
    }

    # resp = requests.post('http://api.image.sogou/v1/open/ocr_translate.json', data=params_img)
    resp = requests.post(url, data=params_img)
    result = resp.json()

    testImg = origin_secpath + lang + '/' + filename
    path = ''

    if result['success'] == int(1):
        pic = result['pic']
        pic = base64.b64decode(pic)

        filename = filename[:-4]

        isPath = rootpath + dest_secpath + lang + '/' + filename + '/'
        storePath = dest_secpath + lang + '/' + filename + '/'
        if not os.path.exists(isPath):
            os.makedirs(isPath)
        if type == 'test':

            file = open(isPath + filename + '_test.jpg', 'wb')
            path = storePath + filename + '_test.jpg'
            file.write(pic)
            # ResultInfo.objects.filter(id=ResultInfo_id).update(testpath=path)
            file.close()
        elif type == 'base':
            file = open(isPath + filename + '_base.jpg', 'wb')
            path = storePath + filename + '_base.jpg'
            file.write(pic)
            # ResultInfo.objects.filter(id=ResultInfo_id).update(basepath=path)
            file.close()
        else:
            update_errorlog("[%s] [%s] of the image don't belong to base or test. \n" % (get_now_time(), filename))

        return testImg, path
    else:
        update_errorlog("[%s] [%s] of the image api [%s] failed. \n" % (get_now_time(), filename, type))
        return testImg, path


if __name__ == '__main__':
    # post_ocr('http://api.image.sogou/v1/ocr/basic.json', 'http://api.image.sogou/v1/ocr/basic.json', 'zh-CHS')
    # post_image('en', 'zh-CHS', base64, filename, url, type)
    # get_material()
    post_ocr()
