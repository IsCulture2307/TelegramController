import os
import sys


def resource_path(relative_path):
    """ 获取资源的绝对路径, 兼容开发模式和 PyInstaller 打包后的模式 """
    try:
        # PyInstaller 创建的临时文件夹, 并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def app_path(relative_path=""):
    """
    获取应用程序可执行文件所在的目录。
    兼容开发模式和 PyInstaller 打包后的模式。
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 .exe 文件
        application_path = os.path.dirname(sys.executable)
    else:
        # 如果是直接运行的 .py 文件
        application_path = os.path.dirname(os.path.abspath(__file__))
        # 在我们的项目结构中，helpers.py 在 utils/ 里，所以需要返回上一级
        application_path = os.path.join(application_path, '..')

    return os.path.join(application_path, relative_path)