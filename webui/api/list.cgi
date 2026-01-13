#!/system/bin/sh
echo "Content-Type: application/json"
echo ""

# 优先使用 system/xbin 下的工具，如果不存在则回退到默认
if [ -x "/system/xbin/jq" ]; then JQ="/system/xbin/jq"; else JQ="jq"; fi
if [ -x "/system/xbin/grep" ]; then GREP="/system/xbin/grep"; else GREP="grep"; fi
if [ -x "/system/xbin/mount" ]; then MOUNT="/system/xbin/mount"; else MOUNT="mount"; fi
if [ -x "/data/adb/ap/bin/busybox" ]; then BUSYBOX="/data/adb/ap/bin/busybox"; elif [ -x /data/adb/ksu/bin/busybox ]; then BUSYBOX="/data/adb/ksu/bin/busybox"; elif [ -x /data/adb/magisk/busybox ]; then BUSYBOX=/data/adb/magisk/busybox; else BUSYBOX=busybox; fi
alias awk="$BUSYBOX awk"
alias sed="$BUSYBOX sed"

# 定义目录
MODDIR="/data/adb/modules/rurima_tool"
ROOT_LXC="/data/ruri/lxc"
ROOT_DOCKER="/data/ruri/docker"
MANUAL_DB="$MODDIR/webui/config/manual.json"
CONFIG_DIR="$MODDIR/webui/config"

# 临时文件
TMP_PATHS="/tmp/rurima_paths.txt"
TMP_JSON_PARTS="/tmp/rurima_parts.txt"

# 清理旧文件
rm "$TMP_PATHS" "$TMP_JSON_PARTS" >/dev/null 2>&1

# LXC
if [ -d "$ROOT_LXC" ]; then
    for p in "$ROOT_LXC"/*; do
        if [ -f "$p/etc/os-release" ]; then echo "$p|lxc|auto" >> "$TMP_PATHS"; fi
    done
fi

# Docker
if [ -d "$ROOT_DOCKER" ]; then
    for p in "$ROOT_DOCKER"/*; do
        if [ -f "$p/etc/os-release" ]; then echo "$p|docker|auto" >> "$TMP_PATHS"; fi
    done
fi

# C. 手动添加 (解析 manual.json)
# 如果文件存在且不为空
if [ -s "$MANUAL_DB" ]; then
    # 使用 jq 提取 path, type, name 
    # 格式输出为: /path/to/container|type|manual
    $JQ -r '.[] | "\(.path)|\(.type)|manual"' "$MANUAL_DB" 2>/dev/null >> "$TMP_PATHS"
fi

# 如果没有找到任何容器，直接输出空数组
if [ ! -s "$TMP_PATHS" ]; then
    echo "[]"
    exit 0
fi

# 按路径排序并去重 (sort -u)
sort -u "$TMP_PATHS" | while IFS='|' read -r CONT_PATH CONT_TYPE SOURCE; do
    # 忽略无效行
    [ -z "$CONT_PATH" ] && continue
    
    NAME=$(basename "$CONT_PATH")
    
    # check status
    if $GREP -q " $CONT_PATH " /proc/mounts; then
        STATUS="running"
    else
        STATUS="stopped"
    fi

    
    AUTOSTART="false"
    CONF_FILE="$CONFIG_DIR/${NAME}.conf"
    if [ -f "$CONF_FILE" ]; then
        if $GREP -q 'AUTOSTART="true"' "$CONF_FILE"; then
            AUTOSTART="true"
        fi
    fi
    
    # --- 生成单条 JSON 对象 ---
    $JQ -n -c \
        --arg n "$NAME" \
        --arg p "$CONT_PATH" \
        --arg t "$CONT_TYPE" \
        --arg s "$STATUS" \
        --arg a "$AUTOSTART" \
        --arg src "$SOURCE" \
        '{name: $n, path: $p, type: $t, status: $s, autostart: $a, source: $src}' >> "$TMP_JSON_PARTS"

done

# 将每一行的 JSON 对象用逗号连接，并包裹在 [] 中
echo "["
if [ -f "$TMP_JSON_PARTS" ]; then
    sed '$!s/$/,/' "$TMP_JSON_PARTS"
fi
echo "]"

rm "$TMP_PATHS" "$TMP_JSON_PARTS" >/dev/null 2>&1
