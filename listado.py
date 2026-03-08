import os

base_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(base_dir, "estructura.txt")

with open(output_file, "w", encoding="utf-8") as f:
    for root, dirs, files in os.walk(base_dir):
        rel_path = os.path.relpath(root, base_dir)

        if rel_path == ".":
            ruta_base = "root"
        else:
            ruta_base = "root/" + rel_path.replace("\\", "/")

        # Escribir carpetas
        for d in dirs:
            f.write(f"{ruta_base}/{d}\n")

        # Escribir archivos
        for file in files:
            if file != "estructura.txt":
                f.write(f"{ruta_base}/{file}\n")

        # Evitar entrar dentro de node_modules
        if "node_modules" in dirs:
            dirs.remove("node_modules")

print("estructura.txt creado")