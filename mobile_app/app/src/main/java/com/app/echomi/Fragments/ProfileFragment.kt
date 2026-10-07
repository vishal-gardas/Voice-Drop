package com.app.echomi.Fragments

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.airbnb.lottie.LottieAnimationView
import com.app.echomi.ContactSelectionScreen
import com.app.echomi.R
import com.app.echomi.SplashScreen
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.material.button.MaterialButton
import com.google.firebase.auth.ktx.auth
import com.google.firebase.ktx.Firebase

class ProfileFragment : Fragment() {

    private lateinit var loadingAnimationView: LottieAnimationView
    private lateinit var nameTextView: TextView
    private lateinit var emailTextView: TextView
    private lateinit var manageContactsButton: MaterialButton
    private lateinit var logoutButton: MaterialButton

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_profile, container, false)

        nameTextView = view.findViewById(R.id.nameTextView)
        emailTextView = view.findViewById(R.id.emailTextView)
        manageContactsButton = view.findViewById(R.id.manageContactsButton)
        logoutButton = view.findViewById(R.id.logoutButton)
        loadingAnimationView = view.findViewById(R.id.loadingAnimationView)

        // Show loading animation initially
        loadingAnimationView.visibility = View.VISIBLE
        nameTextView.visibility = View.GONE
        emailTextView.visibility = View.GONE
        manageContactsButton.visibility = View.GONE
        logoutButton.visibility = View.GONE

        // Configure Lottie animation with error handling
        try {
            loadingAnimationView.speed = 1.0f
            loadingAnimationView.playAnimation() // Ensure animation plays (redundant with autoPlay=true)
        } catch (e: Exception) {
            Toast.makeText(context, "Failed to load animation: ${e.message}", Toast.LENGTH_LONG).show()
            loadingAnimationView.visibility = View.GONE // Hide animation on failure
        }

        // Add failure listener for Lottie animation
        loadingAnimationView.addLottieOnCompositionLoadedListener { composition ->
            if (composition == null) {
                Toast.makeText(context, "Failed to load Lottie animation", Toast.LENGTH_LONG).show()
                loadingAnimationView.visibility = View.GONE // Hide animation on failure
                // Show UI elements as fallback
                nameTextView.visibility = View.VISIBLE
                emailTextView.visibility = View.VISIBLE
                manageContactsButton.visibility = View.VISIBLE
                logoutButton.visibility = View.VISIBLE
            }
        }

        // Simulate loading user data (e.g., fetching from Firebase)
        simulateUserDataLoading()

        return view
    }

    private fun simulateUserDataLoading() {
        // Simulate a brief loading delay (e.g., 1 second) to mimic data fetching
        Handler(Looper.getMainLooper()).postDelayed({
            try {
                val currentUser = Firebase.auth.currentUser
                nameTextView.text = currentUser?.displayName ?: "No Name"
                emailTextView.text = currentUser?.email ?: "No Email"

                // Hide loading animation and show UI elements
                loadingAnimationView.visibility = View.GONE
                nameTextView.visibility = View.VISIBLE
                emailTextView.visibility = View.VISIBLE
                manageContactsButton.visibility = View.VISIBLE
                logoutButton.visibility = View.VISIBLE

                // Set button click listeners
                manageContactsButton.setOnClickListener {
                    startActivity(Intent(activity, ContactSelectionScreen::class.java))
                }

                logoutButton.setOnClickListener {
                    // Show loading animation during logout
                    loadingAnimationView.visibility = View.VISIBLE
                    nameTextView.visibility = View.GONE
                    emailTextView.visibility = View.GONE
                    manageContactsButton.visibility = View.GONE
                    logoutButton.visibility = View.GONE

                    // Sign out from Firebase
                    Firebase.auth.signOut()

                    // Sign out from Google
                    val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN).build()
                    val googleSignInClient = GoogleSignIn.getClient(requireActivity(), gso)
                    googleSignInClient.signOut().addOnCompleteListener {
                        // Navigate to SplashScreen
                        val intent = Intent(activity, SplashScreen::class.java)
                        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        startActivity(intent)
                        requireActivity().finish()
                    }
                }
            } catch (e: Exception) {
                Toast.makeText(context, "Error loading user data: ${e.message}", Toast.LENGTH_LONG).show()
                loadingAnimationView.visibility = View.GONE
                nameTextView.visibility = View.VISIBLE
                emailTextView.visibility = View.VISIBLE
                manageContactsButton.visibility = View.VISIBLE
                logoutButton.visibility = View.VISIBLE
            }
        }, 1000) // 1-second delay to simulate loading
    }

    override fun onPause() {
        super.onPause()
        // Pause animation when fragment is paused
        if (::loadingAnimationView.isInitialized) {
            loadingAnimationView.pauseAnimation()
        }
    }

    override fun onResume() {
        super.onResume()
        // Resume animation when fragment is resumed
        if (::loadingAnimationView.isInitialized) {
            try {
                loadingAnimationView.playAnimation()
            } catch (e: Exception) {
                Toast.makeText(context, "Failed to resume animation: ${e.message}", Toast.LENGTH_LONG).show()
                loadingAnimationView.visibility = View.GONE
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        // Cancel animation when view is destroyed
        if (::loadingAnimationView.isInitialized) {
            loadingAnimationView.cancelAnimation()
        }
    }
}