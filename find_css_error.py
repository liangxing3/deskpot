with open('ui/settings_panel.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("检查CSS样式相关行...")
in_css = False
css_start_line = 0
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    
    # 检查CSS样式块的开始
    if 'setStyleSheet(' in line:
        in_css = True
        css_start_line = i
        print(f"CSS块起始于第 {i} 行")
    
    # 检查CSS块内的内容
    if in_css:
        # 检查是否有潜在的语法问题
        if 'background:' in line and 'qlineargradient' in line:
            print(f"{i:3d}: {stripped}")
            
        # 检查CSS结束
        if '"""' in line and i > css_start_line:
            quotes_count = line.count('"""')
            if quotes_count % 2 == 1:  # 奇数个三引号，表示结束
                print(f"CSS块结束于第 {i} 行")
                in_css = False
    
    # 特别关注第37行附近的区域
    if i >= 30 and i <= 45:
        print(f"{i:3d}: {stripped}")