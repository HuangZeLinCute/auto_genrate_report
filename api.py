# main.py
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import uuid
import os
from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel

from report_generator.report_creator import ReportCreator
from pdf_generator.pdf_maker import PDFMaker

app = FastAPI(title="舆情报告生成API")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储任务进度的字典
task_progress: Dict[str, Dict] = {}

class ReportRequest(BaseModel):
    topic: str
    start_date: str
    end_date: str
    output_path: Optional[str] = None

async def generate_report_task(task_id: str, request: ReportRequest):
    try:
        # 更新任务状态为进行中
        task_progress[task_id]["status"] = "processing"
        
        # 创建ReportCreator实例
        creator = ReportCreator()
        
        # 更新进度 - 开始生成报告
        task_progress[task_id].update({
            "progress": 10,
            "message": "正在初始化报告生成..."
        })
        await asyncio.sleep(1)  # 给前端一些时间更新进度
        
        # 生成报告内容
        task_progress[task_id].update({
            "progress": 30,
            "message": "正在生成报告内容..."
        })
        report_content = creator.create_report(
            topic=request.topic,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # 更新进度 - 开始生成PDF
        task_progress[task_id].update({
            "progress": 60,
            "message": "正在转换为PDF格式..."
        })
        
        # 设置输出路径
        output_dir = request.output_path or "output"
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, f"{task_id}.pdf")
        
        # 生成PDF
        pdf_maker = PDFMaker()
        pdf_maker.markdown_to_pdf(
            markdown_content=report_content,
            output_path=pdf_path
        )
        
        # 更新任务完成状态
        task_progress[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": "报告生成完成",
            "pdf_path": pdf_path
        })
        
    except Exception as e:
        # 更新任务失败状态
        task_progress[task_id].update({
            "status": "failed",
            "message": f"报告生成失败: {str(e)}"
        })
        raise

@app.post("/generate-report/")
async def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    task_progress[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "任务已创建",
        "created_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(generate_report_task, task_id, request)
    
    return JSONResponse({
        "task_id": task_id,
        "message": "报告生成任务已启动",
        "status": "pending"
    })

@app.get("/task-progress/{task_id}")
async def get_task_progress(task_id: str):
    if task_id not in task_progress:
        raise HTTPException(status_code=404, detail="任务不存在")
    return JSONResponse(task_progress[task_id])

@app.get("/download-report/{task_id}")
async def download_report(task_id: str):
    if task_id not in task_progress:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = task_progress[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="报告尚未生成完成")
    
    pdf_path = task["pdf_path"]
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF文件不存在")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"舆情分析报告_{task_id}.pdf"
    )

@app.get("/task-list")
async def get_task_list():
    return JSONResponse({
        task_id: {
            "status": task["status"],
            "progress": task.get("progress", 0),
            "message": task.get("message", ""),
            "created_at": task.get("created_at", "")
        }
        for task_id, task in task_progress.items()
    })

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8888,
        reload=True
    )