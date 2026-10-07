package com.app.echomi.Network

import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.tasks.await
import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val requestBuilder = originalRequest.newBuilder()
            .header("Bypass-Tunnel-Reminder", "true")
            .header("User-Agent", "VoiceDropAndroidApp")

        val currentUser = FirebaseAuth.getInstance().currentUser
        if (currentUser == null) {
            return chain.proceed(requestBuilder.build())
        }

        val token = runBlocking {
            try {
                currentUser.getIdToken(true).await()?.token
            } catch (e: Exception) {
                null
            }
        }

        if (token != null) {
            requestBuilder.header("Authorization", "Bearer $token")
        }

        return chain.proceed(requestBuilder.build())
    }
}