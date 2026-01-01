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
                for line in f:
                    if "model name" in line or "Model" in line:
                        cpu_info = line.split(":")[1].strip()
                        break
    except Exception:
        pass

    # 2. OPERAČNÍ SYSTÉM (Kompletní detekce)
    if platform.system() == "Linux":
        os_full = f"{distro.name(pretty=True)}"
        if distro.codename():
            os_full += f" ({distro.codename()})"
    elif platform.system() == "Windows":
        os_full = f"Windows {platform.release()} (build {platform.version()})"
    else:
        os_full = f"{platform.system()} {platform.release()}"

    # 3. STATISTIKY (RAM, Jádra, Architektura)
    return {
        "cpu": cpu_info,
        "cores": f"{psutil.cpu_count(logical=False)} fyzických / {psutil.cpu_count(logical=True)} vláken",
        "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "os": os_full,
        "arch": platform.machine(),
        "python": platform.python_version(),
        "ver": version_tag
    }
