// 通用工具函数
const utils = {
        // 格式化日期
        formatDate(date) {
                return new Date(date).toLocaleDateString('zh-CN');
        },

        // 格式化数字
        formatNumber(num) {
                return new Intl.NumberFormat('zh-CN').format(num);
        },

        // 显示提示消息
        showToast(message, type = 'info') {
                const toast = document.createElement('div');
                toast.className = `toast align-items-center text-white bg-${type} border-0`;
                toast.setAttribute('role', 'alert');
                toast.setAttribute('aria-live', 'assertive');
                toast.setAttribute('aria-atomic', 'true');

                toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

                document.body.appendChild(toast);
                const bsToast = new bootstrap.Toast(toast);
                bsToast.show();

                toast.addEventListener('hidden.bs.toast', () => {
                        document.body.removeChild(toast);
                });
        },

        // 处理API错误
        handleApiError(error) {
                console.error('API Error:', error);
                this.showToast(error.message || '操作失败，请稍后重试', 'danger');
        }
};

// 数据管理相关函数
const dataManager = {
        // 导入数据
        async importData(formData) {
                try {
                        const response = await fetch('/api/import', {
                                method: 'POST',
                                body: formData
                        });

                        if (!response.ok) {
                                throw new Error('导入失败');
                        }

                        const result = await response.json();
                        utils.showToast('数据导入成功', 'success');
                        return result;
                } catch (error) {
                        utils.handleApiError(error);
                        throw error;
                }
        },

        // 导出数据
        async exportData(type, format) {
                try {
                        const response = await fetch(`/api/export?type=${type}&format=${format}`);

                        if (!response.ok) {
                                throw new Error('导出失败');
                        }

                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `${type}_${new Date().getTime()}.${format}`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);

                        utils.showToast('数据导出成功', 'success');
                } catch (error) {
                        utils.handleApiError(error);
                        throw error;
                }
        }
};

// 图表相关函数
const chartManager = {
        // 初始化图表
        initChart(container, options) {
                const chart = echarts.init(document.getElementById(container));
                chart.setOption(options);
                return chart;
        },

        // 更新图表数据
        updateChart(chart, newData) {
                chart.setOption(newData);
        },

        // 响应式调整
        handleResize(chart) {
                window.addEventListener('resize', () => {
                        chart.resize();
                });
        }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
        // 初始化所有工具提示
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // 初始化所有弹出框
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
                return new bootstrap.Popover(popoverTriggerEl);
        });
});

// 初始化图表实例（加判断，防止首页报错）
let scheduleChart = null,
        statusChart = null,
        mapChart = null;
if (document.getElementById('scheduleChart')) {
        scheduleChart = echarts.init(document.getElementById('scheduleChart'));
}
if (document.getElementById('statusChart')) {
        statusChart = echarts.init(document.getElementById('statusChart'));
}
if (document.getElementById('mapContainer')) {
        mapChart = echarts.init(document.getElementById('mapContainer'));
}

// 加载船舶数据
async function loadShips() {
        try {
                const response = await fetch('/api/ships');
                const ships = await response.json();
                const shipsList = document.getElementById('shipsList');
                shipsList.innerHTML = '';
                ships.forEach(ship => {
                        const shipCard = document.createElement('div');
                        shipCard.className = 'col-12';
                        shipCard.innerHTML = `
                <div class="card">
                    <div class="card-body d-flex align-items-center">
                        <i class="bi bi-truck-front-fill fs-3 text-primary me-3"></i>
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="fw-bold">${ship.name}</span>
                                <span class="badge bg-${ship.status === '在航' ? 'success' : 'secondary'}">${ship.status}</span>
                            </div>
                            <div class="small text-muted">类型: ${ship.type} &nbsp;|&nbsp; 当前港口: ${ship.current_port}</div>
                        </div>
                    </div>
                </div>
            `;
                        shipsList.appendChild(shipCard);
                });
        } catch (error) {
                console.error('加载船舶数据失败:', error);
        }
}

// 更新图表
function updateCharts(data) {
        // 调度图表配置
        const scheduleOption = {
                title: {
                        text: '船舶调度时间表'
                },
                tooltip: {
                        trigger: 'axis'
                },
                xAxis: {
                        type: 'time'
                },
                yAxis: {
                        type: 'category',
                        data: data.map(ship => ship.name)
                },
                series: [{
                        name: 'ETA',
                        type: 'scatter',
                        data: data.map(ship => [new Date(ship.eta), ship.name])
                }]
        };

        // 状态图表配置
        const statusOption = {
                title: {
                        text: '船舶状态分布'
                },
                tooltip: {
                        trigger: 'item'
                },
                series: [{
                        name: '船舶状态',
                        type: 'pie',
                        radius: '50%',
                        data: [{
                                        value: data.filter(ship => ship.status === '在航').length,
                                        name: '在航'
                                },
                                {
                                        value: data.filter(ship => ship.status === '停泊').length,
                                        name: '停泊'
                                }
                        ]
                }]
        };

        if (scheduleChart) scheduleChart.setOption(scheduleOption);
        if (statusChart) statusChart.setOption(statusOption);
}

// 地图初始化
function initMap(data) {
        const mapOption = {
                title: {
                        text: '船舶地理分布'
                },
                tooltip: {
                        trigger: 'item',
                        formatter: '{b}: {c}'
                },
                geo: {
                        map: 'china',
                        roam: true,
                        label: {
                                show: true
                        },
                        itemStyle: {
                                areaColor: '#eee',
                                borderColor: '#0571c2'
                        },
                        emphasis: {
                                itemStyle: {
                                        areaColor: '#cdd0d5'
                                }
                        }
                },
                series: [{
                        type: 'scatter',
                        coordinateSystem: 'geo',
                        data: [],
                        symbolSize: 15,
                        label: {
                                show: false
                        },
                        itemStyle: {
                                color: '#0571c2'
                        }
                }]
        };

        if (mapChart) mapChart.setOption(mapOption);
}

// 船舶详情功能
function showShipDetail(ship) {
        // 设置模态框标题
        document.getElementById('shipDetailModalLabel').textContent = `船舶详情: ${ship.name}`;

        // 填充基本信息表格
        const detailTable = document.getElementById('shipDetailTable');
        detailTable.innerHTML = `
            <tr><th>船舶ID</th><td>${ship.id}</td></tr>
            <tr><th>船舶类型</th><td>${ship.type}</td></tr>
            <tr><th>载重量</th><td>${ship.capacity} 吨</td></tr>
            <tr><th>当前状态</th><td>${ship.status}</td></tr>
            <tr><th>当前港口</th><td>${ship.current_port}</td></tr>
            <tr><th>下一港口</th><td>${ship.next_port}</td></tr>
            <tr><th>预计到达时间</th><td>${ship.eta}</td></tr>
        `;

        // 初始化状态图表
        const statusChart = echarts.init(document.getElementById('shipStatusChart'));
        const statusOption = {
                series: [{
                        type: 'gauge',
                        detail: {
                                formatter: '{value}%'
                        },
                        data: [{
                                value: Math.round(Math.random() * 100),
                                name: '任务完成率'
                        }]
                }]
        };
        statusChart.setOption(statusOption);

        // 初始化航线图表
        const routeChart = echarts.init(document.getElementById('shipRouteChart'));
        const routeOption = {
                title: {
                        text: '历史航线'
                },
                tooltip: {
                        trigger: 'axis'
                },
                xAxis: {
                        type: 'category',
                        data: ['1月', '2月', '3月', '4月', '5月']
                },
                yAxis: {
                        type: 'value'
                },
                series: [{
                        data: [820, 932, 901, 934, 1290],
                        type: 'line',
                        smooth: true
                }]
        };
        routeChart.setOption(routeOption);

        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('shipDetailModal'));
        modal.show();
}

// 加载航线列表
async function loadRoutes() {
        try {
                const response = await fetch('/api/routes');
                const routes = await response.json();
                const routesList = document.getElementById('routesList');
                routesList.innerHTML = '';
                routes.forEach(route => {
                        const routeCard = document.createElement('div');
                        routeCard.className = 'col-12';
                        routeCard.innerHTML = `
                <div class="card">
                    <div class="card-body d-flex align-items-center">
                        <i class="bi bi-signpost-split fs-3 text-warning me-3"></i>
                        <div class="flex-grow-1">
                            <div class="fw-bold">航线${route.id}</div>
                            <div class="small text-muted">经停港口数: ${route.number_of_ports}<br>港口: ${route.ports}<br>挂靠次数: ${route.number_of_calls}</div>
                        </div>
                    </div>
                </div>
            `;
                        routesList.appendChild(routeCard);
                });
        } catch (error) {
                console.error('加载航线数据失败:', error);
        }
}

// 新增统一网络拓扑图绘制函数
async function drawNetworkTopology() {
        const networkTopologyDiv = document.getElementById('network-topology');
        if (!networkTopologyDiv) return;
        try {
                const response = await fetch('/api/network');
                const networkData = await response.json();
                if (networkData.status !== 'success') return;

                const chart = echarts.init(networkTopologyDiv);
                const option = {
                        title: {
                                text: '航线网络拓扑',
                                subtext: '基于当前航线数据',
                                top: 'top',
                                left: 'center'
                        },
                        tooltip: {
                                trigger: 'item',
                                formatter: function (params) {
                                        if (params.dataType === 'edge') {
                                                return `航线: ${params.data.legendName}<br />航段: ${params.data.source} → ${params.data.target}`;
                                        }
                                        return `港口: ${params.data.name}`;
                                }
                        },
                        legend: {
                                data: networkData.legend.map(item => item.name),
                                orient: 'vertical',
                                left: 'left',
                                top: 'middle'
                        },
                        animationDuration: 1500,
                        animationEasingUpdate: 'quinticInOut',
                        series: [{
                                name: '航线网络',
                                type: 'graph',
                                layout: 'force',
                                data: networkData.nodes,
                                links: networkData.links,
                                categories: [{
                                        name: '港口'
                                }],
                                roam: true,
                                label: {
                                        show: true,
                                        position: 'right',
                                        formatter: '{b}',
                                        fontSize: 12,
                                        backgroundColor: 'rgba(255,255,255,0.7)',
                                        padding: [4, 8],
                                        borderRadius: 4
                                },
                                force: {
                                        repulsion: 200,
                                        edgeLength: [100, 200],
                                        gravity: 0.1
                                },
                                edgeSymbol: ['none', 'arrow'],
                                edgeSymbolSize: [0, 8],
                                lineStyle: {
                                        width: 3,
                                        opacity: 0.8,
                                        curveness: 0.2
                                },
                                emphasis: {
                                        focus: 'adjacency',
                                        lineStyle: {
                                                width: 5
                                        }
                                }
                        }]
                };
                chart.setOption(option);
        } catch (error) {
                console.error('加载航线网络拓扑图失败:', error);
        }
}

// 页面加载时自动调用
document.addEventListener('DOMContentLoaded', function () {
        loadShips();
        loadRoutes();
        drawNetworkTopology();

        // 监听窗口大小变化，调整图表大小
        window.addEventListener('resize', () => {
                if (scheduleChart) scheduleChart.resize();
                if (statusChart) statusChart.resize();
                if (mapChart) mapChart.resize();
        });

        // 导入按钮事件
        const importBtn = document.getElementById('importBtn');
        if (importBtn) {
                importBtn.addEventListener('click', () => {
                                        const dataType = document.getElementById('dataType').value;
                                        const fileInput = document.getElementById('dataFile');

                        if (fileInput.files.length === 0) {
                                alert('请选择文件');
                                return;
                        }

                        const file = fileInput.files[0];
                        const reader = new FileReader();

                        reader.onload = function (e) {
                                        let data;
                                        try {
                                                // 假设文件是JSON格式
                                                data = JSON.parse(e.target.result);

                                        // 发送到服务器
                                        fetch(`/api/import/${dataType}`, {
                                                        method: 'POST',
                                                        headers: {
                                                                'Content-Type': 'application/json'
                                                        },
                                                        body: JSON.stringify(data)
                                                })
                                                .then(response => response.json())
                                                .then(result => {
                                                        alert(`导入成功: ${result.message}`);
                                                        loadShips(); // 重新加载数据
                                                })
                                                .catch(error => {
                                                        alert('导入失败: ' + error);
                                                });
                                        } catch (error) {
                                                alert('文件格式错误: ' + error);
                                        }
                                        };

                        reader.readAsText(file);
                        });
        }

        // 导出按钮事件
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
                exportBtn.addEventListener('click', () => {
                                        const exportType = document.getElementById('exportType').value;
                                        const exportFormat = document.getElementById('exportFormat').value;

                        fetch(`/api/export/${exportType}?format=${exportFormat}`)
                                .then(response => response.blob())
                                .then(blob => {
                                        const url = window.URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.style.display = 'none';
                                        a.href = url;
                                        a.download = `${exportType}_data.${exportFormat}`;
                                        document.body.appendChild(a);
                                        a.click();
                                        window.URL.revokeObjectURL(url);
                                })
                                .catch(error => {
                                        alert('导出失败: ' + error);
                                });
                        });
        }

        // 初始化航线规划地图
        const routeMap = echarts.init(document.getElementById('routeMapContainer'));

        // 规划航线按钮点击事件
        const planRouteBtn = document.getElementById('planRouteBtn');
        if (planRouteBtn) {
                planRouteBtn.addEventListener('click', () => {
                                        const startPort = document.getElementById('startPort').value;
                                        const endPort = document.getElementById('endPort').value;
                                        const optimizeGoal = document.getElementById('optimizeGoal').value;

                        // 模拟请求后端规划航线
                        fetch('/api/plan-route', {
                                        method: 'POST',
                                        headers: {
                                                'Content-Type': 'application/json'
                                        },
                                        body: JSON.stringify({
                                                startPort,
                                                endPort,
                                                optimizeGoal
                                        })
                                })
                                .then(response => response.json())
                                .then(data => {
                                        // 显示航线结果
                                        const routeOption = {
                                                title: {
                                                        text: '规划航线'
                                                },
                                                tooltip: {
                                                        trigger: 'item',
                                                },
                                                geo: {
                                                        map: 'china',
                                                        roam: true,
                                                        label: {
                                                                show: true
                                                        },
                                                        itemStyle: {
                                                                areaColor: '#eee',
                                                                borderColor: '#0571c2'
                                                        }
                                                },
                                                series: [{
                                                        type: 'lines',
                                                        coordinateSystem: 'geo',
                                                        data: [{
                                                                coords: [
                                                                        [121.48, 31.22], // 上海
                                                                        [113.23, 23.16] // 广州
                                                                ],
                                                                lineStyle: {
                                                                        width: 3,
                                                                        color: '#ff0000'
                                                                }
                                                        }],
                                                        symbol: ['none', 'arrow'],
                                                        symbolSize: 8
                                                }]
                                        };
                                        routeMap.setOption(routeOption);
                                })
                                .catch(error => {
                                        console.error('规划航线失败:', error);
                                        alert('规划航线失败，请稍后重试');
                                });
                        });
        }

        // 初始化优化结果图表
        const optimizeChart = echarts.init(document.getElementById('optimizeResultChart'));

        // 优化按钮点击事件
        const optimizeBtn = document.getElementById('optimizeBtn');
        if (optimizeBtn) {
                optimizeBtn.addEventListener('click', () => {
                                        const algorithm = document.getElementById('algorithm').value;
                                        const timeGoal = document.getElementById('goal_time').checked;
                                        const costGoal = document.getElementById('goal_cost').checked;
                                        const emissionsGoal = document.getElementById('goal_emissions').checked;
                                        const scope = document.getElementById('scope').value;

                        // 显示加载中
                        optimizeBtn.disabled = true;
                        optimizeBtn.textContent = '优化中...';

                        // 模拟优化过程
                        setTimeout(() => {
                                                // 更新优化进度图表
                                                const optimizeOption = {
                                                        title: {
                                                                text: '优化结果对比'
                                                        },
                                                        tooltip: {
                                                                trigger: 'axis'
                                                        },
                                                        legend: {
                                                                data: ['原计划', '优化后']
                                                        },
                                                        radar: {
                                                                indicator: [{
                                                                                name: '时间',
                                                                                max: 100
                                                                        },
                                                                        {
                                                                                name: '成本',
                                                                                max: 100
                                                                        },
                                                                        {
                                                                                name: '资源利用率',
                                                                                max: 100
                                                                        },
                                                                        {
                                                                                name: '碳排放',
                                                                                max: 100
                                                                        },
                                                                        {
                                                                                name: '港口拥堵',
                                                                                max: 100
                                                                        }
                                                                ]
                                                        },
                                                        series: [{
                                                                type: 'radar',
                                                                data: [{
                                                                                value: [70, 65, 55, 80, 60],
                                                                                name: '原计划'
                                                                        },
                                                                        {
                                                                                value: [90, 80, 75, 60, 85],
                                                                                name: '优化后'
                                                                        }
                                                                ]
                                                        }]
                                                };
                                                optimizeChart.setOption(optimizeOption);

                                // 填充调度表格
                                const scheduleTable = document.getElementById('scheduleTable').getElementsByTagName('tbody')[0];
                                scheduleTable.innerHTML = '';

                                const scheduleData = [{
                                                ship: '远洋之星',
                                                from: '上海港',
                                                to: '新加坡港',
                                                departTime: '2024-05-18 10:00',
                                                arriveTime: '2024-05-25 08:00'
                                        },
                                        {
                                                ship: '海洋号',
                                                from: '广州港',
                                                to: '迪拜港',
                                                departTime: '2024-05-20 14:00',
                                                arriveTime: '2024-05-30 17:30'
                                        },
                                        {
                                                ship: '星辰号',
                                                from: '青岛港',
                                                to: '釜山港',
                                                departTime: '2024-05-19 08:30',
                                                arriveTime: '2024-05-21 12:00'
                                        }
                                ];

                                scheduleData.forEach(item => {
                                                        const row = scheduleTable.insertRow();
                                                        row.innerHTML = `
                    <td>${item.ship}</td>
                    <td>${item.from}</td>
                    <td>${item.to}</td>
                    <td>${item.departTime}</td>
                    <td>${item.arriveTime}</td>
                `;
                                });

                                // 恢复按钮状态
                                optimizeBtn.disabled = false;
                                optimizeBtn.textContent = '开始优化';

                                // 显示成功消息
                                alert('调度优化完成');
                                }, 2000);
                                });
        }

        // 运行算法
        const runBtn = document.getElementById('run-button');
        if (runBtn) {
                runBtn.addEventListener('click', runAlgorithm);
        }
});
// 运行算法
function runAlgorithm() {
        // 收集所有参数
        const algorithmParams = {
                time_horizon: parseInt(document.getElementById('time_horizon').value) || 30,
                algorithm: document.getElementById('algorithm').value || 'bd',
                use_db: document.getElementById('use_db').checked,
                db_path: document.getElementById('db_path').value || 'ships.db',
                max_iter: parseInt(document.getElementById('max_iter').value) || 100,
                max_time: parseInt(document.getElementById('max_time').value) || 600,
                mip_gap: parseFloat(document.getElementById('mip_gap').value) || 0.01,
                robustness: parseFloat(document.getElementById('robustness').value) || 1.0,
                demand_fluctuation: parseFloat(document.getElementById('demand_fluctuation').value) || 0.1,
                empty_rent_cost: parseFloat(document.getElementById('empty_rent_cost').value) || 10,
                penalty_coeff: parseFloat(document.getElementById('penalty_coeff').value) || 100,
                port_load_cost: parseFloat(document.getElementById('port_load_cost').value) || 5,
                port_unload_cost: parseFloat(document.getElementById('port_unload_cost').value) || 5,
                port_transship_cost: parseFloat(document.getElementById('port_transship_cost').value) || 8,
                laden_stay_cost: parseFloat(document.getElementById('laden_stay_cost').value) || 2,
                laden_stay_free_time: parseInt(document.getElementById('laden_stay_free_time').value) || 3,
                empty_stay_cost: parseFloat(document.getElementById('empty_stay_cost').value) || 1,
                empty_stay_free_time: parseInt(document.getElementById('empty_stay_free_time').value) || 3
        };

        // 显示加载状态
        const runButton = document.getElementById('run-button');
        const originalText = runButton.textContent;
        runButton.disabled = true;
        runButton.textContent = '运行中...';

        // 发送请求
        fetch('/api/run_algorithm', {
                        method: 'POST',
                        headers: {
                                'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                                algorithm_params: algorithmParams
                        })
                })
                .then(response => response.json())
                .then(data => {
                        if (data.status === 'success') {
                                // 显示成功消息
                                showMessage('算法执行成功', 'success');
                                // 更新结果显示
                                updateResults(data.output);
                        } else {
                                // 显示错误消息
                                showMessage(`算法执行失败: ${data.error || data.message}`, 'error');
                        }
                })
                .catch(error => {
                        showMessage(`请求失败: ${error.message}`, 'error');
                })
                .finally(() => {
                        // 恢复按钮状态
                        runButton.disabled = false;
                        runButton.textContent = originalText;
                });
}

// 显示消息
function showMessage(message, type = 'info') {
        const messageDiv = document.getElementById('message');
        messageDiv.textContent = message;
        messageDiv.className = `alert alert-${type}`;
        messageDiv.style.display = 'block';

        // 3秒后自动隐藏
        setTimeout(() => {
                messageDiv.style.display = 'none';
        }, 3000);
}

// 更新结果显示
function updateResults(output) {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = `<pre>${output}</pre>`;
}