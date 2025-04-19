from data_loader.redis_loader import RedisLoader
from report_generator.report_creator import ReportCreator
from pdf_generator.pdf_maker import PDFMaker
import json
import os
from datetime import datetime

def main():
    print("开始生成舆情报告...")
    
    # 1. 读取Redis数据
    try:
        print("1. 正在读取Redis数据...")
        redis_loader = RedisLoader()
        data = redis_loader.get_all_data()
        print(f"数据读取成功，共有 {len(data)} 个键")
    except Exception as e:
        print(f"从Redis读取数据失败: {e}")
        print("尝试从本地备份文件读取数据...")
        try:
            # 从备份文件加载数据
            with open('redis_export.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"从备份文件读取数据成功，共有 {len(data)} 个键")
        except Exception as backup_e:
            print(f"从备份文件读取数据也失败: {backup_e}")
            return
    
    # 2. 调用大模型分段生成舆情报告
    print("\n2. 正在生成舆情报告...")
    report_creator = ReportCreator(api_name='kimi')  # 可以改成别的API
    report = report_creator.create_report(data)
    
    # 保存报告到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存Markdown版本
    markdown_path = os.path.join(output_dir, f"report_{timestamp}.md")
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Markdown报告已保存至: {markdown_path}")
    
    # 3. 生成PDF文件
    print("\n3. 正在生成PDF文件...")
    pdf_maker = PDFMaker()
    pdf_path = os.path.join(output_dir, f"report_{timestamp}.pdf")
    pdf_maker.markdown_to_pdf(report, pdf_path, save_html=False)
    
    print(f"\n舆情报告生成完成！")
    print(f"- Markdown文件: {markdown_path}")
    print(f"- PDF文件: {pdf_path}")

if __name__ == "__main__":
    main()
