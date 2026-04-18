import sys
import traceback
with open("d:/LX/Desktop/deskpot/test_output.txt", "w") as f:
    f.write("Starting test...\n")
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        f.write("QApplication created\n")
        
        from ui.pet_window import PetWindow
        from data.asset_manifest import AssetManifest
        f.write("Imports successful\n")
        
        manifest = AssetManifest()
        f.write("AssetManifest created\n")
        
        win = PetWindow(manifest)
        f.write("PetWindow created successfully\n")
        f.write(f"Window visible: {win.isVisible()}\n")
        f.write(f"Window size: {win.size()}\n")
        f.write(f"Window width: {win.width()}, height: {win.height()}\n")
        
        win.show()
        f.write("Window shown\n")
        
        import time
        time.sleep(2)
        f.write("After sleep\n")
        app.quit()
        f.write("Done\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
        traceback.print_exc(file=f)