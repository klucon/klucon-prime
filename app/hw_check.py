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

# 2. OPERAČNÍ SYSTÉM (Definitivní oprava duplicity)
    os_name = platform.system()
    if os_name == "Linux":
        try:
            os_pretty = distro.name(pretty=True) # "Debian GNU/Linux 13 (trixie)"
            codename = distro.codename()         # "trixie"
            
            # Pokud OS_PRETTY už obsahuje závorku, vypíšeme ho čistě, 
            # jinak zkusíme přidat codename, pokud ho známe.
            if "(" in os_pretty:
                os_full = os_pretty
            elif codename:
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
