# 冻结候选发布与回滚（准备稿）

此流程仅适用于已完成数据库结构兼容核验、候选镜像和业务回归、备份校验之后；部门范围仍保持关闭。先以实际运行镜像 ID 核对回滚标签，不能用较早的历史标签替代。不要执行 MySQL 初始化脚本或删除数据卷。

在服务器 `/opt/equipment-rebuild` 创建仅含镜像指定的 Compose 覆盖文件（不包含凭据）：

```yaml
services:
  backend:
    image: equipment-frozen-verification-backend:20261106
  frontend:
    image: equipment-frozen-verification-frontend:20261106
```

使用与现有线上进程相同的 Compose 项目名、环境文件、基础配置和覆盖配置，并额外加入此文件；所有命令在项目目录执行。先通过 `docker image inspect` 和 `docker inspect equipment-live-backend-1 equipment-live-frontend-1` 核对候选 ID、当前容器镜像 ID、回滚标签 ID，以及冻结的 nginx 配置。使用 `docker compose ... config --images` 检查选择的镜像；不要输出完整 config（其中可能包含密码）。检查近期生产备份的清单并验证校验和。发布只重建 backend 和 frontend，使用 `up -d --no-deps --no-build backend frontend`，避免重建源码或重启 MySQL、Redis、网关。服务重建后等待后端 API 可用，再检查 HTTPS、验证码和容器状态，记录实际镜像 ID。若健康检查失败立即回滚。

回滚时将覆盖文件的两个 image 分别改为 `equipment-live-backend:rollback-current-20261106` 和 `equipment-live-frontend:rollback-current-20261106`，核对其 ID 与发布前记录一致后，使用相同 Compose 配置执行 `up -d --no-deps --no-build backend frontend`，再检查 API、HTTPS 和镜像 ID。此操作不恢复数据库；本候选若涉及数据库变更，必须先另行制定数据兼容和恢复方案。本准备稿没有执行线上切换。

例如将上述文件命名为 `deploy/compose.frozen-release.yaml`，检查与切换命令为：

```bash
cd /opt/equipment-rebuild
docker compose -p equipment-live --env-file .env.production -f compose.production.yaml -f deploy/compose.live.yaml -f deploy/compose.frozen-release.yaml config --images
docker compose -p equipment-live --env-file .env.production -f compose.production.yaml -f deploy/compose.live.yaml -f deploy/compose.frozen-release.yaml up -d --no-deps --no-build backend frontend
```

执行前必须再次核实候选标签映射、`.env.production` 与当前容器所用一致、配置与初始化数据库兼容。Compose 参数和标签为当前已知配置，并非已经在生产执行的命令。

## 2026-11-06 上线后运维

当前生产前后端 `equipment-live-*:latest` 已对齐运行镜像；旧版仍以 `rollback-current-20261106` 保留。日常操作仍应使用 `deploy/compose.frozen-release.yaml` 覆盖文件及 `--no-build`，避免 `--build` 重新构建并覆盖已验收的产物。标签调整不会重启容器。
