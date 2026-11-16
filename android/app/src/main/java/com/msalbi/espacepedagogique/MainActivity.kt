package com.msalbi.espacepedagogique

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.webkit.CookieManager
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.msalbi.espacepedagogique.databinding.ActivityMainBinding
import org.json.JSONObject

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var biometricManager: BiometricAuthManager

    private var fileChooserCallback: ValueCallback<Array<Uri>>? = null
    private var customView: View? = null
    private var customViewCallback: WebChromeClient.CustomViewCallback? = null

    private var backPressedOnce = false
    private val resetBackHandler = Handler(Looper.getMainLooper())
    private var hasPromptedAutoBiometric = false

    private val fileChooserLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (fileChooserCallback == null) return@registerForActivityResult
        var results: Array<Uri>? = null
        if (result.resultCode == RESULT_OK) {
            val intent = result.data
            if (intent != null) {
                val dataString = intent.dataString
                val clipData = intent.clipData
                if (clipData != null) {
                    results = Array(clipData.itemCount) { i -> clipData.getItemAt(i).uri }
                } else if (dataString != null) {
                    results = arrayOf(Uri.parse(dataString))
                }
            }
        }
        fileChooserCallback?.onReceiveValue(results)
        fileChooserCallback = null
    }

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            NotificationHelper.showNotification(
                this,
                "Notifications Activées",
                "Vous recevrez désormais les alertes de messages et de cours.",
                999
            )
        }
    }

    fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    android.Manifest.permission.POST_NOTIFICATIONS
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                notificationPermissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        NotificationHelper.createNotificationChannel(this)
        requestNotificationPermissionIfNeeded()

        biometricManager = BiometricAuthManager(this)

        setupBackNavigation()
        setupSwipeRefresh()
        setupOfflineRetry()
        setupFabBiometric()
        setupWebView()

        loadPlatformUrl()
    }

    private fun loadPlatformUrl() {
        val targetUrl = getString(R.string.default_url)
        if (!isNetworkAvailable()) {
            showOfflineView(true)
        } else {
            showOfflineView(false)
            binding.webView.loadUrl(targetUrl)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val webView = binding.webView
        val settings = webView.settings

        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.displayZoomControls = false
        settings.builtInZoomControls = true
        settings.setSupportZoom(true)
        settings.allowFileAccess = true
        settings.mediaPlaybackRequiresUserGesture = false
        settings.cacheMode = WebSettings.LOAD_DEFAULT
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE

        // Cookie management
        val cookieManager = CookieManager.getInstance()
        cookieManager.setAcceptCookie(true)
        cookieManager.setAcceptThirdPartyCookies(webView, true)

        // JavaScript interface bridge
        val webAppInterface = WebAppInterface(this, biometricManager)
        webView.addJavascriptInterface(webAppInterface, "AndroidBridge")

        // Download listener for PDFs, Word documents, Excel sheets
        webView.setDownloadListener { url, userAgent, contentDisposition, mimetype, _ ->
            DownloadHelper.downloadFile(this, url, userAgent, contentDisposition, mimetype)
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                super.onPageStarted(view, url, favicon)
                binding.progressBar.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                binding.progressBar.visibility = View.GONE
                binding.swipeRefreshLayout.isRefreshing = false
                showOfflineView(false)

                injectBridgeScript()
                checkAndAutoPromptBiometric()
                updateBiometricUi()
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                if (request?.isForMainFrame == true) {
                    showOfflineView(true)
                }
            }

            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?
            ): Boolean {
                val url = request?.url?.toString() ?: return false
                val host = request.url?.host ?: ""

                // Keep platform URLs inside WebView
                if (host.contains("cours-msalbi.vercel.app") || host.contains("vercel.app") || host == "localhost") {
                    return false
                }

                // Handle external apps (mailto, tel, whatsapp, etc.)
                return try {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    startActivity(intent)
                    true
                } catch (e: Exception) {
                    false
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                super.onProgressChanged(view, newProgress)
                binding.progressBar.progress = newProgress
                if (newProgress >= 100) {
                    binding.progressBar.visibility = View.GONE
                } else if (binding.progressBar.visibility == View.GONE) {
                    binding.progressBar.visibility = View.VISIBLE
                }
            }

            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                fileChooserCallback?.onReceiveValue(null)
                fileChooserCallback = filePathCallback

                val intent = fileChooserParams?.createIntent() ?: Intent(Intent.ACTION_GET_CONTENT).apply {
                    type = "*/*"
                    addCategory(Intent.CATEGORY_OPENABLE)
                }

                try {
                    fileChooserLauncher.launch(intent)
                } catch (e: Exception) {
                    fileChooserCallback?.onReceiveValue(null)
                    fileChooserCallback = null
                    return false
                }
                return true
            }

            override fun onShowCustomView(view: View?, callback: CustomViewCallback?) {
                if (customView != null) {
                    callback?.onCustomViewHidden()
                    return
                }
                customView = view
                customViewCallback = callback
                binding.customViewContainer.addView(view)
                binding.customViewContainer.visibility = View.VISIBLE
                binding.swipeRefreshLayout.visibility = View.GONE
            }

            override fun onHideCustomView() {
                if (customView == null) return
                binding.customViewContainer.removeView(customView)
                binding.customViewContainer.visibility = View.GONE
                binding.swipeRefreshLayout.visibility = View.VISIBLE
                customViewCallback?.onCustomViewHidden()
                customView = null
                customViewCallback = null
            }
        }
    }

    private fun setupSwipeRefresh() {
        binding.swipeRefreshLayout.setColorSchemeResources(
            R.color.primary,
            R.color.accent,
            R.color.success
        )
        binding.swipeRefreshLayout.setOnRefreshListener {
            if (isNetworkAvailable()) {
                binding.webView.reload()
            } else {
                binding.swipeRefreshLayout.isRefreshing = false
                showOfflineView(true)
            }
        }

        // Only allow pull-to-refresh when at the top of the webpage
        binding.webView.viewTreeObserver.addOnScrollChangedListener {
            binding.swipeRefreshLayout.isEnabled = (binding.webView.scrollY == 0)
        }
    }

    private fun setupOfflineRetry() {
        binding.btnRetry.setOnClickListener {
            if (isNetworkAvailable()) {
                showOfflineView(false)
                binding.webView.reload()
            } else {
                Toast.makeText(this, R.string.offline_title, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun setupFabBiometric() {
        binding.fabBiometric.setOnClickListener {
            startBiometricAuthentication()
        }
    }

    fun startBiometricAuthentication() {
        if (!biometricManager.isBiometricAvailable()) {
            Toast.makeText(this, R.string.biometric_not_supported, Toast.LENGTH_SHORT).show()
            return
        }

        if (!biometricManager.isBiometricConfigured()) {
            Toast.makeText(
                this,
                "Connectez-vous d'abord normalement avec votre identifiant pour enregistrer votre empreinte.",
                Toast.LENGTH_LONG
            ).show()
            return
        }

        biometricManager.authenticate(
            activity = this,
            onSuccess = { user, pass, classe ->
                performAutoLogin(user, pass, classe)
            },
            onError = { errMsg ->
                Toast.makeText(this, errMsg, Toast.LENGTH_SHORT).show()
            }
        )
    }

    private fun performAutoLogin(user: String, pass: String, classe: String) {
        val userJson = JSONObject.quote(user)
        val passJson = JSONObject.quote(pass)
        val classeJson = JSONObject.quote(classe)

        val js = """
            (function() {
                try {
                    var u = $userJson;
                    var p = $passJson;
                    var c = $classeJson;
                    if (window.app && typeof window.app.quickLogin === 'function') {
                        window.app.quickLogin(u, p, c || 'teacher');
                    } else {
                        var uInput = document.getElementById('loginUsername');
                        var pInput = document.getElementById('loginPassword');
                        var cInput = document.getElementById('loginClasse');
                        var form = document.getElementById('loginForm');
                        if (cInput && c) {
                            cInput.value = c;
                            if (window.app && typeof window.app.onClasseChanged === 'function') {
                                window.app.onClasseChanged(c);
                            }
                        }
                        if (uInput) uInput.value = u;
                        if (pInput) pInput.value = p;
                        if (form) {
                            form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                        }
                    }
                } catch(e) {
                    console.error('Biometric auto-login error:', e);
                }
            })();
        """.trimIndent()

        binding.webView.evaluateJavascript(js, null)
    }

    private fun injectBridgeScript() {
        val isConfigured = biometricManager.isBiometricConfigured()
        val isAvailable = biometricManager.isBiometricAvailable()
        val savedUser = JSONObject.quote(biometricManager.getSavedUsername())

        val script = """
            (function() {
                window.isAndroidApp = true;
                window.biometricAvailable = $isAvailable;
                window.biometricConfigured = $isConfigured;

                // Insert biometric quick button if available & configured and on login screen
                var form = document.getElementById('loginForm');
                var existingBtn = document.getElementById('androidBioQuickBtn');
                if (form && $isConfigured && !existingBtn) {
                    var container = document.createElement('div');
                    container.id = 'androidBioQuickBtn';
                    container.className = 'mt-3';
                    container.innerHTML = `
                        <button type="button" onclick="if(window.AndroidBridge) window.AndroidBridge.triggerBiometricPrompt();" 
                                class="w-full py-2.5 px-4 rounded-xl border-2 border-blue-500 bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-sm">
                            <span class="text-base">👆</span>
                            <span>Connexion rapide par Empreinte (${savedUser})</span>
                        </button>
                    `;
                    form.parentNode.insertBefore(container, form.nextSibling);
                }

                // Intercept manual login to prompt saving biometric if not saved
                if (form && !form.dataset.bioHooked) {
                    form.dataset.bioHooked = 'true';
                    form.addEventListener('submit', function() {
                        try {
                            var u = document.getElementById('loginUsername')?.value || '';
                            var p = document.getElementById('loginPassword')?.value || '';
                            var c = document.getElementById('loginClasse')?.value || '';
                            if (u && p && window.AndroidBridge) {
                                setTimeout(function() {
                                    var token = localStorage.getItem('auth_token');
                                    if (token) {
                                        window.AndroidBridge.promptSaveBiometric(u, p, c);
                                    }
                                }, 1500);
                            }
                        } catch(e) {}
                    });
                }
            })();
        """.trimIndent()

        binding.webView.evaluateJavascript(script, null)
    }

    private fun checkAndAutoPromptBiometric() {
        if (!hasPromptedAutoBiometric && biometricManager.isBiometricConfigured()) {
            hasPromptedAutoBiometric = true
            Handler(Looper.getMainLooper()).postDelayed({
                // Check if user is currently on login page (no auth_token in localStorage)
                binding.webView.evaluateJavascript(
                    "(function() { return localStorage.getItem('auth_token') ? 'LOGGED_IN' : 'LOGIN_PAGE'; })();"
                ) { result ->
                    if (result != null && result.contains("LOGIN_PAGE")) {
                        startBiometricAuthentication()
                    }
                }
            }, 800)
        }
    }

    fun updateBiometricUi() {
        binding.webView.evaluateJavascript(
            "(function() { return localStorage.getItem('auth_token') ? 'LOGGED_IN' : 'LOGIN_PAGE'; })();"
        ) { result ->
            val isLoggedIn = result != null && result.contains("LOGGED_IN")
            runOnUiThread {
                if (isLoggedIn) {
                    binding.fabBiometric.visibility = View.GONE
                } else if (biometricManager.isBiometricConfigured()) {
                    binding.fabBiometric.visibility = View.VISIBLE
                } else {
                    binding.fabBiometric.visibility = View.GONE
                }
            }
        }
    }

    fun onUserLoggedIn(username: String, @Suppress("UNUSED_PARAMETER") role: String) {
        binding.fabBiometric.visibility = View.GONE
        NotificationHelper.showNotification(
            context = this,
            title = "Connexion réussie",
            message = "Bienvenue sur l'Espace Msalbi, $username !",
            notificationId = 100
        )
    }

    fun onUserLoggedOut() {
        updateBiometricUi()
    }

    private fun showOfflineView(show: Boolean) {
        if (show) {
            binding.offlineContainer.visibility = View.VISIBLE
            binding.swipeRefreshLayout.visibility = View.GONE
            binding.fabBiometric.visibility = View.GONE
        } else {
            binding.offlineContainer.visibility = View.GONE
            binding.swipeRefreshLayout.visibility = View.VISIBLE
            updateBiometricUi()
        }
    }

    private fun isNetworkAvailable(): Boolean {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork ?: return false
        val capabilities = cm.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun setupBackNavigation() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (customView != null) {
                    binding.webView.webChromeClient?.onHideCustomView()
                    return
                }

                if (binding.webView.canGoBack()) {
                    binding.webView.goBack()
                    return
                }

                if (backPressedOnce) {
                    finish()
                } else {
                    backPressedOnce = true
                    Toast.makeText(this@MainActivity, R.string.press_again_to_exit, Toast.LENGTH_SHORT).show()
                    resetBackHandler.postDelayed({ backPressedOnce = false }, 2000)
                }
            }
        })
    }
}
