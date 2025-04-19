from core.api_manager import APIManager
from typing import Dict, List, Any, Tuple
import re

class ReportCreator:
    def __init__(self, api_name):
        self.api_manager = APIManager(api_name)
        self.sections = [
            "整体情况概览",
            "情感倾向分析",
            "活跃用户情况",
            "主要话题分析",
            "潜在风险点",
            "未来趋势预测"
        ]
        # 每个部分的最大字符数
        self.max_section_length = 1000
        # 每个部分的建议段落数
        self.paragraphs_per_section = 3

    def generate_outline_prompt(self, data: dict) -> str:
        """生成大纲提示词"""
        prompt = f"""
你是一个擅长舆情分析的专家，下面是一组监测到的网络数据。请根据这些数据生成一份简洁的舆情报告大纲。

大纲需要包含以下几个部分，每个部分限制2-3个要点：
1. 整体情况概览
2. 情感倾向分析
3. 活跃用户情况
4. 主要话题分析
5. 潜在风险点
6. 未来趋势预测

对于每个部分，请列出2-3个关键子标题或要点，确保分析简洁但深入。

数据内容如下：
{data}

输出格式示例：
# 整体情况概览
- 总体数据量与时间分布
- 主要平台分布情况
...

# 情感倾向分析
...

请仅输出大纲内容，不要有多余的解释。
"""
        return prompt

    def generate_section_prompt(self, data: dict, section: str, outline: str, previous_sections: str = "") -> str:
        """为特定部分生成提示词"""
        section_outline = self._extract_section_outline(outline, section)
        
        chart_instruction = ""
        if section == "情感倾向分析":
            chart_instruction = """请在此部分开头包含一个情感分布饼图，使用以下格式：
<div class="chart">
    <script>
    const data = [{{
        "values": [35, 25, 40],
        "labels": ["正面", "负面", "中性"],
        "type": "pie"
    }}];
    const layout = {{
        "title": "情感分布",
        "height": 400,
        "width": 800
    }};
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
</div>
"""
        elif section == "活跃用户情况":
            chart_instruction = """请在此部分开头包含一个用户活跃度折线图，使用以下格式：
<div class="chart">
    <script>
    const data = [{{
        "x": ["1周前", "6天前", "5天前", "4天前", "3天前", "2天前", "1天前", "今天"],
        "y": [120, 135, 142, 153, 158, 165, 172, 180],
        "type": "scatter",
        "mode": "lines+markers"
    }}];
    const layout = {{
        "title": "用户活跃度趋势",
        "height": 400,
        "width": 800
    }};
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
</div>
"""
        elif section == "主要话题分析":
            chart_instruction = """请在此部分开头包含一个话题分布条形图，使用以下格式：
<div class="chart">
    <script>
    const data = [{{
        "x": ["话题A", "话题B", "话题C", "话题D", "话题E"],
        "y": [25, 20, 15, 10, 5],
        "type": "bar"
    }}];
    const layout = {{
        "title": "热门话题分布",
        "height": 400,
        "width": 800
    }};
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
</div>
"""
        
        # 为未来趋势预测部分添加特殊指导
        specific_instruction = ""
        if section == "未来趋势预测":
            specific_instruction = """
特别注意：
1. 不要使用"根据提供的数据分析，以下是对未来趋势的预测："或类似的引导句开头
2. 直接以具体的趋势预测内容开始，如"## 情感趋势变化"、"## 用户行为预测"等
3. 避免使用任何形式的引言句，直接进入主题
4. 每个预测点应该简洁明了，直接描述预测内容
"""
        
        # 为每个部分添加不同的格式指导
        format_guidance = """
1. 使用正确的Markdown格式：
   - 二级标题使用 ## 格式（例如：## 二级标题）
   - 确保标题后有一个空行
   - 段落之间要有空行
   - 列表项使用 1. 2. 3. 或 - 格式，且前后要有空行

2. 严格遵循以下格式示例：

## 二级标题
这是一个段落，包含具体内容。

这是另一个段落，注意段落之间有空行。

## 另一个二级标题
- 这是列表项1
- 这是列表项2

1. 这是有序列表项1
2. 这是有序列表项2
"""
        
        prompt = f"""
你是一个擅长舆情分析的专家。请根据以下数据和大纲，简明扼要地撰写舆情报告的【{section}】部分。

数据内容：
{data}

{section}部分的大纲：
{section_outline}

{chart_instruction}
{specific_instruction}

要求：
1. 字数控制在{self.max_section_length}字以内
2. 分为{self.paragraphs_per_section}个段落左右
3. 内容简洁专业
4. 使用正确的Markdown格式
5. 只生成【{section}】部分的内容
6. 如果包含图表，请确保图表位于此部分的开头位置

{format_guidance}

请直接开始生成，无需添加标题（如"# {section}"），我会在合并时自动添加。
"""
        return prompt

    def generate_charts_prompt(self, data: dict, report_content: str) -> str:
        """生成图表补充提示词"""
        prompt = f"""
你是一个擅长舆情分析和数据可视化的专家。下面是一份舆情分析报告，但其中的图表部分可能不完整或缺失。请根据报告内容和原始数据，生成或补充必要的图表。

原始数据：
{data}

报告内容：
{report_content}

请生成以下三个核心图表，使用HTML和Plotly.js：

1. 情感分布饼图：
<div class="chart">
    <script>
    const data = [{{
        "values": [35, 25, 40],  // 请根据实际情感分布修改这些数值
        "labels": ["正面", "负面", "中性"],
        "type": "pie"
    }}];
    const layout = {{
        "title": "情感分布",
        "height": 400,
        "width": 800
    }};
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
</div>

2. 用户活跃度趋势图：
<div class="chart">
    <script>
    const data = [{{
        "x": ["1周前", "6天前", "5天前", "4天前", "3天前", "2天前", "1天前", "今天"],
        "y": [120, 135, 142, 153, 158, 165, 172, 180],  // 请根据实际数据修改这些数值
        "type": "scatter",
        "mode": "lines+markers"
    }}];
    const layout = {{
        "title": "用户活跃度趋势",
        "height": 400,
        "width": 800
    }};
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
</div>

3. 热门话题分布图：
<div class="chart">
    <script>
    const data = [{{
        "x": ["话题A", "话题B", "话题C", "话题D", "话题E"],  // 请用实际话题名称替换
        "y": [25, 20, 15, 10, 5],  // 请根据实际数据修改这些数值
        "type": "bar"
    }}];
    const layout = {{
        "title": "热门话题分布",
        "height": 400,
        "width": 800
    }};
    Plotly.newPlot(document.currentScript.parentElement, data, layout);
    </script>
</div>

请根据报告内容和原始数据调整图表数据，使其更准确地反映实际情况。请只返回这三个图表的HTML代码，无需其他说明。
"""
        return prompt

    def _extract_section_outline(self, outline: str, section: str) -> str:
        """从大纲中提取特定部分的内容"""
        pattern = rf"#\s*{re.escape(section)}(.*?)(?=#\s*\w|$)"
        match = re.search(pattern, outline, re.DOTALL)
        if match:
            return match.group(1).strip()
        return f"关于{section}的分析"

    def _merge_sections(self, sections_content: List[str]) -> str:
        """合并各个部分内容并进行后处理"""
        # 添加标题
        titled_sections = []
        for i, content in enumerate(sections_content):
            section_title = f"# {self.sections[i]}"
            
            # 检查内容是否已经包含图表
            has_chart = '<div class="chart">' in content
            
            # 处理可能存在的格式问题
            content = self._fix_section_format(content)
            
            # 特殊处理未来趋势预测部分
            if self.sections[i] == "未来趋势预测":
                # 删除常见的引导性开场白
                content = re.sub(r'^(?:根据.*?分析.*?(?:以下|如下).*?(?:预测|趋势).*?[:：])', '', content, flags=re.DOTALL)
                content = re.sub(r'^(?:以下是.*?对.*?(?:预测|趋势).*?[:：])', '', content, flags=re.DOTALL)
                content = re.sub(r'^(?:通过分析.*?(?:预测|趋势).*?[:：])', '', content, flags=re.DOTALL)
                content = re.sub(r'^(?:(?:预测|分析)表明.*?[:：])', '', content, flags=re.DOTALL)
                # 清理处理后可能留下的空行
                content = re.sub(r'^\s*\n+', '', content)
                # 确保第一个二级标题有正确的格式
                if not re.match(r'^## ', content):
                    # 如果内容不是以二级标题开始，查找第一个二级标题
                    first_heading = re.search(r'## ', content)
                    if first_heading:
                        # 删除第一个标题之前的所有内容
                        content = content[first_heading.start():]
                    else:
                        # 如果没有二级标题，添加一个
                        content = "## 趋势预测\n\n" + content
            
            # 如果开头不是图表，添加标题
            if has_chart:
                # 确保图表在标题之后
                titled_content = f"{section_title}\n\n{content}"
            else:
                titled_content = f"{section_title}\n\n{content}"
                
            titled_sections.append(titled_content)
        
        # 合并所有部分
        merged_content = "\n\n".join(titled_sections)
        
        # 添加总标题
        merged_content = f"# 舆情分析报告\n\n{merged_content}"
        
        # 删除重复的标题（如果大模型生成了标题）
        for section in self.sections:
            pattern = rf"# {re.escape(section)}\s*\n+\s*# {re.escape(section)}"
            merged_content = re.sub(pattern, f"# {section}", merged_content)
        
        # 确保图表后有适当的空行
        merged_content = re.sub(r'</div>\s*(?!\n\n)', r'</div>\n\n', merged_content)
        
        # 确保各部分之间有足够的空行
        merged_content = re.sub(r"(# \w)", r"\n\1", merged_content)
        
        # 确保二级标题格式一致
        merged_content = re.sub(r"(?<!\n\n)##\s*", r"\n\n## ", merged_content)
        
        # 删除多余的空行
        merged_content = re.sub(r"\n{3,}", "\n\n", merged_content)
        
        # 修复错误的标题格式例如"## # 标题"
        merged_content = re.sub(r'##\s+#\s+', r'## ', merged_content)
        
        # 修复标题格式（确保#后有空格）
        merged_content = re.sub(r'(^|\n)##?#?#?#?#?(?!\s)', r'\1\g<0> ', merged_content)
        
        return merged_content
        
    def _fix_section_format(self, content: str) -> str:
        """修复单个部分的格式问题"""
        # 检查并修复常见的格式问题
        
        # 1. 修复缺少空格的标题格式
        content = re.sub(r'(^|\n)##(?!\s)', r'\1## ', content)
        
        # 2. 修复错误的标题格式例如"## # 标题"
        content = re.sub(r'##\s+#\s+', r'## ', content)
        
        # 3. 确保列表项前有空行
        content = re.sub(r'([^\n])\n([\*\-\+]|\d+\.)\s', r'\1\n\n\2 ', content)
        
        # 4. 确保段落之间有空行
        content = re.sub(r'([^\n])\n([^#\s\*\-\+\d])', r'\1\n\n\2', content)
        
        # 5. 删除空的二级标题
        content = re.sub(r'\n##\s*\n', '\n', content)
        
        # 6. 确保内容以空行结束
        if not content.endswith('\n\n'):
            content = content.rstrip() + '\n\n'
            
        return content

    def create_report(self, data: dict) -> str:
        """生成完整舆情报告"""
        # 第一步：生成报告大纲
        print("第一步：生成报告大纲...")
        outline_prompt = self.generate_outline_prompt(data)
        outline = self.api_manager.get_response(outline_prompt)
        print(f"大纲已生成，长度: {len(outline)} 字符")
        
        # 第二步：逐段生成各部分内容
        sections_content = []
        
        print("第二步：逐段生成各部分内容...")
        for i, section in enumerate(self.sections):
            print(f"生成第 {i+1}/{len(self.sections)} 部分：{section}...")
            section_prompt = self.generate_section_prompt(data, section, outline)
            section_content = self.api_manager.get_response(section_prompt)
            
            # 检查是否超出长度限制
            if len(section_content) > self.max_section_length * 1.5:
                # 如果内容过长，截断并添加说明
                print(f"警告：{section} 内容过长 ({len(section_content)} 字符)，将截断")
                section_content = section_content[:self.max_section_length] + "\n\n..."
            
            sections_content.append(section_content)
            print(f"{section} 部分已生成，长度: {len(section_content)} 字符")
        
        # 第三步：合并内容并后处理
        print("第三步：合并内容并进行后处理...")
        final_report = self._merge_sections(sections_content)
        print(f"报告生成完成，总长度: {len(final_report)} 字符")
        
        return final_report
