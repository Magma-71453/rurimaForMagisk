#!/system/bin/sh
MODDIR=${0%/*}

while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 1
done
sleep 5

pid=$(ps aux | grep -v grep | grep "busybox httpd.*-p 8081.*/data/adb/modules/rurima_tool/webui" | awk '{print $2}')

if [ -n "$pid" ]; then
    echo "Killing process $pid"
    kill $pid
else
    echo "Process not found"
fi

# start WebUI
nohup busybox httpd -f -v -p 8081 -h "$MODDIR/webui" -c "$MODDIR/httpd.conf"

CONFIG_DIR="$MODDIR/webui/config"
DATA_LXC="/data/ruri/lxc"
DATA_DOCKER="/data/ruri/docker"
MANUAL_DB="$CONFIG_DIR/manual.json"

if [ -x "/system/xbin/jq" ]; then JQ="/system/xbin/jq"; else JQ="jq"; fi

start_container() {
    local name=$1
    local path=$2
    local conf="$CONFIG_DIR/${name}.conf"
    
    local args=""
    if [ -f "$conf" ]; then
        while IFS='=' read -r key value; do
            if [ "$key" != "AUTOSTART" ] && [ -n "$key" ]; then
                clean_val=$(echo "$value" | tr -d '"')
                args="$args $key $clean_val"
            fi
        done < "$conf"
    fi
    nohup rurima ruri $args "$path" >/dev/null 2>&1 &
}

for CONF in "$CONFIG_DIR"/*.conf; do
    [ -f "$CONF" ] || continue
    if grep -q 'AUTOSTART="true"' "$CONF"; then
        NAME=$(basename "$CONF" .conf)
        if [ -d "$DATA_LXC/$NAME" ]; then
            start_container "$NAME" "$DATA_LXC/$NAME"
        elif [ -d "$DATA_DOCKER/$NAME" ]; then
            start_container "$NAME" "$DATA_DOCKER/$NAME"
        fi
        sleep 2
    fi
done

if [ -f "$MANUAL_DB" ] && [ -s "$MANUAL_DB" ]; then
    $JQ -r '.[].name' "$MANUAL_DB" 2>/dev/null | while read -r NAME; do
        CONF="$CONFIG_DIR/${NAME}.conf"
        if [ -f "$CONF" ] && grep -q 'AUTOSTART="true"' "$CONF"; then
            PATH=$($JQ -r --arg n "$NAME" '.[] | select(.name==$n) | .path' "$MANUAL_DB")
            if [ -d "$PATH" ]; then
                start_container "$NAME" "$PATH"
                sleep 2
            fi
        fi
    done
fi
