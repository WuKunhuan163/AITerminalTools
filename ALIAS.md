# ALIAS 命令接口说明

## 概述
ALIAS 是一个永久别名创建工具，可以在系统路径文件中创建持久的命令别名。

## 基本语法
```bash
ALIAS <简写命令> <等效命令>
```

## 使用示例

### 基本别名创建
```bash
# 创建简单别名
ALIAS ll "ls -la"
ALIAS gs "git status"
ALIAS python python3

# 创建复杂命令别名
ALIAS myip "curl -s https://ipinfo.io/ip"
ALIAS weather "curl -s wttr.in"
```

### 高级用法
```bash
# 创建带参数的别名
ALIAS gitlog "git log --oneline --graph --all"
ALIAS search "grep -r"

# 创建系统管理别名
ALIAS ports "lsof -i -P -n | grep LISTEN"
ALIAS processes "ps aux | grep"
```

## 功能特性

### 🔄 多Shell支持
ALIAS工具会同时更新以下配置文件：
- `~/.bash_profile` (Bash登录Shell)
- `~/.bashrc` (Bash非登录Shell)
- `~/.zshrc` (Zsh Shell)

### 🔒 安全检查
- 禁止使用 "ALIAS" 作为别名名称
- 检查别名名称格式（不允许空格）
- 自动处理现有别名的更新

### 📝 智能管理
- 自动创建不存在的配置文件
- 检测并更新现有别名
- 提供详细的操作反馈

## 参数说明

### 必需参数
1. **简写命令**: 要创建的别名名称
   - 不能是 "ALIAS"
   - 不能包含空格
   - 建议使用简短、易记的名称

2. **等效命令**: 别名对应的完整命令
   - 如果包含空格，必须用引号包围
   - 支持复杂的命令组合
   - 可以包含管道和重定向

## 使用场景

### 📂 文件操作
```bash
# 文件列表别名
ALIAS ll "ls -la"
ALIAS la "ls -A"
ALIAS l "ls -CF"

# 文件操作别名
ALIAS cp "cp -i"
ALIAS mv "mv -i"
ALIAS rm "rm -i"
```

### 🔧 Git操作
```bash
# Git状态和日志
ALIAS gs "git status"
ALIAS gl "git log --oneline"
ALIAS gd "git diff"

# Git提交和推送
ALIAS gca "git commit -a"
ALIAS gp "git push"
ALIAS gpl "git pull"
```

### 🌐 网络工具
```bash
# 网络诊断
ALIAS ping "ping -c 4"
ALIAS myip "curl -s https://ipinfo.io/ip"
ALIAS speedtest "curl -s https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py | python -"
```

### 🖥️ 系统监控
```bash
# 系统信息
ALIAS df "df -h"
ALIAS du "du -h"
ALIAS free "free -h"

# 进程管理
ALIAS ps "ps aux"
ALIAS top "htop"
ALIAS ports "lsof -i -P -n | grep LISTEN"
```

## 工作流程

1. **参数验证**: 检查参数数量和格式
2. **名称检查**: 验证别名名称的合法性
3. **文件处理**: 创建或更新配置文件
4. **别名管理**: 处理现有别名的更新
5. **结果反馈**: 显示操作结果和使用提示

## 配置文件说明

### ~/.bash_profile
- Bash登录Shell的配置文件
- 用户登录时自动执行
- 通常包含环境变量和启动脚本

### ~/.bashrc
- Bash非登录Shell的配置文件
- 新建终端窗口时执行
- 包含别名和函数定义

### ~/.zshrc
- Zsh Shell的配置文件
- macOS Catalina及以后版本的默认Shell
- 功能类似于.bashrc

## 立即生效

创建别名后，需要重新加载配置文件：

```bash
# 方法1: 重新加载配置文件
source ~/.bash_profile
source ~/.bashrc
source ~/.zshrc

# 方法2: 重新打开终端窗口

# 方法3: 使用exec重新启动Shell
exec $SHELL
```

## 管理现有别名

### 查看所有别名
```bash
# 查看当前Shell的所有别名
alias

# 查看特定别名
alias ll
```

### 临时禁用别名
```bash
# 使用反斜杠禁用别名
\ls instead of ls

# 使用command命令
command ls
```

### 删除别名
```bash
# 临时删除（当前会话）
unalias ll

# 永久删除（需要手动编辑配置文件）
vi ~/.bashrc
```

## 最佳实践

### 🎯 命名规范
- 使用简短、直观的名称
- 避免与系统命令冲突
- 使用一致的命名风格

### 📋 常用别名推荐
```bash
# 系统导航
ALIAS .. "cd .."
ALIAS ... "cd ../.."
ALIAS home "cd ~"

# 文件操作
ALIAS ll "ls -la"
ALIAS tree "tree -C"
ALIAS grep "grep --color=auto"

# 开发工具
ALIAS python python3
ALIAS pip pip3
ALIAS serve "python -m http.server"
```

### ⚠️ 注意事项
- 别名不能包含参数位置变量（$1, $2等）
- 复杂逻辑建议使用函数而非别名
- 定期清理不再使用的别名

## 错误处理

### 常见错误
1. **参数不足**: 需要提供两个参数
2. **非法名称**: 别名名称包含空格或特殊字符
3. **权限问题**: 无法写入配置文件
4. **文件冲突**: 配置文件被其他程序占用

### 调试技巧
```bash
# 检查别名是否生效
which <alias_name>

# 查看别名定义
type <alias_name>

# 检查配置文件
cat ~/.bashrc | grep alias
```

## 高级功能

### 条件别名
虽然ALIAS工具本身不支持条件别名，但可以在配置文件中手动添加：

```bash
# 根据操作系统创建不同别名
if [[ "$OSTYPE" == "darwin"* ]]; then
    alias ls="ls -G"
else
    alias ls="ls --color=auto"
fi
```

### 函数别名
对于复杂逻辑，建议使用函数：

```bash
# 在配置文件中定义函数
mkcd() {
    mkdir -p "$1" && cd "$1"
}
```

## 故障排除

### 别名不生效
1. 检查配置文件是否正确更新
2. 确认使用的Shell类型
3. 重新加载配置文件或重启终端

### 别名冲突
1. 检查是否与系统命令同名
2. 使用`type`命令查看命令类型
3. 选择不同的别名名称

## 项目位置
- 主程序: `~/.local/bin/ALIAS`
- 接口文档: `~/.local/bin/ALIAS.md`
- 配置文件: `~/.bash_profile`, `~/.bashrc`, `~/.zshrc` 