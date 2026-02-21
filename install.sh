#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Запустите install.sh от root"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_INSTALL_DIR="/opt/fuq-bot"
DEFAULT_SERVICE_NAME="fuq-bot"
PACKAGE_MANAGER=""

detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    PACKAGE_MANAGER="apt"
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    PACKAGE_MANAGER="dnf"
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    PACKAGE_MANAGER="yum"
    return
  fi
  if command -v pacman >/dev/null 2>&1; then
    PACKAGE_MANAGER="pacman"
    return
  fi
  if command -v zypper >/dev/null 2>&1; then
    PACKAGE_MANAGER="zypper"
    return
  fi
  echo "Не удалось определить пакетный менеджер"
  exit 1
}

read_nonempty() {
  local prompt="$1"
  local value=""
  while [[ -z "$value" ]]; do
    read -r -p "$prompt" value
  done
  printf "%s" "$value"
}

read_default() {
  local prompt="$1"
  local default="$2"
  local value=""
  read -r -p "$prompt [$default]: " value
  if [[ -z "$value" ]]; then
    printf "%s" "$default"
  else
    printf "%s" "$value"
  fi
}

read_yes_no() {
  local prompt="$1"
  local default="$2"
  local hint=""
  local default_value=""
  local value=""
  if [[ "$default" =~ ^[Yy]$ ]]; then
    hint="Y/n"
    default_value="Y"
  else
    hint="y/N"
    default_value="N"
  fi
  read -r -p "$prompt [$hint]: " value
  value="${value:-$default_value}"
  if [[ "$value" =~ ^([Yy]|[Yy][Ee][Ss]|[Дд]|[Дд][Аа])$ ]]; then
    printf "yes"
  else
    printf "no"
  fi
}

warn() {
  echo "WARN: $1"
}

normalize_ports_csv() {
  local raw="$1"
  local cleaned=""
  local chunk=""
  local token=""
  local out=""
  local seen="|"
  cleaned="${raw//;/,}"
  IFS=',' read -ra chunks <<< "$cleaned"
  for chunk in "${chunks[@]}"; do
    token="$(echo "$chunk" | tr -d '[:space:]')"
    if [[ -z "$token" ]]; then
      continue
    fi
    if [[ "$token" =~ ^[0-9]+$ ]] && (( token >= 1 && token <= 65535 )); then
      if [[ "$seen" != *"|$token|"* ]]; then
        seen="${seen}${token}|"
        if [[ -z "$out" ]]; then
          out="$token"
        else
          out="${out},${token}"
        fi
      fi
    fi
  done
  if [[ -z "$out" ]]; then
    out="22,80,443"
  fi
  echo "$out"
}

apply_safe_firewall() {
  local ports_csv="$1"
  local port=""
  local parts=()
  iptables -F
  iptables -X
  iptables -P INPUT DROP
  iptables -P FORWARD DROP
  iptables -P OUTPUT ACCEPT
  iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  iptables -A INPUT -i lo -j ACCEPT
  iptables -A INPUT -p icmp -j ACCEPT
  IFS=',' read -ra parts <<< "$ports_csv"
  for port in "${parts[@]}"; do
    [[ -z "$port" ]] && continue
    iptables -A INPUT -p tcp --dport "$port" -j ACCEPT
    iptables -A INPUT -p udp --dport "$port" -j ACCEPT
  done
}

install_first_available() {
  local manager="$1"
  shift
  case "$manager" in
    apt)
      local pkg=""
      for pkg in "$@"; do
        if apt-cache show "$pkg" >/dev/null 2>&1; then
          if apt-get install -y "$pkg"; then
            return 0
          fi
        fi
      done
      ;;
    dnf)
      local pkg=""
      for pkg in "$@"; do
        if dnf install -y "$pkg"; then
          return 0
        fi
      done
      ;;
    yum)
      local pkg=""
      for pkg in "$@"; do
        if yum install -y "$pkg"; then
          return 0
        fi
      done
      ;;
    pacman)
      local pkg=""
      for pkg in "$@"; do
        if pacman -S --noconfirm "$pkg"; then
          return 0
        fi
      done
      ;;
    zypper)
      local pkg=""
      for pkg in "$@"; do
        if zypper --non-interactive install "$pkg"; then
          return 0
        fi
      done
      ;;
  esac
  return 1
}

install_base_packages() {
  case "$PACKAGE_MANAGER" in
    apt)
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -y
      apt-get install -y python3 python3-venv python3-pip iptables tar
      install_first_available apt iproute2 iproute || true
      install_first_available apt iputils-ping iputils || true
      ;;
    dnf)
      dnf install -y python3 python3-pip iptables tar
      install_first_available dnf iproute iproute2 || true
      install_first_available dnf iputils iputils-ping || true
      ;;
    yum)
      yum install -y python3 python3-pip iptables tar
      install_first_available yum iproute iproute2 || true
      install_first_available yum iputils iputils-ping || true
      ;;
    pacman)
      pacman -Sy --noconfirm python python-pip iptables iproute2 iputils tar
      ;;
    zypper)
      zypper --non-interactive install python3 python3-pip python3-virtualenv iptables tar
      install_first_available zypper iproute2 iproute || true
      install_first_available zypper iputils iputils-ping || true
      ;;
  esac
}

install_optional_packages() {
  local install_docker="$1"
  local install_fail2ban="$2"
  case "$PACKAGE_MANAGER" in
    apt)
      if [[ "$install_docker" == "yes" ]]; then
        if ! install_first_available apt docker.io docker; then
          warn "Не удалось установить Docker Engine"
        fi
        if ! install_first_available apt docker-compose-plugin docker-compose-v2 docker-compose; then
          warn "Не удалось установить Docker Compose"
        fi
      fi
      if [[ "$install_fail2ban" == "yes" ]]; then
        if ! install_first_available apt fail2ban; then
          warn "Не удалось установить Fail2ban"
        fi
      fi
      ;;
    dnf)
      if [[ "$install_docker" == "yes" ]]; then
        if ! install_first_available dnf docker moby-engine; then
          warn "Не удалось установить Docker Engine"
        fi
        if ! install_first_available dnf docker-compose-plugin docker-compose; then
          warn "Не удалось установить Docker Compose"
        fi
      fi
      if [[ "$install_fail2ban" == "yes" ]]; then
        if ! install_first_available dnf fail2ban; then
          warn "Не удалось установить Fail2ban"
        fi
      fi
      ;;
    yum)
      if [[ "$install_docker" == "yes" ]]; then
        if ! install_first_available yum docker docker-ce; then
          warn "Не удалось установить Docker Engine"
        fi
        if ! install_first_available yum docker-compose-plugin docker-compose; then
          warn "Не удалось установить Docker Compose"
        fi
      fi
      if [[ "$install_fail2ban" == "yes" ]]; then
        if ! install_first_available yum fail2ban; then
          warn "Не удалось установить Fail2ban"
        fi
      fi
      ;;
    pacman)
      if [[ "$install_docker" == "yes" ]]; then
        if ! install_first_available pacman docker; then
          warn "Не удалось установить Docker Engine"
        fi
        if ! install_first_available pacman docker-compose docker-buildx; then
          warn "Не удалось установить Docker Compose"
        fi
      fi
      if [[ "$install_fail2ban" == "yes" ]]; then
        if ! install_first_available pacman fail2ban; then
          warn "Не удалось установить Fail2ban"
        fi
      fi
      ;;
    zypper)
      if [[ "$install_docker" == "yes" ]]; then
        if ! install_first_available zypper docker; then
          warn "Не удалось установить Docker Engine"
        fi
        if ! install_first_available zypper docker-compose docker-compose-switch; then
          warn "Не удалось установить Docker Compose"
        fi
      fi
      if [[ "$install_fail2ban" == "yes" ]]; then
        if ! install_first_available zypper fail2ban; then
          warn "Не удалось установить Fail2ban"
        fi
      fi
      ;;
  esac
}

detect_package_manager

echo "FUQ Telegram Server Bot Installer"
BOT_TOKEN="$(read_nonempty "Введите BOT_TOKEN: ")"
ADMIN_ID="$(read_nonempty "Введите ADMIN_ID: ")"
while [[ ! "$ADMIN_ID" =~ ^[0-9]+$ ]]; do
  ADMIN_ID="$(read_nonempty "ADMIN_ID должен быть числом. Введите ADMIN_ID: ")"
done
INSTALL_DIR="$(read_default "Папка установки" "$DEFAULT_INSTALL_DIR")"
SERVICE_NAME="$(read_default "Имя systemd сервиса" "$DEFAULT_SERVICE_NAME")"
COMMAND_TIMEOUT="$(read_default "Таймаут системных команд (сек)" "30")"
TERMINAL_TIMEOUT="$(read_default "Таймаут терминала (сек)" "60")"
EXTRA_ADMIN_IDS_RAW="$(read_default "Дополнительные ADMIN_ID через запятую (опционально)" "")"
EXTRA_ADMIN_IDS="$(echo "$EXTRA_ADMIN_IDS_RAW" | tr -d '[:space:]')"
FIREWALL_SAFE_PORTS_INPUT="$(read_default "Безопасные входящие порты firewall (через запятую)" "22,80,443")"
FIREWALL_SAFE_PORTS="$(normalize_ports_csv "$FIREWALL_SAFE_PORTS_INPUT")"
ENABLE_FIREWALL_NOW="$(read_yes_no "Включить безопасный firewall сразу после установки?" "N")"
if [[ ",$FIREWALL_SAFE_PORTS," != *",22,"* ]]; then
  warn "В списке firewall-портов нет 22/tcp. Убедитесь, что ваш SSH-порт добавлен."
fi
INSTALL_DOCKER="$(read_yes_no "Установить Docker/Compose?" "Y")"
INSTALL_FAIL2BAN="$(read_yes_no "Установить Fail2ban?" "Y")"

echo
echo "Параметры установки:"
echo "BOT_TOKEN: задан"
echo "ADMIN_ID: $ADMIN_ID"
echo "INSTALL_DIR: $INSTALL_DIR"
echo "SERVICE_NAME: $SERVICE_NAME"
echo "COMMAND_TIMEOUT: $COMMAND_TIMEOUT"
echo "TERMINAL_TIMEOUT: $TERMINAL_TIMEOUT"
echo "EXTRA_ADMIN_IDS: ${EXTRA_ADMIN_IDS:-<none>}"
echo "FIREWALL_SAFE_PORTS: $FIREWALL_SAFE_PORTS"
echo "ENABLE_FIREWALL_NOW: $ENABLE_FIREWALL_NOW"
echo "INSTALL_DOCKER: $INSTALL_DOCKER"
echo "INSTALL_FAIL2BAN: $INSTALL_FAIL2BAN"
echo "PACKAGE_MANAGER: $PACKAGE_MANAGER"
read -r -p "Продолжить установку? [Y/n]: " CONFIRM
CONFIRM="${CONFIRM:-Y}"
if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
  echo "Установка отменена"
  exit 0
fi

install_base_packages
install_optional_packages "$INSTALL_DOCKER" "$INSTALL_FAIL2BAN"

PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python || true)"
fi
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python не найден после установки"
  exit 1
fi

mkdir -p "$INSTALL_DIR"
tar --exclude=".venv" --exclude=".git" --exclude="__pycache__" -cf - -C "$SCRIPT_DIR" . | tar -xf - -C "$INSTALL_DIR"
"$PYTHON_BIN" -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

cat > "$INSTALL_DIR/.env" <<EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID
ADMIN_IDS=$EXTRA_ADMIN_IDS
COMMAND_TIMEOUT=$COMMAND_TIMEOUT
TERMINAL_TIMEOUT=$TERMINAL_TIMEOUT
FIREWALL_SAFE_PORTS=$FIREWALL_SAFE_PORTS
EOF
chmod 600 "$INSTALL_DIR/.env"

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=FUQ Telegram Linux Control Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/python -m app.bot
Restart=always
RestartSec=3
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

if [[ "$INSTALL_DOCKER" == "yes" ]]; then
  systemctl enable --now docker || true
fi
if [[ "$INSTALL_FAIL2BAN" == "yes" ]]; then
  systemctl enable --now fail2ban || true
fi

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

if [[ "$ENABLE_FIREWALL_NOW" == "yes" ]]; then
  if ! apply_safe_firewall "$FIREWALL_SAFE_PORTS"; then
    warn "Не удалось применить firewall автоматически. Можно включить его из бота."
  fi
fi

echo
echo "Сервис запущен. Краткий статус:"
systemctl --no-pager --full status "$SERVICE_NAME" | sed -n '1,14p'
echo
echo "Готово"
