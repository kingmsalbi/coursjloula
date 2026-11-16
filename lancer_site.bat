@echo off
title Espace Pedagogique Msalbi - Serveur de Partage de Cours
color 0B
chcp 65001 >nul

echo ======================================================================
echo          ESPACE PEDAGOGIQUE - PROFESSEUR MSALBI
echo       Plateforme de Partage de Cours et de Suivi d'Assiduite
echo ======================================================================
echo.
echo Demarrage du serveur local...
echo.

:: Verifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas detecte sur votre systeme.
    echo Veuillez installer Python depuis https://www.python.org/
    pause
    exit /b
)

:: Lancement du serveur Python Flask
echo [OK] Serveur demarre avec succes !
echo.
echo ----------------------------------------------------------------------
echo  Adresses d'acces :
echo    - Sur cet ordinateur : http://localhost:5050
echo    - Pour les eleves :    http://[VOTRE_IP_LOCALE]:5050
echo.
echo  Identifiants :
echo    * Professeur (Admin) : identifiant = msalbi   ^| mot de passe = msalbi123
echo    * Eleve Demo :         identifiant = yassine.b ^| mot de passe = eleve123
echo ----------------------------------------------------------------------
echo.
echo Ouverture automatique de votre navigateur dans 2 secondes...
start "" "http://localhost:5050"

python app.py
pause
