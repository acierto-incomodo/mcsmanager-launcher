@echo off
setlocal

rem Variables
rem %~dp0 se expande a la ruta del directorio donde se encuentra este script.
set "projectRoot=%~dp0"
set "publishFolder=%projectRoot%publish"

echo.
echo --- Proceso de copia para publicacion ---
echo.

rem Crear carpeta publish si no existe
if not exist "%publishFolder%" (
    echo Creando carpeta de publicacion: %publishFolder%
    mkdir "%publishFolder%"
)

rem Copiar contenido de "output" completo
set "outputFolder=%projectRoot%output"
if exist "%outputFolder%" (
    echo Copiando contenido de 'output'...
    xcopy "%outputFolder%\*" "%publishFolder%" /E /I /Y /Q
)

rem Copiar contenido de "dist" completo
set "distFolder=%projectRoot%dist"
if exist "%distFolder%" (
    echo Copiando contenido de 'dist'...
    xcopy "%distFolder%\*" "%publishFolder%" /E /I /Y /Q
)

rem Archivos específicos
echo Copiando archivos especificos (version, notas, etc.)...
set "filesToCopy=version.txt ReleaseNotes.txt version_win_launcher.txt"
for %%f in (%filesToCopy%) do (
    if exist "%projectRoot%%%f" (
        copy /Y "%projectRoot%%%f" "%publishFolder%" > nul
    )
)

rem Archivos por extensión
echo Copiando archivos por extension (*.png, *.ico)...
copy /Y "%projectRoot%*.png" "%publishFolder%" > nul
copy /Y "%projectRoot%*.ico" "%publishFolder%" > nul

rem Eliminar installer_updater.exe de la carpeta publish
if exist "%publishFolder%\installer_updater.exe" (
    del "%publishFolder%\installer_updater.exe"
    echo Eliminado 'installer_updater.exe' de la carpeta de publicacion.
)

echo.
echo --- Proceso completado. Archivos copiados en 'publish' ---
echo.

endlocal