import shutil


def detect_package_manager() -> str | None:
    if shutil.which("apt-get"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("yum"):
        return "yum"
    if shutil.which("pacman"):
        return "pacman"
    if shutil.which("zypper"):
        return "zypper"
    return None


def manager_title(manager: str | None) -> str:
    if manager == "apt":
        return "APT"
    if manager == "dnf":
        return "DNF"
    if manager == "yum":
        return "YUM"
    if manager == "pacman":
        return "Pacman"
    if manager == "zypper":
        return "Zypper"
    return "Unknown"


def updates_check_command(manager: str | None) -> str | None:
    if manager == "apt":
        return "apt list --upgradable 2>/dev/null"
    if manager == "dnf":
        return (
            "dnf -q check-update; code=$?; "
            "if [ $code -eq 0 ] || [ $code -eq 100 ]; then exit 0; else exit $code; fi"
        )
    if manager == "yum":
        return (
            "yum -q check-update; code=$?; "
            "if [ $code -eq 0 ] || [ $code -eq 100 ]; then exit 0; else exit $code; fi"
        )
    if manager == "pacman":
        return "pacman -Sy --noconfirm >/dev/null && (pacman -Qu || true)"
    if manager == "zypper":
        return "zypper --non-interactive list-updates"
    return None


def updates_upgrade_command(manager: str | None) -> str | None:
    if manager == "apt":
        return "apt-get update -y && apt-get upgrade -y"
    if manager == "dnf":
        return "dnf upgrade -y"
    if manager == "yum":
        return "yum update -y"
    if manager == "pacman":
        return "pacman -Syu --noconfirm"
    if manager == "zypper":
        return "zypper --non-interactive update"
    return None


def updates_cleanup_command(manager: str | None) -> str | None:
    if manager == "apt":
        return "apt-get autoremove -y && apt-get autoclean -y"
    if manager == "dnf":
        return "dnf autoremove -y && dnf clean all"
    if manager == "yum":
        return "yum autoremove -y && yum clean all"
    if manager == "pacman":
        return "pacman -Sc --noconfirm"
    if manager == "zypper":
        return "zypper --non-interactive clean --all"
    return None
