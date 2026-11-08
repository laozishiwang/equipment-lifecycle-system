# 冻结产物镜像构建

使用已验证的冻结构建输出建立两个独立目录：后端目录含 `ruoyi-admin.jar` 和 `backend.frozen.Dockerfile`；前端目录含 `dist/`、生产预期 `nginx.conf` 和 `frontend.frozen.Dockerfile`。分别以各自目录为构建上下文，执行 `docker build -f backend.frozen.Dockerfile -t <后端候选标签> .` 和 `docker build -f frontend.frozen.Dockerfile -t <前端候选标签> .`。构建不安装依赖或重新编译，构建后对镜像内 JAR 与 dist 逐文件核对哈希，并使用隔离数据库完成镜像级业务测试，再考虑发布。

2026-11-06 隔离验证：后端镜像 `equipment-frozen-verification-backend:20261106` 的 JAR SHA256 为 `1c2e452ce988ec8e787940605770ee4c69f7b51659df7e82376d3172886c6dc5`；前端镜像 `equipment-frozen-verification-frontend:20261106` 的 dist 文件哈希一致，基础 nginx 镜像额外包含默认 `50x.html`。镜像尚未经过完整业务测试，未部署生产。前端 nginx.conf 取自隔离目录，不是冻结源码包内经单独验证的配置，发布前须冻结并核对配置。

2026-11-06 配置核验：候选镜像与运行中的生产前端 `/etc/nginx/conf.d/default.conf` SHA-256 均为 `6e3ebb1a67be04fffff5a08073660eaa5719f6ccf30eb4fb4d5da0f4194ffbed`；在可解析 backend 的容器网络中执行候选镜像 `nginx -t` 通过。配置随候选镜像固定，业务端到端测试仍需单独完成。
