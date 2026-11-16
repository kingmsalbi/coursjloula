package com.msalbi.espacepedagogique

import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.webkit.CookieManager
import android.webkit.URLUtil
import android.widget.Toast

object DownloadHelper {

    fun downloadFile(
        context: Context,
        url: String,
        userAgent: String?,
        contentDisposition: String?,
        mimetype: String?
    ) {
        try {
            val uri = Uri.parse(url)
            val request = DownloadManager.Request(uri)

            var fileName = URLUtil.guessFileName(url, contentDisposition, mimetype)
            if (fileName.isNullOrBlank() || fileName == "downloadfile.bin") {
                val lastSegment = uri.lastPathSegment
                if (!lastSegment.isNullOrBlank()) {
                    fileName = lastSegment
                }
            }

            val cookies = CookieManager.getInstance().getCookie(url)
            if (!cookies.isNullOrEmpty()) {
                request.addRequestHeader("Cookie", cookies)
            }
            if (!userAgent.isNullOrEmpty()) {
                request.addRequestHeader("User-Agent", userAgent)
            }

            request.setTitle(fileName)
            request.setDescription("Espace Pédagogique Msalbi")
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName)
            request.setAllowedOverMetered(true)
            request.setAllowedOverRoaming(true)

            val downloadManager = context.getSystemService(Context.DOWNLOAD_SERVICE) as? DownloadManager
            if (downloadManager != null) {
                downloadManager.enqueue(request)
                val msg = context.getString(R.string.download_started, fileName)
                Toast.makeText(context, msg, Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(context, R.string.download_failed, Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(context, "Erreur téléchargement: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }
}
