package com.msalbi.espacepedagogique

import android.webkit.JavascriptInterface
import android.widget.Toast
import androidx.appcompat.app.AlertDialog

class WebAppInterface(
    private val activity: MainActivity,
    private val biometricManager: BiometricAuthManager
) {

    @JavascriptInterface
    fun isBiometricAvailable(): Boolean {
        return biometricManager.isBiometricAvailable()
    }

    @JavascriptInterface
    fun isBiometricConfigured(): Boolean {
        return biometricManager.isBiometricConfigured()
    }

    @JavascriptInterface
    fun getSavedUsername(): String {
        return biometricManager.getSavedUsername()
    }

    @JavascriptInterface
    fun getSavedClasse(): String {
        return biometricManager.getSavedClasse()
    }

    @JavascriptInterface
    fun triggerBiometricPrompt() {
        activity.runOnUiThread {
            activity.startBiometricAuthentication()
        }
    }

    @JavascriptInterface
    fun saveBiometricCredentials(username: String, password: String, classe: String): Boolean {
        return try {
            biometricManager.saveCredentials(username, password, classe)
            activity.runOnUiThread {
                activity.updateBiometricUi()
                Toast.makeText(activity, R.string.biometric_enabled_toast, Toast.LENGTH_SHORT).show()
            }
            true
        } catch (e: Exception) {
            false
        }
    }

    @JavascriptInterface
    fun clearBiometricCredentials() {
        biometricManager.clearCredentials()
        activity.runOnUiThread {
            activity.updateBiometricUi()
            Toast.makeText(activity, R.string.biometric_disabled_toast, Toast.LENGTH_SHORT).show()
        }
    }

    @JavascriptInterface
    fun promptSaveBiometric(username: String, password: String, classe: String) {
        if (!biometricManager.isBiometricAvailable()) return
        if (biometricManager.isBiometricConfigured()) {
            val saved = biometricManager.getSavedUsername()
            if (saved == username) return
        }

        activity.runOnUiThread {
            AlertDialog.Builder(activity)
                .setTitle(R.string.biometric_title)
                .setMessage("Voulez-vous activer la connexion par empreinte digitale pour « $username » lors de vos prochaines visites ?")
                .setPositiveButton("Activer") { _, _ ->
                    saveBiometricCredentials(username, password, classe)
                }
                .setNegativeButton("Plus tard", null)
                .show()
        }
    }

    @JavascriptInterface
    fun onLoginSuccess(username: String, @Suppress("UNUSED_PARAMETER") token: String, role: String) {
        activity.runOnUiThread {
            activity.onUserLoggedIn(username, role)
        }
    }

    @JavascriptInterface
    fun onLogout() {
        activity.runOnUiThread {
            activity.onUserLoggedOut()
        }
    }

    @JavascriptInterface
    fun showToast(message: String) {
        activity.runOnUiThread {
            Toast.makeText(activity, message, Toast.LENGTH_SHORT).show()
        }
    }

    @JavascriptInterface
    fun showNotification(title: String, message: String, notificationId: Int) {
        NotificationHelper.showNotification(
            context = activity,
            title = title,
            message = message,
            notificationId = if (notificationId > 0) notificationId else 1001
        )
    }

    @JavascriptInterface
    fun areNotificationsEnabled(): Boolean {
        return androidx.core.app.NotificationManagerCompat.from(activity).areNotificationsEnabled()
    }

    @JavascriptInterface
    fun requestNotificationPermission() {
        activity.runOnUiThread {
            activity.requestNotificationPermissionIfNeeded()
        }
    }
}
