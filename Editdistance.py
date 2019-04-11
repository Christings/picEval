import json
import numpy as np
from shapely.geometry import Polygon
import Levenshtein
import requests
import os
import base64
#compute editdistance
def Distance(str1,str2):
    return Levenshtein.distance(str1,str2)

#compute IOU
def GetIOU(test_coordinate,base_coordinate):
    test_coordinate = np.array(test_coordinate)
    base_coordinate = np.array(base_coordinate)
    test_coordinate = Polygon(test_coordinate[:8].reshape(4,2))
    base_coordinate = Polygon(base_coordinate[:8].reshape(4,2))
    if not test_coordinate.is_valid or not base_coordinate.is_valid:
        return 0
    inter_area = Polygon(test_coordinate).intersection(Polygon(base_coordinate)).area
    union_area = test_coordinate.area + base_coordinate.area - inter_area
    if union_area == 0:
        return 1
    else:
        return (inter_area * 1.0)/union_area

#get coordinate info of each line
def GetRecInfo(result):
    res_info=[]
    for res in result:
        cont = res['content']
        frame = res['frame']
        coords = []
        for fr in frame:
            coord = fr.split(',')
            coords.append(int(coord[0]))
            coords.append(int(coord[1]))
        res_info.append([cont,coords])
    return res_info

#parse response
def ParseResponse(response):
    response_str=response
    #response_str=json.load(response)
    #response_str=response.json()
    if 'result' not in response_str.keys():
        #获取base的识别结果，
        return None
    else:
        return response_str['result']

#calculate the max iou of all results for each line
def CalculateMaxIOU(ious):
    maxIOU_list=[]
    for iou in ious:
        idx = -1
        max_iou=-2
        for i,subIou in enumerate(iou):
            if subIou > max_iou:
                max_iou = subIou
                idx = i
        if max_iou>0.5:
            maxIOU_list.append([idx,max_iou])
        else:
            maxIOU_list.append([-1,-1])
    return maxIOU_list

#match the max iou of both results,find the best matched one
def GetMatchList(test_res_info,base_res_info):
    match_list=[]
    test_len = len(test_res_info)
    base_len = len(base_res_info)
    test_iou = []
    base_iou = []
    for i in range(base_len):
        tmp = [-1]*test_len
        base_iou.append(tmp)
    for i in range(test_len):
        tmp = [-1]*base_len
        test_coord = test_res_info[i][1]
        for j in range(base_len):
            base_coord = base_res_info[j][1]
            iou = GetIOU(test_coord,base_coord)
            tmp[j]=iou
            base_iou[j][i]=iou
        test_iou.append(tmp)
    test_max_iou = CalculateMaxIOU(test_iou)
    base_max_iou = CalculateMaxIOU(base_iou)
    for i,iou in enumerate(test_max_iou):
        idx = iou[0]
        if idx != -1 and base_max_iou[idx][0]==i:
            match_list.append([i,idx])
    return match_list

#Calculate edit distance for test and base response
def GetEditDistance(test_res_info,base_res_info,match_list):
    img_diff = 0
    sum_distance = 0
    base_cont_count=len(base_res_info)
    text_diff=0
    res=[]
    data={}
    for i,j in match_list:
    	res_member={}
        test_str=test_res_info[i][0]
        base_str=base_res_info[j][0]
        edit_distance=Distance(test_str,base_str)
        if edit_distance !=0:
            img_diff = 1
            sum_distance +=edit_distance
            text_diff +=1
        res_member['basecontent']=base_str
        res_member['testcontent']=test_str
        res_member['distance']=edit_distance
        res.append(res_member)
    if len(match_list)!=len(test_res_info) or len(match_list)!=len(base_res_info):
        test_matched_idx=set()
        base_matched_idx=set()
        for i,j in match_list:
            test_matched_idx.add(i)
            base_matched_idx.add(j)
        for idx, info in enumerate(test_res_info):
            res_member = {}
            if idx in test_matched_idx:
                continue
            edit_distance=Distance(info[0],"")
            img_diff=1
            sum_distance+=edit_distance
            text_diff+=1
            res_member['basecontent']=""
            res_member['testcontent']=info[0]
            res_member['distance']=edit_distance
            res.append(res_member)
        for idx, info in enumerate(base_res_info):
            res_member = {}
            if idx in base_matched_idx:
                continue
            edit_distance = Distance("",info[0])
            img_diff = 1
            sum_distance += edit_distance
            text_diff += 1
            res_member['basecontent']=info[0]
            res_member['testcontent']=""
            res_member['distance']=edit_distance
            res.append(res_member)
    data["img_diff_count"]=img_diff
    data["test_base_count"]=base_cont_count
    data["text_diff_count"]=text_diff
    data["sum_distance"]=sum_distance
    data["result"]=res
    return data

def ReturnRes(testResponse,baseResponse):
    test_res=ParseResponse(testResponse)
    base_res=ParseResponse(baseResponse)
    if test_res== None:
        pass
    if base_res == None:
        pass
    test_res_info=GetRecInfo(test_res)
    base_res_info=GetRecInfo(base_res)
    match_list=GetMatchList(test_res_info,base_res_info)
    data=GetEditDistance(test_res_info,base_res_info,match_list)
    return json.dumps(data)

if __name__ == '__main__':
    image_path = os.path.dirname('__file__')+ 'ja.png'
    with open(image_path, "rb") as img:
        bytes = img.read()
        image = base64.b64encode(bytes)
    url1 = "http://10.141.177.27:30000/v1/ocr/basic.json"
    url2 = "http://10.141.177.27:3111/v1/ocr_translate.json"
    header = {'Content-Type': "application/x-www-form-urlencoded"}
    data1 = {'lang': 'ja',
             'image': image,
             'direction_detect':'true'
             }
    data2 = {'from': 'ja',
             'to': 'zh-CHS',
             'image': image,
             'result_type': 'image',
             }
    timeout = 20000
    test_response1 = requests.post(url1, headers=header, data=data1, timeout=float(timeout))
    test_response2 = requests.post(url1, headers=header, data=data1, timeout=float(timeout))

    print(ReturnRes(test_response1.json(),test_response2.json()))