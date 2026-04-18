import json
from pathlib import Path
from data.asset_manifest import AssetManifest
from utils.paths import resource_path

print('检查 manifest.json...')
manifest_path = Path('assets/manifest.json')
if manifest_path.exists():
    print('✓ manifest.json 存在')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f'✓ manifest.json 可读取，包含 {len(data.get("animations", []))} 个动画条目')
else:
    print('✗ manifest.json 不存在')

print('\n检查前几个资源文件...')
manifest = AssetManifest()
for i, entry in enumerate(manifest.entries[:5]):
    path = resource_path(entry.path)
    exists = path.exists()
    status = '✓' if exists else '✗'
    print(f'{status} {entry.id}: {path} ({"存在" if exists else "不存在"})')
    
print("\n所有GIF文件列表:")
gif_dir = Path("assets/GIF")
if gif_dir.exists():
    for gif_file in gif_dir.iterdir():
        if gif_file.suffix.lower() == '.gif':
            print(f"  - {gif_file.name}")
else:
    print("  assets/GIF 目录不存在")