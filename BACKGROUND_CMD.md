# BACKGROUND_CMD - 后台进程管理工具

## ⚠️ 重要使用说明

**CRITICAL: 此工具必须在前台模式运行**

- 在 Cursor AI 中使用时，必须设置 `is_background=false`
- 不要在后台终端中运行此工具，会导致终端冲突和测试失败
- 此工具本身用于管理其他后台进程，但自身必须在前台执行

## 概述

BACKGROUND_CMD 是一个安全的后台进程管理工具，专为解决 Cursor IDE 和其他开发环境中的 `posix_spawnp failed` 错误而设计。它提供了创建、监控和管理后台进程的完整解决方案，防止系统资源耗尽。

## 主要特性

- 🚀 **安全的进程创建**: 使用独立会话组，防止信号传播
- 🔄 **自动清理机制**: 自动检测和清理已死亡的进程
- 📊 **实时监控**: 监控进程状态、CPU和内存使用情况
- 🐚 **多Shell支持**: 支持 zsh 和 bash shell
- 📝 **日志管理**: 自动创建和管理进程日志文件
- ⚡ **别名解析**: 自动解析shell别名
- 🎯 **进程限制**: 可配置的最大进程数限制（默认1000）
- 💾 **状态持久化**: 进程状态在工具重启后保持

## 安装

### 依赖要求

```bash
pip install psutil
```

### 文件权限

确保脚本具有执行权限：

```bash
chmod +x ~/.local/bin/BACKGROUND_CMD.py
chmod +x ~/.local/bin/BACKGROUND_CMD.sh
```

## 使用方法

### 基本命令

```bash
# 创建后台进程（使用默认zsh）
BACKGROUND_CMD "sleep 60"

# 使用bash shell
BACKGROUND_CMD "ls -la" --shell bash

# 列出所有活跃进程
BACKGROUND_CMD --list

# 终止指定进程
BACKGROUND_CMD --kill 12345

# 强制终止进程
BACKGROUND_CMD --force-kill 12345

# 清理所有进程
BACKGROUND_CMD --cleanup
```

### 快捷命令（通过 .sh 脚本）

```bash
# 列出进程的快捷方式
BACKGROUND_CMD list
BACKGROUND_CMD ls
BACKGROUND_CMD ps

# 清理进程的快捷方式
BACKGROUND_CMD clean
BACKGROUND_CMD cleanup

# 终止进程的快捷方式
BACKGROUND_CMD kill 12345
BACKGROUND_CMD fkill 12345  # 强制终止

# 查看日志
BACKGROUND_CMD logs
BACKGROUND_CMD log tail 12345  # 实时查看指定PID的日志
```

### 高级选项

```bash
# 设置最大进程数
BACKGROUND_CMD "command" --max-processes 500

# 自定义日志目录
BACKGROUND_CMD "command" --log-dir ~/my_logs

# 不解析shell别名
BACKGROUND_CMD "command" --no-alias

# JSON输出格式
BACKGROUND_CMD --list --json
```

## 配置

### 环境变量

可以通过环境变量设置默认值：

```bash
export BACKGROUND_CMD_LOG_DIR="~/tmp/background_cmd_logs"
export BACKGROUND_CMD_MAX_PROCESSES="1000"
export BACKGROUND_CMD_DEFAULT_SHELL="zsh"
```

### 日志文件

- **默认位置**: `~/tmp/background_cmd_logs/`
- **命名格式**: `bg_cmd_YYYYMMDD_HHMMSS_mmm.log`
- **内容**: 包含进程的标准输出和标准错误

## 工作原理

### 进程隔离

BACKGROUND_CMD 使用 `os.setsid()` 创建新的会话组，确保：
- 后台进程不会被父进程的信号影响
- 避免终端关闭时进程被意外终止
- 防止 Ctrl+C 等信号传播到子进程

### 进程跟踪

工具使用以下机制跟踪进程：
- **PID + 创建时间**: 防止PID重用问题
- **psutil监控**: 实时获取进程状态和资源使用
- **状态持久化**: 将进程信息保存到JSON文件

### 自动清理

定期执行清理操作：
- 检查进程是否仍然存在
- 验证PID和创建时间匹配
- 移除已死亡进程的记录
- 清理空的日志文件

## 示例用法

### 开发场景

```bash
# 启动开发服务器
BACKGROUND_CMD "npm start" --shell bash

# 运行测试套件
BACKGROUND_CMD "pytest tests/" --shell zsh

# 启动数据库
BACKGROUND_CMD "mongod --dbpath ./data"

# 监控文件变化
BACKGROUND_CMD "fswatch . | grep -E '\\.(py|js)$'"
```

### 系统维护

```bash
# 定期备份
BACKGROUND_CMD "rsync -av /home/user/ /backup/"

# 日志监控
BACKGROUND_CMD "tail -f /var/log/system.log"

# 网络监控
BACKGROUND_CMD "ping -i 60 google.com"
```

### 批量任务

```bash
# 批量图片处理
for img in *.jpg; do
    BACKGROUND_CMD "convert $img -resize 800x600 resized_$img"
done

# 查看所有任务状态
BACKGROUND_CMD --list
```

## 故障排除

### 常见问题

1. **posix_spawnp failed 错误**
   - 原因: 系统资源耗尽或进程数达到限制
   - 解决: 使用 `BACKGROUND_CMD --cleanup` 清理僵尸进程

2. **进程无法启动**
   - 检查shell类型是否正确
   - 确认命令语法是否有效
   - 查看日志文件获取详细错误信息

3. **日志文件找不到**
   - 确认日志目录权限
   - 检查磁盘空间是否充足

### 调试模式

```bash
# 查看详细进程信息
BACKGROUND_CMD --list

# 检查特定进程的日志
BACKGROUND_CMD log tail 12345

# JSON格式输出便于调试
BACKGROUND_CMD --list --json
```

## API 参考

### 命令行参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `command` | string | - | 要执行的命令 |
| `--shell` | choice | zsh | Shell类型 (zsh/bash) |
| `--max-processes` | int | 1000 | 最大进程数 |
| `--log-dir` | string | ~/tmp/background_cmd_logs | 日志目录 |
| `--no-alias` | flag | false | 不解析别名 |
| `--list` | flag | false | 列出进程 |
| `--kill` | int | - | 终止进程PID |
| `--force-kill` | int | - | 强制终止PID |
| `--cleanup` | flag | false | 清理所有进程 |
| `--json` | flag | false | JSON输出 |

### JSON 输出格式

#### 进程列表
```json
{
  "success": true,
  "processes": [
    {
      "pid": 12345,
      "command": "sleep 60",
      "shell": "zsh",
      "status": "sleeping",
      "cpu_percent": 0.0,
      "memory_mb": 2.1,
      "runtime": "0:05:30",
      "log_file": "/path/to/log.log",
      "cwd": "/current/directory"
    }
  ],
  "total_count": 1
}
```

#### 进程创建
```json
{
  "success": true,
  "action": "create",
  "pid": 12345,
  "log_file": "/path/to/log.log",
  "command": "sleep 60",
  "shell": "zsh"
}
```

## 性能考虑

- **内存使用**: 每个进程记录约占用几KB内存
- **CPU开销**: 进程检查操作CPU使用率低
- **磁盘空间**: 日志文件会持续增长，建议定期清理
- **进程限制**: 默认1000个进程，可根据系统能力调整

## 安全注意事项

- 工具需要能够创建和终止进程的权限
- 日志文件可能包含敏感信息，注意访问权限
- 清理操作会终止所有管理的进程，使用时需谨慎
- 建议在受控环境中使用，避免在生产系统上运行不信任的命令

## 版本历史

### v1.0 (当前版本)
- 初始发布
- 支持基本的进程管理功能
- 自动清理机制
- 多Shell支持
- 日志管理

## 许可证

本工具遵循 MIT 许可证。

## 贡献

欢迎提交问题报告和功能请求。

---

**注意**: 本工具主要用于开发和测试环境。在生产环境中使用前，请充分测试并了解其行为。
