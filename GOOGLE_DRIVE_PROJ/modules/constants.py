"""
GDS (Google Drive Shell) 常量定义
"""

# Background任务文件名模板
BG_STATUS_FILE_TEMPLATE = "cmd_bg_{bg_pid}.status"
BG_SCRIPT_FILE_TEMPLATE = "cmd_bg_{bg_pid}.sh"
BG_LOG_FILE_TEMPLATE = "cmd_bg_{bg_pid}.log"
BG_RESULT_FILE_TEMPLATE = "cmd_bg_{bg_pid}.result.json"

# 生成具体文件名的辅助函数
def get_bg_status_file(bg_pid):
    """获取background状态文件名"""
    return BG_STATUS_FILE_TEMPLATE.format(bg_pid=bg_pid)

def get_bg_script_file(bg_pid):
    """获取background脚本文件名"""
    return BG_SCRIPT_FILE_TEMPLATE.format(bg_pid=bg_pid)

def get_bg_log_file(bg_pid):
    """获取background日志文件名"""
    return BG_LOG_FILE_TEMPLATE.format(bg_pid=bg_pid)

def get_bg_result_file(bg_pid):
    """获取background结果文件名"""
    return BG_RESULT_FILE_TEMPLATE.format(bg_pid=bg_pid)

