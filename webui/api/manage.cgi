#!/system/bin/sh

if [ -x "/system/xbin/jq" ]; then JQ="/system/xbin/jq"; else JQ="jq"; fi
if [ -x "/system/xbin/mount" ]; then MOUNT="/system/xbin/mount"; else MOUNT="mount"; fi
if [ -x "/data/adb/ap/bin/busybox" ]; then BUSYBOX="/data/adb/ap/bin/busybox"; elif [ -x /data/adb/ksu/bin/busybox ]; then BUSYBOX="/data/adb/ksu/bin/busybox"; elif [ -x /data/adb/magisk/busybox ]; then BUSYBOX=/data/adb/magisk/busybox; else BUSYBOX=busybox; fi
alias awk="$BUSYBOX awk"
alias sed="$BUSYBOX sed"

# 读取 POST 数据
read -r POST_DATA

# 如果是 GET 请求或数据为空
if [ -z "$POST_DATA" ]; then
    echo "Content-Type: application/json"
    echo ""
    echo '{"status": "error", "message": "No data received"}'
    exit 0
fi

# 解析参数
ACTION=$(echo "$POST_DATA" | $JQ -r '.action')
NAME=$(echo "$POST_DATA" | $JQ -r '.name')
PATH=$(echo "$POST_DATA" | $JQ -r '.path')
TYPE=$(echo "$POST_DATA" | $JQ -r '.type')
IS_AUTO=$(echo "$POST_DATA" | $JQ -r '.autostart')
# Config 数据是一个数组对象
CONFIG_DATA=$(echo "$POST_DATA" | $JQ -c '.config') 

MODDIR="/data/adb/modules/rurima_tool"
CONF_FILE="$MODDIR/webui/config/${NAME}.conf"
MANUAL_DB="$MODDIR/webui/config/manual.json"

echo "Content-Type: application/json"
echo ""

case "$ACTION" in
    "start")
        ARGS=""
        if [ -f "$CONF_FILE" ]; then
            while IFS='=' read -r key value; do
                if [ "$key" != "AUTOSTART" ] && [ -n "$key" ]; then
                    clean_val=$(echo "$value" | tr -d '"')
                    ARGS="$ARGS $key $clean_val"
                fi
            done < "$CONF_FILE"
        fi
        
        # 启动命令
        nohup rurima ruri $ARGS "$PATH" >/dev/null 2>&1 &
        sleep 1
        echo '{"status": "success", "message": "Start command issued"}'
        ;;

    "stop")
        # 强制停止逻辑
        fuser -k "$PATH" >/dev/null 2>&1
        ruri -U "$PATH" >/dev/null 2>&1
        umount -lvf "$PATH" 2>/dev/null
        umount -lf "$PATH/sdcard" 2>/dev/null
        umount -lf "$PATH/sys" 2>/dev/null
        umount -lf "$PATH/proc" 2>/dev/null
        umount -lf "$PATH/dev" 2>/dev/null
        
        echo '{"status": "success", "message": "Container stopped"}'
        ;;

    "save")
        echo "# Config for $NAME" > "$CONF_FILE"
        echo "AUTOSTART=\"$IS_AUTO\"" >> "$CONF_FILE"
        
        # 只有当 CONFIG_DATA 不是 null 且不为空时才处理
        if [ "$CONFIG_DATA" != "null" ] && [ "$CONFIG_DATA" != "[]" ]; then
            echo "$CONFIG_DATA" | $JQ -c '.[]' | while read -r item; do
                k=$(echo "$item" | $JQ -r '.key')
                v=$(echo "$item" | $JQ -r '.value')
                # 只有 key 存在才写入
                if [ -n "$k" ] && [ "$k" != "null" ]; then
                    echo "$k=\"$v\"" >> "$CONF_FILE"
                fi
            done
        fi
        echo '{"status": "success", "message": "Configuration saved"}'
        ;;
        
    "get_config")
        if [ -f "$CONF_FILE" ]; then
            # 使用 awk 构造简单的 JSON，不依赖 jq 复杂的 filter
            awk -F'=' 'BEGIN{print "["} /="/ {gsub(/"/, "", $2); printf "{\"key\":\"%s\", \"value\":\"%s\"},", $1, $2} END{print "{}]"}' "$CONF_FILE" | sed 's/,{}]/]/g'
        else
            echo "[]"
        fi
        ;;

    "add_manual")
        # 1. 检查目录是否存在
        if [ ! -d "$PATH" ]; then
            echo '{"status": "error", "message": "Path does not exist on device"}'
            exit 0
        fi
        
        # 2. 构造新对象
        NEW_ENTRY=$($JQ -n --arg n "$NAME" --arg p "$PATH" --arg t "$TYPE" '{name: $n, path: $p, type: $t}')
        
        # 3. 确保 manual.json 是合法的 JSON 数组
        if [ ! -s "$MANUAL_DB" ]; then echo "[]" > "$MANUAL_DB"; fi
        # 如果文件内容坏了 (比如 jq 读取失败)，重置它
        if ! $JQ . "$MANUAL_DB" >/dev/null 2>&1; then echo "[]" > "$MANUAL_DB"; fi
        
        # 4. 写入
        tmp=$(mktemp)
        $JQ --argjson new "$NEW_ENTRY" '. += [$new] | unique_by(.path)' "$MANUAL_DB" > "$tmp" && mv "$tmp" "$MANUAL_DB"
        chmod 666 "$MANUAL_DB"
        
        echo '{"status": "success", "message": "Container added manually"}'
        ;;
        
    *)
        echo '{"status": "error", "message": "Unknown action"}'
        ;;
esac
