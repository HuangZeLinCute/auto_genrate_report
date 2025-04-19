# 舆情分析报告生成服务

这是一个基于 FastAPI 的舆情分析报告生成服务，支持异步任务处理和实时进度追踪。

## 功能特点

- 异步报告生成：支持长时间运行的报告生成任务
- 实时进度追踪：提供详细的任务进度和状态更新
- RESTful API：标准的 REST API 接口
- 自动文档：集成 Swagger UI 接口文档
- CORS 支持：支持跨域请求，方便前端集成
- PDF 导出：自动生成 PDF 格式的分析报告

## 安装要求

- Python 3.10+
- FastAPI
- Uvicorn
- 其他依赖项（见 requirements.txt）

## 快速开始

1. 克隆项目并安装依赖：

```bash
git clone <repository_url>
cd public_opinion
pip install -r requirements.txt
```

2. 启动服务：

```bash
python api.py
```

服务将在 http://localhost:8888 上运行。

## API 接口

### 1. 生成报告

```bash
POST /generate-report/
```

请求体示例：
```json
{
    "topic": "舆情问题",
    "start_date": "2024-01-01",
    "end_date": "2024-03-01",
    "output_path": "output"  // 可选
}
```

响应示例：
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "报告生成任务已启动",
    "status": "pending"
}
```

### 2. 查询任务进度

```bash
GET /task-progress/{task_id}
```

响应示例：
```json
{
    "status": "processing",
    "progress": 60,
    "message": "正在转换为PDF格式...",
    "created_at": "2024-03-01T12:00:00"
}
```

### 3. 下载报告

```bash
GET /download-report/{task_id}
```

返回生成的 PDF 文件。

### 4. 查看任务列表

```bash
GET /task-list
```

响应示例：
```json
{
    "task_id_1": {
        "status": "completed",
        "progress": 100,
        "message": "报告生成完成",
        "created_at": "2024-03-01T12:00:00"
    },
    "task_id_2": {
        "status": "processing",
        "progress": 30,
        "message": "正在生成报告内容...",
        "created_at": "2024-03-01T12:05:00"
    }
}
```

## API 文档

访问 http://localhost:8888/docs 查看完整的 API 文档（Swagger UI）。

## 状态说明

任务状态包括：
- `pending`: 等待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 失败

## 错误处理

服务会返回标准的 HTTP 状态码：
- 404: 任务不存在
- 400: 报告未生成完成
- 500: 服务器内部错误

## 注意事项

1. 服务使用内存存储任务状态，重启后状态会丢失
2. 生成的 PDF 文件默认保存在 `output` 目录下
3. 建议在生产环境中使用数据库或 Redis 持久化存储任务状态

## 开发说明

1. 修改配置：
   - 服务端口在 `api.py` 中配置（默认 8888）
   - CORS 设置可在 `api.py` 中的中间件配置修改

2. 开发模式：
   ```bash
   uvicorn api:app --reload --port 8888
   ```