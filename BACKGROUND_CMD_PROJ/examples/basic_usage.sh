#!/bin/bash
#
# BACKGROUND_CMD 基础使用示例
#

echo "=== BACKGROUND_CMD 基础使用示例 ==="

# 获取BACKGROUND_CMD路径
BACKGROUND_CMD="$HOME/.local/bin/BACKGROUND_CMD.sh"

if [[ ! -x "$BACKGROUND_CMD" ]]; then
    echo "错误: BACKGROUND_CMD 未找到或无执行权限"
    exit 1
fi

echo "1. 创建一个简单的后台任务 (sleep 10秒)"
$BACKGROUND_CMD "sleep 10"
echo

echo "2. 列出当前所有后台进程"
$BACKGROUND_CMD list
echo

echo "3. 创建一个使用bash的任务"
$BACKGROUND_CMD "echo 'Hello from bash'; sleep 5" --shell bash
echo

echo "4. 再次列出进程查看新任务"
$BACKGROUND_CMD list
echo

echo "5. 等待5秒后再次检查"
sleep 5
$BACKGROUND_CMD list
echo

echo "6. 创建一个会产生输出的任务"
$BACKGROUND_CMD "for i in {1..5}; do echo \"Count: \$i\"; sleep 2; done"
echo

echo "7. 查看日志目录"
$BACKGROUND_CMD logs
echo

echo "示例完成！"
echo "提示: 使用 'BACKGROUND_CMD cleanup' 清理所有后台进程"
