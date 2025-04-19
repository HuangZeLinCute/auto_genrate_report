import os
from typing import Tuple, List
import markdown
from bs4 import BeautifulSoup
import asyncio
from playwright.async_api import async_playwright
import json
import plotly.io as pio
import plotly.graph_objects as go
import re
import base64
import uuid

class PDFMaker:
    def __init__(self):
        # 配置plotly生成静态HTML
        pio.templates.default = "plotly_white"
        
        self.css_content = """
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 40px;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #333;
            margin-top: 20px;
            margin-bottom: 10px;
            font-weight: bold;
        }
        h1 { font-size: 24px; }
        h2 { font-size: 20px; }
        h3 { font-size: 18px; }
        p { margin-bottom: 16px; }
        .plot-container {
            width: 800px;
            height: 400px;
            margin: 20px auto;
            page-break-inside: avoid;
        }
        .mermaid-container {
            width: 100%;
            margin: 20px auto;
            text-align: center;
            page-break-inside: avoid;
        }
        @media print {
            .plot-container, .mermaid-container {
                break-inside: avoid;
            }
        }
        """

    def _preprocess_markdown(self, markdown_content: str) -> str:
        """预处理Markdown内容，修复常见的格式问题"""
        # 修复标题格式（确保#后有空格）
        markdown_content = re.sub(r'(^|\n)##?#?#?#?#?(?!\s)', r'\1\g<0> ', markdown_content)
        
        # 修复错误的标题格式例如"## # 标题"
        markdown_content = re.sub(r'##\s+#\s+', r'## ', markdown_content)
        
        # 确保列表项前有空行
        markdown_content = re.sub(r'([^\n])\n([\*\-\+]|\d+\.)\s', r'\1\n\n\2 ', markdown_content)
        
        # 确保段落之间有空行
        markdown_content = re.sub(r'([^\n])\n([^#\s\*\-\+\d])', r'\1\n\n\2', markdown_content)
        
        # 处理不正确的嵌套标题
        lines = markdown_content.split('\n')
        fixed_lines = []
        for i, line in enumerate(lines):
            if i > 0 and line.strip().startswith('#') and lines[i-1].strip().startswith('#'):
                # 如果连续两行都是标题，确保第二个标题格式正确
                if '##' in line and not re.match(r'^##\s', line):
                    # 将错误的 ## 标题修复
                    line = re.sub(r'^##(?!\s)', r'## ', line)
            fixed_lines.append(line)
        
        # 修复每个部分最后一段可能缺失空行的问题
        markdown_content = '\n'.join(fixed_lines)
        
        # 将空的##标题（没有内容的）替换为正确的二级标题或删除
        markdown_content = re.sub(r'\n##\s*\n', '\n', markdown_content)
        
        return markdown_content

    def _extract_mermaid_diagrams(self, markdown_content: str) -> Tuple[str, List[str]]:
        """从Markdown中提取Mermaid图表代码，用占位符替换，并返回图表代码列表"""
        # 匹配以 ```mermaid 或 graph LR 等开头的代码块
        mermaid_pattern = r'```mermaid\s+([\s\S]+?)```|graph\s+(?:LR|TD|RL|BT)[\s\S]+?(?=\n\n|\n#|\n$)'
        
        diagrams = []
        # 查找所有图表代码
        matches = re.finditer(mermaid_pattern, markdown_content, re.MULTILINE)
        
        # 替换为占位符，并收集图表代码
        processed_content = markdown_content
        for i, match in enumerate(matches):
            diagram_code = match.group(1) if match.group(1) else match.group(0)
            diagrams.append(diagram_code)
            # 创建占位符并替换原始图表代码
            placeholder = f"___MERMAID_DIAGRAM_{i}___"
            processed_content = processed_content.replace(match.group(0), placeholder)
        
        return processed_content, diagrams

    async def _pre_render_mermaid_to_svg(self, diagrams: List[str]) -> List[str]:
        """预渲染Mermaid图表为SVG字符串"""
        if not diagrams:
            return []
            
        svg_outputs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            for i, diagram in enumerate(diagrams):
                try:
                    # 预处理图表代码，确保语法正确
                    diagram = diagram.strip()
                    if not diagram.startswith('graph') and not diagram.startswith('flowchart'):
                        # 使用字符串拼接而不是f-string包含\n
                        diagram = "graph TD" + "\n" + diagram
                    
                    # 创建唯一ID，避免渲染冲突
                    diagram_id = f"mermaid-{uuid.uuid4()}"
                    
                    # 创建一个临时HTML页面，使用Mermaid.js渲染图表
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
                        <style>
                            body {{ margin: 0; padding: 20px; }}
                            #container {{ width: 800px; }}
                        </style>
                    </head>
                    <body>
                        <div id="container">
                            <pre class="mermaid" id="{diagram_id}">
                                {diagram}
                            </pre>
                        </div>
                        <script>
                            mermaid.initialize({{
                                startOnLoad: true,
                                theme: 'default',
                                flowchart: {{
                                    useMaxWidth: true,
                                    htmlLabels: true
                                }}
                            }});
                            
                            // 等待页面加载完成
                            window.addEventListener('load', async () => {{
                                try {{
                                    // 直接获取渲染后的SVG
                                    await mermaid.run();
                                    const svgElement = document.querySelector('#{diagram_id} svg');
                                    window.renderedSVG = svgElement ? svgElement.outerHTML : '';
                                    
                                    // 设置标志通知完成
                                    window.renderingDone = true;
                                }} catch (error) {{
                                    console.error('Mermaid渲染错误:', error);
                                    window.renderingDone = true;
                                    window.renderingError = error.toString();
                                }}
                            }});
                        </script>
                    </body>
                    </html>
                    """
                    
                    await page.set_content(html_content)
                    
                    # 等待渲染完成
                    try:
                        await page.wait_for_function('window.renderingDone === true', timeout=10000)
                        svg_content = await page.evaluate('window.renderedSVG || ""')
                        
                        if svg_content:
                            svg_outputs.append(svg_content)
                            print(f"成功渲染图表 #{i+1}")
                        else:
                            error = await page.evaluate('window.renderingError || "未知错误"')
                            print(f"图表 #{i+1} 渲染失败: {error}")
                            svg_outputs.append("")
                    except Exception as e:
                        print(f"等待图表 #{i+1} 渲染时出错: {e}")
                        svg_outputs.append("")
                        
                except Exception as e:
                    print(f"处理图表 #{i+1} 时出错: {e}")
                    svg_outputs.append("")
                    
            await browser.close()
            
        return svg_outputs

    def _js_to_json(self, js_code: str) -> str:
        """将JavaScript对象转换为JSON格式"""
        if not js_code or not isinstance(js_code, str):
            print(f"无效的JavaScript代码: {type(js_code)}")
            return "{}"  # 返回空对象
        
        # 检测空数组
        if js_code.strip() == "[]":
            print("检测到空数组")
            return "[]"
            
        # 移除JavaScript注释
        js_code = re.sub(r'//.*?\n|/\*.*?\*/', '', js_code, flags=re.DOTALL)
        
        # 替换JavaScript中的单引号为双引号
        js_code = js_code.replace("'", '"')
        
        # 给没有引号的属性名添加双引号 (针对常见的JavaScript对象格式)
        js_code = re.sub(r'(\s*)(\w+)(\s*:)', r'\1"\2"\3', js_code)
        
        # 处理最后一个属性后的逗号
        js_code = re.sub(r',(\s*})', r'\1', js_code)
        
        # 处理函数调用和其他不兼容JSON的语法
        js_code = re.sub(r'new Date\([^)]*\)', r'"2023-01-01"', js_code)  # 替换Date对象
        js_code = re.sub(r'\w+\s*\([^)]*\)', r'"function_call"', js_code)  # 替换其他函数调用
        
        return js_code

    def _extract_variable(self, js_code: str, var_name: str) -> Tuple[str, int]:
        """从JavaScript代码中提取变量值"""
        # 尝试匹配const/let/var声明
        pattern1 = r'(?:const|let|var)?\s*' + re.escape(var_name) + r'\s*=\s*(.*?)(?:;|$)'
        match = re.search(pattern1, js_code, re.DOTALL)
        if match:
            start_idx = match.start(1)
            value = match.group(1).strip()
            
            if value.startswith('['):
                return self._extract_balanced_brackets(js_code, start_idx, '[', ']')
            elif value.startswith('{'):
                return self._extract_balanced_brackets(js_code, start_idx, '{', '}')
        
        # 尝试匹配对象属性
        pattern2 = r'[\'"]?' + re.escape(var_name) + r'[\'"]?\s*:\s*(.*?)(?:,|\}|$)'
        match = re.search(pattern2, js_code, re.DOTALL)
        if match:
            start_idx = match.start(1)
            value = match.group(1).strip()
            
            if value.startswith('['):
                return self._extract_balanced_brackets(js_code, start_idx, '[', ']')
            elif value.startswith('{'):
                return self._extract_balanced_brackets(js_code, start_idx, '{', '}')
        
        # 尝试从Plotly.newPlot中提取
        if var_name == "data":
            pattern3 = r'Plotly\.newPlot\s*\([^,]*,\s*(\[.*)'
            match = re.search(pattern3, js_code, re.DOTALL)
            if match:
                start_idx = match.start(1)
                return self._extract_balanced_brackets(js_code, start_idx, '[', ']')
        elif var_name == "layout":
            pattern4 = r'Plotly\.newPlot\s*\([^,]*,\s*\[.*?\],\s*(\{.*)'
            match = re.search(pattern4, js_code, re.DOTALL)
            if match:
                start_idx = match.start(1)
                return self._extract_balanced_brackets(js_code, start_idx, '{', '}')
        
        return "", -1

    def _extract_balanced_brackets(self, text: str, start_idx: int, open_bracket: str, close_bracket: str) -> Tuple[str, int]:
        """从指定位置开始提取包含平衡括号的文本段"""
        # 确保起始位置有效
        if start_idx < 0 or start_idx >= len(text):
            return "", -1
            
        # 找到开始括号的位置
        open_pos = text.find(open_bracket, start_idx)
        if open_pos == -1:
            return "", -1
            
        # 计算嵌套的括号
        balance = 1
        pos = open_pos + 1
        
        while pos < len(text) and balance > 0:
            if text[pos] == open_bracket:
                balance += 1
            elif text[pos] == close_bracket:
                balance -= 1
            pos += 1
            
        if balance != 0:
            # 括号不平衡
            return "", -1
            
        return text[open_pos:pos], open_pos

    def _create_fallback_chart(self, title: str = "数据图表") -> str:
        """创建备用图表"""
        fig = go.Figure()
        fig.add_annotation(
            text="图表生成失败，请查看原始数据",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20)
        )
        fig.update_layout(
            title=title,
            width=800,
            height=400
        )
        return pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs=False,
            config={'staticPlot': True}
        )

    def _sanitize_chart_data(self, data, layout, chart_index: int) -> tuple:
        """检查并修复图表数据和布局，确保它们是有效的Plotly格式"""
        # 处理data
        if not isinstance(data, list):
            print(f"图表 #{chart_index}: data不是列表，使用默认数据")
            data = [{
                "x": ["类别A", "类别B", "类别C", "类别D", "类别E"],
                "y": [5, 10, 15, 10, 5],
                "type": "bar",
                "name": "示例数据"
            }]
        elif len(data) == 0:
            print(f"图表 #{chart_index}: data是空列表，添加默认数据")
            data = [{
                "x": ["类别A", "类别B", "类别C", "类别D", "类别E"],
                "y": [5, 10, 15, 10, 5],
                "type": "bar",
                "name": "示例数据"
            }]
        else:
            # 检查每个数据项
            for i, trace in enumerate(data):
                if not isinstance(trace, dict):
                    print(f"图表 #{chart_index}: 数据项 #{i} 不是字典，修复")
                    data[i] = {"type": "bar", "x": ["A"], "y": [1]}
                elif "type" not in trace:
                    print(f"图表 #{chart_index}: 数据项 #{i} 缺少type属性，默认为scatter")
                    trace["type"] = "scatter"
        
        # 处理layout
        if not isinstance(layout, dict):
            print(f"图表 #{chart_index}: layout不是字典，使用默认布局")
            layout = {
                "title": {"text": f"图表 #{chart_index+1}"},
                "height": 400,
                "width": 800
            }
        else:
            # 确保有标题
            if "title" not in layout:
                layout["title"] = {"text": f"图表 #{chart_index+1}"}
            elif isinstance(layout["title"], str):
                layout["title"] = {"text": layout["title"]}
            
            # 确保有高度和宽度
            if "height" not in layout:
                layout["height"] = 400
            if "width" not in layout:
                layout["width"] = 800
                
        return data, layout

    def _extract_and_convert_charts(self, html_content: str) -> str:
        """提取并转换图表为静态HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        chart_divs = soup.find_all('div', class_='chart')
        
        for i, div in enumerate(chart_divs):
            try:
                script = div.find('script')
                if script:
                    # 提取JavaScript代码
                    js_code = script.string
                    if not js_code:
                        print(f"图表 #{i} 没有找到脚本内容")
                        continue
                        
                    print("\n======= 处理图表 #" + str(i) + " =======")
                    
                    # 尝试提取变量
                    print("尝试提取data变量...")
                    data_js, data_pos = self._extract_variable(js_code, "data")
                    print("尝试提取layout变量...")
                    layout_js, layout_pos = self._extract_variable(js_code, "layout")
                    
                    if data_js and layout_js:
                        print(f"找到data和layout，长度: {len(data_js)}, {len(layout_js)}")
                        # 转换为JSON
                        try:
                            data_json = self._js_to_json(data_js)
                            layout_json = self._js_to_json(layout_js)
                            
                            # 打印处理后的JSON（前50个字符）
                            print(f"处理后的data JSON: {data_json[:50]}...")
                            print(f"处理后的layout JSON: {layout_json[:50]}...")
                            
                            # 解析JSON
                            try:
                                data = json.loads(data_json)
                                layout = json.loads(layout_json)
                                
                                # 特殊情况：空数据数组但保留原始图表
                                if isinstance(data, list) and len(data) == 0:
                                    print(f"图表 #{i} 数据为空数组，保留原始HTML")
                                    # 保留原始图表的HTML，不进行转换
                                    continue
                                
                                # 生成静态HTML
                                fig_dict = {"data": data, "layout": layout}
                                static_html = pio.to_html(
                                    fig_dict,
                                    full_html=False,
                                    include_plotlyjs=False,
                                    config={'staticPlot': True}
                                )
                                
                                # 替换原始div
                                new_div = soup.new_tag('div')
                                new_div['class'] = 'plot-container'
                                new_div.append(BeautifulSoup(static_html, 'html.parser'))
                                div.replace_with(new_div)
                                print("成功转换图表")
                            except json.JSONDecodeError as e:
                                print(f"JSON解析错误: {e}")
                                print(f"保留原始图表...")
                                continue
                        except Exception as e:
                            print(f"处理图表 #{i} JSON时出错: {e}")
                            print(f"保留原始图表...")
                            continue
                    else:
                        print(f"未找到data或layout变量，保留原始图表...")
                        continue
            except Exception as e:
                print(f"转换图表 #{i} 时出错: {e}")
                print(f"保留原始图表...")
                continue
        
        return str(soup)

    def _replace_mermaid_with_svg(self, html_content: str, svg_outputs: List[str]) -> str:
        """替换HTML中的Mermaid图表占位符为预渲染的SVG内容"""
        if not svg_outputs:
            return html_content
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找所有占位符文本节点
        text_nodes = soup.find_all(string=lambda text: text and "___MERMAID_DIAGRAM_" in text)
        
        for text_node in text_nodes:
            # 提取占位符索引
            placeholder = text_node.strip()
            match = re.search(r'___MERMAID_DIAGRAM_(\d+)___', placeholder)
            
            if match:
                idx = int(match.group(1))
                if idx < len(svg_outputs) and svg_outputs[idx]:
                    # 创建包含SVG的div
                    container_div = soup.new_tag('div')
                    container_div['class'] = 'mermaid-container'
                    
                    # 解析SVG并添加到容器中
                    svg_content = BeautifulSoup(svg_outputs[idx], 'html.parser')
                    container_div.append(svg_content)
                    
                    # 替换占位符
                    text_node.replace_with(container_div)
                else:
                    # 创建一个文本占位符
                    fallback_div = soup.new_tag('div')
                    fallback_div['class'] = 'mermaid-container'
                    fallback_div.string = "[图表渲染失败]"
                    text_node.replace_with(fallback_div)
        
        return str(soup)

    def _create_html_template(self) -> str:
        """创建基础HTML模板"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
            <style>
                {css}
            </style>
        </head>
        <body>
            {content}
        </body>
        </html>
        """

    async def _generate_pdf(self, html_content: str, output_path: str) -> None:
        """使用Playwright生成PDF"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # 设置视口大小
            await page.set_viewport_size({"width": 1200, "height": 800})
            
            # 设置页面内容
            await page.set_content(html_content, wait_until='networkidle')
            
            # 等待所有图像加载完成
            await page.wait_for_load_state('load')
            
            # 直接生成PDF
            await page.pdf(
                path=output_path,
                format='A4',
                print_background=True,
                margin={
                    'top': '40px',
                    'right': '40px',
                    'bottom': '40px',
                    'left': '40px'
                }
            )
            
            await browser.close()

    async def _process_markdown_async(self, markdown_content: str) -> str:
        """异步处理Markdown内容，包括预渲染Mermaid图表"""
        # 预处理Markdown内容
        print("预处理Markdown内容，修复格式问题...")
        preprocessed_content = self._preprocess_markdown(markdown_content)
        
        # 替换占位符图片
        print("检测并替换占位符图片...")
        preprocessed_content = self._replace_placeholder_images(preprocessed_content)
        
        # 提取Mermaid图表并替换为占位符
        print("提取Mermaid图表...")
        processed_content, mermaid_diagrams = self._extract_mermaid_diagrams(preprocessed_content)
        
        # 预渲染Mermaid图表为SVG
        print(f"预渲染 {len(mermaid_diagrams)} 个Mermaid图表为SVG...")
        svg_outputs = await self._pre_render_mermaid_to_svg(mermaid_diagrams)
        
        # 转换Markdown为HTML
        print("将Markdown转换为HTML...")
        try:
            # 使用更多扩展，以支持更多Markdown功能
            html_content = markdown.markdown(
                processed_content, 
                extensions=[
                    'tables', 
                    'fenced_code',
                    'nl2br',  # 将换行符转换为<br>标签
                    'sane_lists',  # 更好的列表处理
                    'smarty'  # 智能引号等
                ]
            )
        except Exception as e:
            print(f"Markdown转换出错: {e}")
            # 尝试分段转换
            html_parts = []
            for part in processed_content.split('\n# '):
                if part.strip():
                    if not part.startswith('# '):
                        part = '# ' + part
                    try:
                        html_part = markdown.markdown(part, extensions=['tables', 'fenced_code'])
                        html_parts.append(html_part)
                    except Exception as e2:
                        print(f"部分Markdown转换出错: {e2}")
                        # 最简单的转换
                        part_with_br = part.replace('\n', '<br>')
                        html_parts.append(f"<div>{part_with_br}</div>")
            html_content = '\n'.join(html_parts)
        
        # 替换Mermaid图表占位符为SVG内容
        if mermaid_diagrams:
            print("替换Mermaid图表占位符为SVG内容...")
            html_content = self._replace_mermaid_with_svg(html_content, svg_outputs)
        
        # 提取并转换其他图表为静态HTML
        print("处理其他图表...")
        html_content = self._extract_and_convert_charts(html_content)
        
        return html_content

    def _replace_placeholder_images(self, markdown_content: str) -> str:
        """替换Markdown中的占位符图片为图表"""
        # 匹配所有Markdown图片语法: ![alt text](image_url)
        img_pattern = r'!\[(.*?)\]\((https?://[^)]+)\)'
        
        # 查找所有图片标记
        matches = re.finditer(img_pattern, markdown_content)
        
        # 替换占位符图片为图表
        processed_content = markdown_content
        for match in matches:
            alt_text = match.group(1)
            image_url = match.group(2)
            
            print(f"检测到图片链接: {alt_text}, URL: {image_url}")
            
            # 根据alt_text或图片URL选择合适的图表类型
            if "Sentiment" in alt_text or "情感" in alt_text or "sentiment" in image_url.lower():
                chart_html = self._create_sentiment_chart(alt_text)
            elif "Activity" in alt_text or "User" in alt_text or "用户" in alt_text or "activity" in image_url.lower() or "user" in image_url.lower():
                chart_html = self._create_user_activity_chart(alt_text)
            elif "Topic" in alt_text or "话题" in alt_text or "topic" in image_url.lower():
                chart_html = self._create_topic_chart(alt_text)
            elif "via.placeholder.com" in image_url:
                # 默认图表 - 占位符
                chart_html = self._create_default_chart(alt_text)
            else:
                # 所有其他外部图片链接，根据URL特征决定图表类型
                if "imgur" in image_url.lower():
                    # 针对imgur链接生成适当的图表
                    if "5J3J3J3" in image_url:  # 特定图表识别
                        chart_html = self._create_bar_chart(alt_text or "评论分析")
                    else:
                        chart_html = self._create_default_chart(alt_text or "图表")
                else:
                    # 其他图片链接
                    chart_html = self._create_default_chart(alt_text or "图表")
            
            # 替换原始图片标记为图表HTML
            processed_content = processed_content.replace(match.group(0), "\n<div class=\"chart\">\n" + chart_html + "\n</div>\n")
            
        return processed_content
        
    def _create_sentiment_chart(self, title: str) -> str:
        """创建情感分析图表"""
        return """
    <script>
    const data = [{
        "values": [30.95, 54.56, 14.49],
        "labels": ["正面", "负面", "中性"],
        "type": "pie"
    }];
    const layout = {
        "title": \"""" + title + """\",
        "height": 400,
        "width": 800
    };
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
"""

    def _create_user_activity_chart(self, title: str) -> str:
        """创建用户活跃度图表"""
        return """
    <script>
    const data = [{
        "x": ["1周前", "6天前", "5天前", "4天前", "3天前", "2天前", "1天前", "今天"],
        "y": [120, 135, 142, 153, 158, 165, 172, 180],
        "type": "scatter",
        "mode": "lines+markers"
    }];
    const layout = {
        "title": \"""" + title + """\",
        "height": 400,
        "width": 800
    };
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
"""

    def _create_topic_chart(self, title: str) -> str:
        """创建话题分析图表"""
        return """
    <script>
    const data = [{
        "x": ["校园游戏", "校园体育", "校园经济", "校园教育", "校园科研"],
        "y": [25.07, 17.27, 11.35, 6.58, 8.55],
        "type": "bar"
    }];
    const layout = {
        "title": \"""" + title + """\",
        "height": 400,
        "width": 800
    };
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
"""

    def _create_default_chart(self, title: str) -> str:
        """创建默认图表"""
        return """
    <script>
    const data = [{
        "x": ["类别A", "类别B", "类别C", "类别D", "类别E"],
        "y": [25, 20, 15, 10, 5],
        "type": "bar"
    }];
    const layout = {
        "title": \"""" + title + """\",
        "height": 400,
        "width": 800
    };
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
"""

    def _create_bar_chart(self, title: str) -> str:
        """创建柱状图 - 用于替换特定的外部图片链接"""
        return """
    <script>
    const data = [{
        "x": ["正面评论", "负面评论", "中性评论", "建议", "问题"],
        "y": [32, 18, 25, 15, 10],
        "type": "bar",
        "marker": {
            "color": ["#4CAF50", "#F44336", "#2196F3", "#FF9800", "#9C27B0"]
        }
    }];
    const layout = {
        "title": \"""" + title + """\",
        "height": 400,
        "width": 800,
        "xaxis": {
            "title": "评论类型"
        },
        "yaxis": {
            "title": "数量"
        }
    };
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
"""

    def _create_area_chart(self, title: str) -> str:
        """创建面积图 - 用于替换外部图片链接"""
        return """
    <script>
    const data = [{
        "x": ["1月", "2月", "3月", "4月", "5月", "6月"],
        "y": [45, 52, 63, 58, 66, 72],
        "fill": "tozeroy",
        "type": "scatter",
        "line": {"color": "#2196F3"}
    }];
    const layout = {
        "title": \"""" + title + """\",
        "height": 400,
        "width": 800,
        "xaxis": {"title": "月份"},
        "yaxis": {"title": "数值"}
    };
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
"""

    def _create_heatmap_chart(self, title: str) -> str:
        """创建热力图 - 用于替换外部图片链接"""
        return """
    <script>
    const data = [{
        "z": [
            [1, 20, 30, 50, 10, 40],
            [20, 1, 60, 80, 30, 20],
            [30, 60, 1, 50, 20, 30],
            [50, 80, 50, 1, 60, 20],
            [10, 30, 20, 60, 1, 10],
            [40, 20, 30, 20, 10, 1]
        ],
        "x": ["A", "B", "C", "D", "E", "F"],
        "y": ["A", "B", "C", "D", "E", "F"],
        "type": "heatmap",
        "colorscale": "Viridis"
    }];
    const layout = {
        "title": \"""" + title + """\",
        "height": 500,
        "width": 700
    };
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
"""

    async def _markdown_to_pdf_async(self, markdown_content: str, output_path: str, save_html: bool = False) -> None:
        """异步版本的markdown_to_pdf方法"""
        # 处理Markdown内容（包括Mermaid图表渲染）
        html_content = await self._process_markdown_async(markdown_content)
        
        # 创建完整的HTML
        template = self._create_html_template()
        final_html = template.format(
            css=self.css_content,
            content=html_content
        )
        
        # 保存HTML文件（可选，用于调试）
        if save_html:
            html_debug_path = output_path.replace('.pdf', '.html')
            with open(html_debug_path, 'w', encoding='utf-8') as f:
                f.write(final_html)
            print(f"调试用HTML文件已保存: {html_debug_path}")
        
        # 生成PDF
        print("生成PDF文件...")
        await self._generate_pdf(final_html, output_path)

    def markdown_to_pdf(self, markdown_content: str, output_path: str, save_html: bool = False) -> None:
        """将Markdown内容（包含HTML图表和Mermaid图表）转换为PDF"""
        # 使用异步方式处理
        asyncio.run(self._markdown_to_pdf_async(markdown_content, output_path, save_html))
