#!/usr/bin/env python3
"""
验证修复是否有效的测试脚本
"""

import sys
import traceback
from pathlib import Path

def test_asset_loading():
    print("正在测试资源加载...")
    
    try:
        # 导入必要的模块
        from data.asset_manifest import AssetManifest
        from utils.paths import resource_path
        
        print("✓ 成功导入 AssetManifest 和 resource_path")
        
        # 创建 AssetManifest 实例
        manifest = AssetManifest()
        print(f"✓ 成功创建 AssetManifest，包含 {len(manifest.entries)} 个条目")
        
        # 测试资源文件是否存在
        print("\n正在测试资源文件是否存在...")
        missing_files = []
        existing_files = []
        
        for entry in manifest.entries[:5]:  # 只测试前5个条目
            path = resource_path(entry.path)
            if path.exists():
                existing_files.append(path)
                print(f"✓ 存在: {path}")
            else:
                missing_files.append(path)
                print(f"✗ 缺失: {path}")
        
        print(f"\n测试结果:")
        print(f"- 找到 {len(existing_files)} 个存在的文件")
        print(f"- 发现 {len(missing_files)} 个缺失的文件")
        
        if len(existing_files) > 0:
            print("✓ 资源路径配置正确，至少有一些资源文件存在")
            return True
        else:
            print("✗ 所有测试的资源文件都不存在，请检查路径配置")
            return False
            
    except Exception as e:
        print(f"✗ 测试过程中出现错误: {e}")
        traceback.print_exc()
        return False

def test_ui_components():
    print("\n正在测试 UI 组件...")
    
    try:
        from ui.pet_window import PetWindow
        from data.asset_manifest import AssetManifest
        print("✓ 成功导入 UI 组件")
        
        manifest = AssetManifest()
        window = PetWindow(manifest)
        print("✓ 成功创建 PetWindow 实例")
        
        return True
    except Exception as e:
        print(f"✗ UI 组件测试失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始验证修复...")
    
    asset_success = test_asset_loading()
    ui_success = test_ui_components()
    
    print(f"\n验证结果:")
    print(f"- 资源加载测试: {'通过' if asset_success else '失败'}")
    print(f"- UI 组件测试: {'通过' if ui_success else '失败'}")
    
    if asset_success and ui_success:
        print("\n✓ 修复验证成功！程序应该能够正常显示 UI。")
    else:
        print("\n✗ 修复验证失败，请检查配置。")