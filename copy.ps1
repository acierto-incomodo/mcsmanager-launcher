# Variables
$projectRoot = "C:\Users\melio\Documents\GitHub\mcsmanager-launcher"  # Cambia a tu ruta si es diferente
$publishFolder = Join-Path $projectRoot "publish"

# Crear carpeta publish si no existe
if (-Not (Test-Path $publishFolder)) {
    New-Item -ItemType Directory -Path $publishFolder | Out-Null
}

# Copiar contenido de "output" completo
$outputFolder = Join-Path $projectRoot "output"
if (Test-Path $outputFolder) {
    Copy-Item "$outputFolder\*" $publishFolder -Recurse -Force
}

# Copiar contenido de "dist" completo
$distFolder = Join-Path $projectRoot "dist"
if (Test-Path $distFolder) {
    Copy-Item "$distFolder\*" $publishFolder -Recurse -Force
}

# Archivos específicos
$filesToCopy = @(
    "version.txt",
    "ReleaseNotes.txt",
    "version_win_launcher.txt"
)

foreach ($file in $filesToCopy) {
    $filePath = Join-Path $projectRoot $file
    if (Test-Path $filePath) {
        Copy-Item $filePath $publishFolder -Force
    }
}

# Archivos por extensión
$extensions = @("*.png", "*.ico")
foreach ($ext in $extensions) {
    Get-ChildItem -Path $projectRoot -Filter $ext | ForEach-Object {
        Copy-Item $_.FullName $publishFolder -Force
    }
}

# Eliminar installer_updater.exe de la carpeta publish
$updaterExePath = Join-Path $publishFolder "installer_updater.exe"
if (Test-Path $updaterExePath) {
    Remove-Item $updaterExePath -Force
    Write-Host "Eliminado 'installer_updater.exe' de la carpeta de publicación."
}



Write-Host "Todos los archivos copiados en '$publishFolder'"