import os
import shutil
from typing import Tuple


def get_baseDir():
    '''
    获取软件的baseDir目录
    '''
    return os.getcwd()

def get_save_info(filePath) -> Tuple[str, str]:
    '''
    返回fileName, saveDir
    @param filePath: 文件的绝对路径
    @return: 返回文件的文件名头部、文件的文件名、文件的保存路径
    '''
    fileDir = os.path.dirname(filePath)
    fileName = filePath.split('/')[-1]
    filePrefix, fileSuffix = os.path.splitext(fileName)

    if fileSuffix == "":
        saveDir = os.path.join(fileDir, f"{filePrefix}_BYXS20")
    else:
        saveDir = os.path.join(fileDir, filePrefix)
    return filePrefix, fileName, saveDir

def clear_and_create_dir(saveDir):
    '''
    删除saveDir文件夹并重
    @param saveDir: 保存文件的文件夹
    '''
    if os.path.exists(saveDir):
        shutil.rmtree(saveDir, ignore_errors=True)
    os.makedirs(saveDir)
