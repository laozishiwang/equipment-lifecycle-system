# Linux 部署指南

以下示例适用于已安装 Java 17、Maven、Node.js 22（仅构建前端）、Nginx、MySQL 8 和 Redis 的 Linux 服务器。路径以 `/opt/equipment-system` 为例；先通过系统包管理器或对应官方文档安装这些软件，并检查 `java -version`、`mvn -v`、`node -v`、`mysql --version`、`redis-cli ping`。

## 1. 初始化数据库

创建空数据库和仅授予本库权限的应用账号。密码请在 MySQL 交互终端输入自己的强密码，勿写入仓库或聊天：

```sql
CREATE DATABASE equipment CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'equipment'@'localhost' IDENTIFIED BY '替换为强密码';
GRANT ALL PRIVILEGES ON equipment.* TO 'equipment'@'localhost';
```

使用有建表权限的账号依次导入基础表和业务脚本（仅空库首次初始化；原有数据库应先备份并核对每个已执行的版本）：

```bash
cd /opt/equipment-system
mysql -u root -p equipment < backend/sql/ry_20260417.sql
mysql -u root -p equipment < backend/sql/quartz.sql
for file in database/[0-9][0-9][0-9]_*.sql; do mysql -u root -p equipment < "$file" || break; done
```

执行前检查 SQL，部分脚本包含 `ALTER TABLE`，不可盲目重复运行；按脚本名顺序执行包括 029 和 030 的两份脚本。基础 SQL 中的默认账号必须修改为独立强密码，禁用不需要的账号后才能上线；不要沿用示例密码。MySQL 如在 Docker 中运行，应用账号 host、连接地址和映射端口应与实际网络匹配。

## 2. Redis

启动 Redis 并验证连接；仅监听本机或可信内网。若启用密码，配置应用环境变量 `SPRING_DATA_REDIS_PASSWORD`；Redis 主机和端口分别用 `SPRING_DATA_REDIS_HOST`、`SPRING_DATA_REDIS_PORT`。根据服务安装方式启用持久化并保护密码。

以发行版提供的 Redis 服务为例，先在其配置文件中设置 `bind 127.0.0.1`、`protected-mode yes` 和自己的 `requirepass`，按发行版服务名称执行 `sudo systemctl enable --now redis`。之后用 `redis-cli --askpass ping` 输入密码，预期返回 `PONG`。如果使用 Docker，服务名可能为 `redis` 或实际容器名；不要将 Redis 端口直接暴露到公网。

## 3. 后端构建与 systemd

```bash
cd /opt/equipment-system/backend
mvn -B -DskipTests package
sudo useradd --system --home-dir /opt/equipment-system --shell /sbin/nologin equipment
sudo install -d -o equipment -g equipment /var/lib/equipment/uploads /var/lib/equipment/private-uploads
sudo install -o equipment -g equipment -m 0644 ruoyi-admin/target/ruoyi-admin.jar /opt/equipment-system/app.jar
```

建立 `/etc/equipment-system.env`，仅 root 和服务用户可读，填入真实值。环境变量覆盖 `backend/ruoyi-admin/src/main/resources/application.yml` 与 `application-druid.yml`，不要修改提交到 Git 的配置填密码：

```ini
SPRING_DATASOURCE_DRUID_MASTER_URL=jdbc:mysql://127.0.0.1:3306/equipment?useUnicode=true&characterEncoding=utf8&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai
SPRING_DATASOURCE_DRUID_MASTER_USERNAME=equipment
SPRING_DATASOURCE_DRUID_MASTER_PASSWORD=替换为数据库密码
SPRING_DATA_REDIS_HOST=127.0.0.1
SPRING_DATA_REDIS_PORT=6379
SPRING_DATA_REDIS_PASSWORD=替换为Redis密码
TOKEN_SECRET=替换为随机长密钥
RUOYI_PROFILE=/var/lib/equipment/uploads
EMS_PRIVATE_UPLOAD_DIR=/var/lib/equipment/private-uploads
EMS_PUBLIC_BASE_URL=https://替换为手机可访问的地址
EMS_MONITOR_ENABLED=true
```

无 Redis 密码时去掉 `SPRING_DATA_REDIS_PASSWORD`。`EMS_PUBLIC_BASE_URL` 用于生成二维码；公网使用应配置有效 HTTPS 证书。设置文件权限 `sudo chown root:equipment /etc/equipment-system.env && sudo chmod 640 /etc/equipment-system.env`。

创建 `/etc/systemd/system/equipment-system.service`：

```ini
[Unit]
Description=Equipment management system
After=network.target mysql.service redis.service
[Service]
Type=simple
User=equipment
Group=equipment
WorkingDirectory=/opt/equipment-system
EnvironmentFile=/etc/equipment-system.env
ExecStart=/usr/bin/java -Xms128m -Xmx512m -jar /opt/equipment-system/app.jar
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
```

MySQL/Redis 使用 Docker 时，根据实际服务名调整 `After=`。运行 `sudo systemctl daemon-reload && sudo systemctl enable --now equipment-system`；使用 `systemctl status equipment-system` 和 `journalctl -u equipment-system -f` 检查。

## 4. 前端构建与 Nginx

默认 `frontend/.env.production` 的 `VITE_APP_BASE_API=/prod-api`，同域 Nginx 代理时无需更改；跨域部署要同时配置 API 地址、CORS 与 HTTPS。修改后重新构建：

```bash
cd /opt/equipment-system/frontend
npm install
npm run build:prod
sudo mkdir -p /var/www/equipment
sudo cp -a dist/. /var/www/equipment/
```

Nginx 站点配置示例（HTTPS 证书与 443 配置按实际域名或公网 IP 证书补充）：

```nginx
server {
    listen 80;
    server_name example.com;
    root /var/www/equipment;
    client_max_body_size 20m;
    location / { try_files $uri $uri/ /index.html; }
    location /prod-api/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

执行 `sudo nginx -t && sudo systemctl reload nginx`。通过浏览器测试登录、二维码、手机巡检、报修照片和维修费用。生产 HTTPS 配置须具备客户端信任的证书；手机现场入口在公网可访问时，拿到链接的人可自行填写姓名提交。

## 5. Docker 部署

项目提供 `compose.production.yaml`、`deploy/production.env.example`。复制示例环境文件到不纳入版本控制的本地文件，配置数据库密码、管理员密码哈希、token 和站点地址，检查挂载与初始化脚本后按实际环境执行 `docker compose --env-file ... -f compose.production.yaml up -d --build`。数据库初始化仅首次创建空数据卷时执行；已有卷升级需备份后单独迁移。不要在现有线上直接使用示例配置覆盖实际运行配置。

## 6. 备份与恢复

数据库备份脚本和恢复脚本见 `deploy/`；运行前先阅读脚本参数，确认目标库、备份路径与 MySQL 凭据。**照片不在数据库中**：还需与数据库备份同批保存 `/var/lib/equipment/uploads` 和 `/var/lib/equipment/private-uploads`，Docker 部署则备份对应卷。先在隔离环境恢复并核对图片，勿在生产直接覆盖未备份的数据。生产备份应定期复制到异地并检查可恢复性。


例如先在服务器准备仅自己可读的 MySQL 客户端选项文件 `/etc/equipment-backup.cnf`：

```ini
[client]
user=备份账号
password=替换为密码
host=127.0.0.1
port=3306
```

执行 `sudo chmod 600 /etc/equipment-backup.cnf`，然后以有权读取文件的账号运行：

```bash
export MYSQL_CNF=/etc/equipment-backup.cnf
./deploy/mysql-backup.sh equipment /var/backups/equipment
# 恢复前建立隔离目标库，然后按提示确认目标库名
./deploy/mysql-restore.sh /var/backups/equipment/备份文件.sql.gz equipment_restore
```

恢复会覆盖目标库同名对象和数据，先确认库名及现有备份；请先在隔离库验证。勿将选项文件加入版本库。

可用 root 的 `crontab -e` 安排每日备份，例如：

```cron
30 2 * * * MYSQL_CNF=/etc/equipment-backup.cnf /opt/equipment-system/deploy/mysql-backup.sh equipment /var/backups/equipment >> /var/log/equipment-backup.log 2>&1
```

定时任务的账号必须可读取选项文件并写入目标目录；首次运行后检查日志与生成文件，并按本节要求另行保存照片目录、在隔离库演练恢复。此定时任务只备份 MySQL，不会自动复制到异地。
