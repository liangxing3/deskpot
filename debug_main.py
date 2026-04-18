import sys
import traceback
from PySide6.QtWidgets import QApplication

from core.pet_controller import AppController
from utils.exception_handler import install_global_exception_handler
from utils.font_loader import configure_application_font
from utils.logger import configure_logging

def main() -> int:
    print("开始配置日志...")
    logger = configure_logging()
    print("安装全局异常处理器...")
    install_global_exception_handler(logger)

    print("创建 QApplication...")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    print("配置应用字体...")
    configure_application_font(app, logger)
    print("创建控制器...")
    controller = AppController(app, logger)
    app._desktop_pet_controller = controller
    print("启动应用循环...")
    return app.exec()

if __name__ == "__main__":
    print("启动桌面宠物应用...")
    try:
        exit_code = main()
        print(f"应用退出，代码: {exit_code}")
    except Exception as e:
        print(f"应用启动失败: {e}")
        traceback.print_exc()
    finally:
        print("完成")