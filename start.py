import img_deploy
import sys,json


#deploy_dict = json.loads(sys.argv[1])


if __name__ == "__main__":
    #deploy_dict = str(sys.argv[1])
    mission_id = int(sys.argv[1].replace('\n',''))
    ret = img_deploy.Deploy_all(mission_id)
