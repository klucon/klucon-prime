import platform
import psutil
import distro
import os

def get_sys_info(version_tag):
    # 1. PROCESOR (včetně hloubkové kontroly na Linuxu)
    cpu_info = platform.processor() or platform.machine()
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                content = f.read()
                for line in content.splitlines():
                    if "model name" in line or "Model" in line:
                        cpu_info = line.split(":")[1].strip()
                        break
    except Exception:
        pass

    # 2. OPERAČNÍ SYSTÉM (Oprava duplicitních jmen)
    os_name = platform.system()
    if os_name == "Linux":
        try:
            os_pretty = distro.name(pretty=True)
            codename = distro.codename()
            # Pokud už je codename v názvu (Debian to tak dělá), nebudeme ho zdvojovat
            if codename and codename.lower() not in os_pretty.lower():
                os_full = f"{os_pretty} ({codename})"
            else:
                os_full = os_pretty
        except:
            os_full = "Linux (Neznámá distribuce)"
    elif os_name == "Windows":
        os_full = f"Windows {platform.release()} (build {platform.version()})"
    else:
        os_full = f"{os_name} {platform.release()}"

    # 3. STATISTIKY
    return {
        "cpu": cpu_info,
        "cores": f"{psutil.cpu_count(logical=False)} fyzických / {psutil.cpu_count(logical=True)} vláken",
        "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "os": os_full,
        "arch": platform.machine(),
        "python": platform.python_version(),
        "ver": version_tag
    }
