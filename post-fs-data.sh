#!/system/bin/sh
MODDIR=${0%/*}

chmod 755 "$MODDIR/webroot/api/"*.cgi
chmod 755 "$MODDIR/service.sh"

chmod -R 777 "$MODDIR/webroot/config" 2>/dev/null
if [ ! -d "$MODDIR/webroot/config" ]; then
    mkdir -p "$MODDIR/webroot/config"
    chmod 777 "$MODDIR/webroot/config"
fi
