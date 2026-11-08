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

## 6. MySQL 和照片备份与恢复

设备数据保存在 MySQL，照片存放在文件目录。**两个部分都要备份**，并记录属于同一批次的备份；只有数据库无法恢复照片。下面以数据库 `equipment`、目录 `/var/backups/equipment` 为例，请替换为实际环境。以下脚本适用于服务器已安装 MySQL 客户端工具的情况；MySQL 在 Docker 中时，客户端必须能通过容器网络或受控端口连接，不要把数据库端口暴露公网。

### 6.1 准备凭据和目录

准备具有读取目标库、视图、触发器和存储过程所需权限的备份账号；恢复账号还需要对**目标库**具有建表、写入等权限。具体授权以数据库对象及 MySQL 配置为准。建立客户端配置文件 `/etc/equipment-backup.cnf`：

```ini
[client]
user=备份账号
password=替换为自己的密码
host=127.0.0.1
port=3306
```

`[client]` 是 MySQL 客户端共同读取的配置段；`user` 是数据库账号，`password` 是该账号的密码，`host` 和 `port` 是 MySQL 的实际连接地址。使用 `sudo chown root:root /etc/equipment-backup.cnf`、`sudo chmod 600 /etc/equipment-backup.cnf`，不要把此文件提交到 Git。命令中的 `MYSQL_CNF` 只传配置文件路径，不传密码。备份目录应由执行用户写入，确保磁盘容量充足。

### 6.2 手动备份数据库

```bash
cd /opt/equipment-system
export MYSQL_CNF=/etc/equipment-backup.cnf
./deploy/mysql-backup.sh equipment /var/backups/equipment
ls -lh /var/backups/equipment
```

第一个参数 `equipment` 是待备份的数据库名；第二个参数是输出目录。脚本生成 `equipment-时间.sql.gz` 及对应 `.sha256` 文件，时间使用 UTC。脚本执行的核心命令相当于：

```bash
mysqldump --defaults-extra-file="$MYSQL_CNF" --single-transaction --quick --routines --triggers --set-gtid-purged=OFF equipment | gzip -c > backup.sql.gz
```

- `--defaults-extra-file`：从受限文件读取连接和认证配置，必须放在客户端其他选项之前。
- `--single-transaction`：为 InnoDB 表使用一致性事务快照；不能保证非事务表或备份期间 DDL 的一致性。
- `--quick`：逐行读取，降低大表导出时的客户端内存占用。
- `--routines` / `--triggers`：包含存储过程、函数及触发器；账户需要相应权限。
- `--set-gtid-purged=OFF`：不在导出中写入 GTID 设置；如依赖 GTID 的复制或时间点恢复，应另行设计备份策略。
- `equipment`：要导出的数据库；`gzip -c` 压缩输出，`>` 写入文件。脚本使用临时文件、检查压缩完整性后再生成正式文件。

执行后核对：

```bash
# 替换为实际生成的文件名；在校验文件所在目录执行
cd /var/backups/equipment
sha256sum -c equipment-实际时间.sql.gz.sha256
gzip -t equipment-实际时间.sql.gz
```

`sha256sum -c` 检查文件是否与备份时一致；`gzip -t` 检查压缩流是否完整。两者都不等于业务恢复演练。脚本保存的校验文件可能包含调用时传入的输出路径；请确保该路径仍可访问，跨机器复制后可重新比对 `sha256sum` 输出与校验文件中的哈希值。

### 6.3 同批备份照片

以 systemd 部署目录为例，确认 `/var/lib/equipment/uploads` 和 `/var/lib/equipment/private-uploads` 与实际环境变量 `RUOYI_PROFILE`、`EMS_PRIVATE_UPLOAD_DIR` 一致：

```bash
sudo tar -C /var/lib/equipment -czf /var/backups/equipment/photos-批次.tar.gz uploads private-uploads
sudo tar -tzf /var/backups/equipment/photos-批次.tar.gz | head
sudo sha256sum /var/backups/equipment/photos-批次.tar.gz > /var/backups/equipment/photos-批次.tar.gz.sha256
```

`tar -C` 先切换目录、`-c` 创建归档、`-z` gzip 压缩、`-f` 指定文件；`-t` 查看归档目录。数据库和照片分别导出不是原子快照：为确保对应，建议在低峰短暂停止写入后依次备份，或使用支持一致性快照的方案。Docker 部署须确认实际卷名和挂载后备份对应卷；不要误备空的宿主机目录。将同批 SQL、照片归档和校验文件加密保存到另一台可信设备或存储，定期检查容量和恢复效果。

### 6.4 先恢复到隔离库演练

```sql
CREATE DATABASE equipment_restore CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

上面应在隔离 MySQL 实例执行；不要使用正式库名。先准备隔离实例的恢复账号配置文件 `/etc/equipment-restore.cnf`：其中 `host`、`port`、`user` 和 `password` 必须是隔离实例的信息，不能照搬正式库配置。恢复账号需要目标库的建表和写入权限，文件权限同样设为 `600`。然后：

```bash
cd /opt/equipment-system
export MYSQL_CNF=/etc/equipment-restore.cnf
./deploy/mysql-restore.sh /var/backups/equipment/equipment-实际时间.sql.gz equipment_restore
```

第一个参数是 SQL 压缩备份，第二个是**要写入的目标库**。脚本先检查 gzip，并要求手工输入目标库名确认；它不会自动核验 `.sha256`，所以恢复前必须按 6.2 手工核验。脚本内部 `gzip -dc` 解压到标准输出，`mysql --defaults-extra-file=... equipment_restore` 将 SQL 导入目标库。确认目标库账号有足够权限，并检查输出及退出状态。

照片先恢复到单独的空目录，以免覆盖正式文件：

```bash
sudo mkdir -p /var/tmp/equipment-restore-photos
sudo tar -xzf /var/backups/equipment/photos-批次.tar.gz -C /var/tmp/equipment-restore-photos
sudo ls -la /var/tmp/equipment-restore-photos
```

`mkdir -p` 创建目录及必要的上级目录；`tar -xzf` 中 `-x` 为解包、`-z` 为 gzip 解压、`-f` 指定归档文件，`-C` 指定解压目的地；`ls -la` 显示目录内容及权限。确认归档的来源可信、目录内容符合预期后，为隔离应用配置独立 `RUOYI_PROFILE` 和 `EMS_PRIVATE_UPLOAD_DIR`，并确保运行账号有相应访问权限。不要直接覆盖生产照片。用隔离应用抽查设备、工单、人工费、配件费和真实照片能否打开。若从无照片的备份恢复成功，不能据此认定照片恢复已验证。

### 6.5 正式恢复和定时备份

正式恢复是覆盖性操作：先确认目标库、停写并保留当前数据库和照片备份，核对同一批次文件与哈希，再由负责人按隔离演练步骤恢复；完成后验证权限、工单、费用和照片。脚本不会自动回滚已有目标库，也不会创建数据库或恢复照片。

在 `crontab -e` 中添加数据库定时备份示例：

```cron
30 2 * * * MYSQL_CNF=/etc/equipment-backup.cnf /opt/equipment-system/deploy/mysql-backup.sh equipment /var/backups/equipment >> /var/log/equipment-backup.log 2>&1
```

`30 2 * * *` 表示每天服务器本地时间 02:30；`MYSQL_CNF=...` 指定凭据文件；最后两个参数分别是数据库名和输出目录；`>>` 追加日志，`2>&1` 将错误也写入同一日志。执行账号必须能读取凭据、写入备份及日志目录。此任务**只备份 MySQL**，不会备份照片、自动清理旧文件或复制到异地；这些工作需单独安排，定期检查日志并恢复演练。
