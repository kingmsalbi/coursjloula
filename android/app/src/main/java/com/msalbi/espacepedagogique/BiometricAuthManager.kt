package com.msalbi.espacepedagogique

import android.content.Context
import android.content.SharedPreferences
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class BiometricAuthManager(private val context: Context) {

    private val sharedPreferences: SharedPreferences by lazy {
        try {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()

            EncryptedSharedPreferences.create(
                context,
                "msalbi_biometric_secure_prefs",
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (e: Exception) {
            context.getSharedPreferences("msalbi_biometric_prefs_fallback", Context.MODE_PRIVATE)
        }
    }

    companion object {
        private const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
        private const val KEY_USERNAME = "bio_username"
        private const val KEY_PASSWORD = "bio_password"
        private const val KEY_CLASSE = "bio_classe"
    }

    fun isBiometricAvailable(): Boolean {
        val biometricManager = BiometricManager.from(context)
        val authenticators = BiometricManager.Authenticators.BIOMETRIC_STRONG or
                BiometricManager.Authenticators.BIOMETRIC_WEAK
        return biometricManager.canAuthenticate(authenticators) == BiometricManager.BIOMETRIC_SUCCESS
    }

    fun isBiometricConfigured(): Boolean {
        return sharedPreferences.getBoolean(KEY_BIOMETRIC_ENABLED, false) &&
                !sharedPreferences.getString(KEY_USERNAME, null).isNullOrEmpty() &&
                !sharedPreferences.getString(KEY_PASSWORD, null).isNullOrEmpty()
    }

    fun getSavedUsername(): String {
        return sharedPreferences.getString(KEY_USERNAME, "") ?: ""
    }

    fun getSavedClasse(): String {
        return sharedPreferences.getString(KEY_CLASSE, "") ?: ""
    }

    fun getSavedCredentials(): Triple<String, String, String>? {
        val user = sharedPreferences.getString(KEY_USERNAME, null) ?: return null
        val pass = sharedPreferences.getString(KEY_PASSWORD, null) ?: return null
        val classe = sharedPreferences.getString(KEY_CLASSE, "") ?: ""
        return Triple(user, pass, classe)
    }

    fun saveCredentials(username: String, password: String, classe: String) {
        sharedPreferences.edit()
            .putBoolean(KEY_BIOMETRIC_ENABLED, true)
            .putString(KEY_USERNAME, username)
            .putString(KEY_PASSWORD, password)
            .putString(KEY_CLASSE, classe)
            .apply()
    }

    fun clearCredentials() {
        sharedPreferences.edit()
            .putBoolean(KEY_BIOMETRIC_ENABLED, false)
            .remove(KEY_USERNAME)
            .remove(KEY_PASSWORD)
            .remove(KEY_CLASSE)
            .apply()
    }

    fun authenticate(
        activity: FragmentActivity,
        onSuccess: (user: String, pass: String, classe: String) -> Unit,
        onError: (String) -> Unit
    ) {
        val creds = getSavedCredentials()
        if (creds == null) {
            onError(activity.getString(R.string.biometric_not_enrolled))
            return
        }

        val executor = ContextCompat.getMainExecutor(activity)
        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle(activity.getString(R.string.biometric_title))
            .setSubtitle(activity.getString(R.string.biometric_subtitle))
            .setDescription("Connectez-vous en tant que : ${creds.first}")
            .setNegativeButtonText(activity.getString(R.string.biometric_negative))
            .setAllowedAuthenticators(
                BiometricManager.Authenticators.BIOMETRIC_STRONG or
                        BiometricManager.Authenticators.BIOMETRIC_WEAK
            )
            .build()

        val biometricPrompt = BiometricPrompt(
            activity,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    onSuccess(creds.first, creds.second, creds.third)
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    if (errorCode != BiometricPrompt.ERROR_USER_CANCELED &&
                        errorCode != BiometricPrompt.ERROR_NEGATIVE_BUTTON
                    ) {
                        onError(errString.toString())
                    }
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                }
            }
        )

        biometricPrompt.authenticate(promptInfo)
    }
}
