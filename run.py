import os
import subprocess
import time

script_name = "helper.py"


def main():
  print(f"[Run.py] Запуск {script_name}...")
  process = subprocess.Popen(["python", script_name])

  # Запоминаем время последнего изменения файла
  last_mtime = os.path.getmtime(script_name)

  try:
    while True:
      time.sleep(0.5)
      current_mtime = os.path.getmtime(script_name)

      # Если файл был изменен (сохранен), перезапускаем процесс
      if current_mtime != last_mtime:
        last_mtime = current_mtime
        print(f"[Run.py] Обнаружены изменения, перезапуск приложения...")

        process.terminate()
        process.wait()

        process = subprocess.Popen(["python", script_name])

  except KeyboardInterrupt:
    process.terminate()
    print("[Run.py] Остановлено.")


if __name__ == "__main__":
  main()