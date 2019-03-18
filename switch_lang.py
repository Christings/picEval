from img_deploy import *

from_lang = sys.argv[1]
mission_id=int(sys.argv[2])

if __name__ == "__main__":
    ret = Switch_lang(from_lang,mission_id)
