#!/bin/bash
# Remote Window Queue Reset Tool
# 重置远程窗口队列工具

echo "正在重置远程窗口队列..."

# 检查默认文件是否存在
if [ -f "GOOGLE_DRIVE_PROJ/remote_window_queue_default.json" ]; then
    # 使用默认文件重置
    cp "GOOGLE_DRIVE_PROJ/remote_window_queue_default.json" "GOOGLE_DRIVE_PROJ/remote_window_queue.json"
    echo "✅ 队列已重置为默认状态"
else
    # 手动创建默认状态
    cat > "GOOGLE_DRIVE_PROJ/remote_window_queue.json" << EOF
{
  "current_window": null,
  "waiting_queue": [],
  "last_update": $(date +%s)
}
EOF
    echo "✅ 队列已重置（创建新的默认状态）"
fi

# 显示当前状态
echo "当前队列状态:"
cat "GOOGLE_DRIVE_PROJ/remote_window_queue.json" | python3 -m json.tool
