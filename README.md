# 解忧信箱

一个治愈系信封风格的卡密兑换页面，附带「反差问答链」功能。用户在电商平台购买兑换码后，来到网站输入兑换码，解锁一封温暖的信，同时可以匿名回答他人问题、留下自己的问题，体验跨年龄的温暖连接。

## 项目结构

```
jieyoupu/
├── backend/
│   ├── main.py              # FastAPI 服务（API + 静态文件）
│   ├── models.py            # SQLAlchemy 数据模型（6 张表）
│   ├── seed.py              # 数据库初始化 + 示例数据 + 种子问题
│   └── requirements.txt     # Python 依赖
├── static/
│   ├── index.html           # 用户端（兑换 + 问答 + 查询回答）
│   └── jieyou.html          # 管理后台（需安全码验证）
├── data/
│   └── jieyoupu.db          # SQLite 数据库
└── .gitignore
```

## 快速开始

```bash
cd backend
pip install -r requirements.txt   # 安装依赖
python seed.py                    # 初始化数据库（写入信件模板 + 示例兑换码 + 57条种子问题）
python main.py                    # 启动服务
```

启动后访问：
- 用户端：http://localhost:8000
- 管理后台：http://localhost:8000/jieyou.html（安全码：`jieyou2026`）
- API 文档：http://localhost:8000/docs

## 核心功能

### 信件兑换
- 用户输入兑换码 → 填写年龄 → 解锁治愈系信件
- 昵称自动生成（兑换码后3位 + "用户"），无需注册登录
- 兑换码一次性使用，重复输入仅提示"已使用过"

### 反差问答链
- 用户兑换信件后，信件下方出现一条随机问题（来自他人或种子库）
- 可选回答该问题，并可留下自己的新问题
- 回答经后台人工审核通过后，提问者通过兑换码查询回答
- 年龄差反差是核心卖点（小学生提问大学生回答等）

### 管理后台
- 安全码验证机制，防止未授权访问
- 信件模板管理、兑换码批量生成与管理
- 问答审核（问题审核 + 回答审核）
- 数据统计概览
- 兑换码一键复制发货文案（符合淘宝虚拟发货规范）

## 示例兑换码

| 兑换码 | 信件 | 说明 |
|---|---|---|
| `XJ-888888` | 今日解忧 | 治愈解忧类 |
| `XJ-666666` | 静心时刻 | 治愈解忧类 |
| `ZF-999999` | 生日祝福 | 生日祝福类 |
| `GL-123456` | 为你加油 | 加油鼓励类 |
| `WA-520131` | 晚安好梦 | 晚安陪伴类 |
| `QS-999999` | 遇见你真好 | 暖心情书类 |

## 数据模型

| 表名 | 说明 |
|---|---|
| `letters` | 信件模板（治愈/晚安/生日/加油/情书等类型） |
| `codes` | 兑换码（active → used / expired） |
| `user_profiles` | 用户档案（兑换码 + 昵称 + 年龄） |
| `questions` | 问题池（种子问题 + 用户提问，7天过期） |
| `answers` | 回答（需审核通过后提问者才可见） |

## API 端点

### 公开接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/redeem` | 兑换码核销，返回信件内容 + 用户档案 |
| GET | `/api/question/random?code=XXX` | 获取随机待回答问题 |
| POST | `/api/answer` | 提交回答 + 可选新问题 |
| POST | `/api/answers/query` | 通过兑换码查询自己问题的回答 |

### 管理接口（需 Bearer Token 鉴权）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/admin/login` | 安全码登录，返回 token |
| GET | `/api/admin/letters` | 信件模板列表 |
| POST | `/api/admin/letters` | 新建信件模板 |
| PUT | `/api/admin/letters/{id}` | 编辑信件模板 |
| DELETE | `/api/admin/letters/{id}` | 删除信件模板 |
| GET | `/api/admin/codes` | 兑换码列表（支持状态/批次筛选 + 分页） |
| POST | `/api/admin/codes/generate` | 批量生成兑换码 |
| DELETE | `/api/admin/codes/{id}` | 删除未使用的兑换码 |
| GET | `/api/admin/stats` | 数据概览 |
| GET | `/api/admin/questions` | 问题列表（支持状态/来源筛选 + 分页） |
| PUT | `/api/admin/questions/{id}/review` | 审核问题（approve / reject） |
| GET | `/api/admin/answers` | 回答列表（支持状态筛选 + 分页） |
| PUT | `/api/admin/answers/{id}/review` | 审核回答（approve / reject） |

## 兑换码生成

在管理后台或通过 API 生成，格式为 `前缀-6位随机码`。

| 信件类型 | 前缀 | 适用场景 |
|---|---|---|
| healing（治愈解忧） | `XJ` | 心情不好、需要安慰 |
| night（晚安陪伴） | `WA` | 睡前读物、每日陪伴 |
| birthday（生日祝福） | `SR` | 送朋友生日祝福 |
| encouragement（加油鼓励） | `GL` | 考试、面试、低谷期 |
| love（暖心情书） | `QS` | 表白、纪念日 |

不同前缀对应不同的商品 SKU，可在电商平台上架不同的商品链接。

## 安全机制

- 管理后台页面更名为 `jieyou.html`，避免默认路径被猜到
- 访问管理后台需输入安全码，验证通过后生成随机 token
- 所有管理 API 通过 `Authorization: Bearer <token>` 鉴权
- Token 失效自动跳回安全码输入页
- 用户提交内容经过基础违规词过滤

## 技术栈

- **前端**：HTML + Tailwind CSS + JavaScript
- **后端**：Python FastAPI
- **数据库**：SQLite（可无缝迁移至 PostgreSQL）
- **ORM**：SQLAlchemy 2.0+

## 部署说明

### 1. 上传项目到服务器

```bash
# 方式一：scp 上传
scp -r ./jieyoupu root@服务器IP:/opt/jieyoupu

# 方式二：git clone（推荐）
ssh root@你的服务器IP
cd /opt
git clone https://github.com/你的用户名/jieyoupu.git
cd jieyoupu
```

### 2. 安装 Py 依赖

```bash
cd /opt/jieyoupu/backend
pip3 install -r requirements.txt
```

### 3. 初始化数据库

```bash
python3 seed.py
```

### 4. 使用 Systemd 管理服务

创建服务文件：

```bash
sudo nano /etc/systemd/system/jieyoupu.service
```

写入以下内容：

```ini
[Unit]
Description=Jieyou Xinxiang API
After=network.target

[Service]
WorkingDirectory=/opt/jieyoupu/backend
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

启动前后端服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start jieyoupu
sudo systemctl enable jieyoupu    # 开机自启

# 查看运行状态
sudo systemctl status jieyoupu

# 查看日志
sudo journalctl -u jieyoupu -f
```

### 5. 配置 Nginx 反向代理

```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/jieyoupu
```

写入以下内容（将 `jieyouci.com` 替换为你的域名）：

```nginx
server {
    listen 80;
    server_name jieyouci.com www.jieyouci.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/jieyoupu /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. 配置 HTTPS

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d jieyouci.com -d www.jieyouci.com
```

Certbot 会自动配置 SSL 证书和 Nginx，证书到期前自动续期

### 7. 验证部署

```bash
# 检查服务是否正常
curl http://127.0.0.1:8000/docs

# 浏览器访问
用户端：https://jieyouci.com
管理后台：https://jieyouci.com/jieyou.html
```

### 常见运维操作

```bash
# 更新代码后重启服务
cd /opt/jieyoupu && git pull
sudo systemctl restart jieyoupu

# 重新初始化数据库（会清空数据，谨慎操作）
cd /opt/jieyoupu/backend
rm ../data/jieyoupu.db
python3 seed.py
sudo systemctl restart jieyoupu

# 修改管理员安全码：编辑 backend/main.py 中的 ADMIN_PASSWORD
# 修改后需重启服务
sudo systemctl restart jieyoupu
```
