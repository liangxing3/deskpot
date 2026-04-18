import sys
import traceback
import os

log_file = r"d:\LX\Desktop\deskpot\test_diag.txt"

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

log("=== Starting diagnostic ===")

try:
    log("Step 1: Creating QApplication")
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    log("Step 2: QApplication created successfully")
    
    log("Step 3: Importing modules")
    from ui.pet_window import PetWindow
    from data.asset_manifest import AssetManifest
    from core.runtime_app_controller import AppController
    log("Step 4: All imports successful")
    
    log("Step 5: Creating AssetManifest")
    manifest = AssetManifest()
    log(f"Step 6: AssetManifest created with {len(manifest.entries)} entries")
    
    log("Step 7: Creating PetWindow")
    win = PetWindow(manifest)
    log(f"Step 8: PetWindow created, visible={win.isVisible()}, size={win.width()}x{win.height()}")
    
    log("Step 9: Showing window")
    win.show()
    log(f"Step 10: After show(), visible={win.isVisible()}")
    
    log("Step 11: Process events")
    app.processEvents()
    
    import time
    time.sleep(1)
    app.processEvents()
    log(f"Step 12: After sleep, visible={win.isVisible()}")
    
    app.quit()
    log("=== Diagnostic completed successfully ===")
    
except Exception as e:
    log(f"ERROR: {e}")
    traceback.print_exc(file=open(log_file, "a"))
    log("=== Diagnostic failed ===")