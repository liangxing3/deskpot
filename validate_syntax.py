import ast
import sys

try:
    with open('ui/settings_panel.py', 'r', encoding='utf-8') as f:
        content = f.read()
    ast.parse(content)
    print('✓ 文件语法正确')
except SyntaxError as e:
    print(f'✗ 语法错误: {e}')
    print(f'   行号: {e.lineno}, 列号: {e.offset}')
    if e.lineno:
        lines = content.splitlines()
        print(f'   错误行: {lines[e.lineno-1]}')
        if e.lineno > 1:
            print(f'   前一行: {lines[e.lineno-2]}')
        if e.lineno < len(lines):
            print(f'   后一行: {lines[e.lineno]}')
except Exception as e:
    print(f'✗ 其他错误: {e}')
    import traceback
    traceback.print_exc()