"path": "assets/GIF/normal.gif"
import sys
from PySide6.QtWidgets import QApplication
from ui.pet_window import PetWindow
from data.asset_manifest import AssetManifest

print("创建应用实例...")
app = QApplication(sys.argv)

print("创建资源清单...")
manifest = AssetManifest()
print(f"找到 {len(manifest.entries)} 个动画条目")

print("创建窗口...")
window = PetWindow(manifest)

print("显示窗口...")
window.show()

print("窗口已显示，运行应用...")
sys.exit(app.exec())