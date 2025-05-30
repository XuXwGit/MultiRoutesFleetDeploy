# 智慧航运物流优化系统前端

这是一个基于Python Flask的智慧航运物流优化系统前端界面。

## 功能特点

- 船舶列表显示
- 实时调度状态监控
- 数据可视化展示
- 响应式设计

## 安装说明

1. 确保已安装Python 3.7或更高版本
2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

## 运行说明

1. 在项目根目录下运行：
   ```bash
   python app.py
   ```
2. 打开浏览器访问：http://localhost:5000

## 项目结构

```
src_ui/
├── app.py              # Flask应用主文件
├── static/             # 静态文件目录
│   ├── css/           # CSS样式文件
│   └── js/            # JavaScript文件
├── templates/          # HTML模板目录
└── requirements.txt    # Python依赖文件
```

## 开发说明

- 前端使用Bootstrap 5框架
- 数据可视化使用ECharts
- 后端使用Flask框架 