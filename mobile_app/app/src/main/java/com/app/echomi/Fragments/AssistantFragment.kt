package com.app.echomi.Fragments

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.airbnb.lottie.LottieAnimationView
import com.app.echomi.Adapter.PromptsAdapter
import com.app.echomi.Network.RetrofitInstance
import com.app.echomi.R
import com.app.echomi.data.Prompt
import com.app.echomi.data.UpdatePromptRequest
import kotlinx.coroutines.launch

class AssistantFragment : Fragment() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: PromptsAdapter
    private lateinit var progressBar: ProgressBar
    private lateinit var lottieAnimationView: LottieAnimationView

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_assistant, container, false)
        recyclerView = view.findViewById(R.id.promptsRecyclerView)
        progressBar = view.findViewById(R.id.progressBar)
        lottieAnimationView = view.findViewById(R.id.lottieAnimationView)

        setupRecyclerView()
        fetchPrompts()

        // Configure Lottie animation with error handling
        try {
            lottieAnimationView.speed = 1.0f
            lottieAnimationView.playAnimation() // Ensure animation plays (redundant with autoPlay=true)
        } catch (e: Exception) {
            Toast.makeText(context, "Failed to load animation: ${e.message}", Toast.LENGTH_LONG).show()
            lottieAnimationView.visibility = View.GONE // Hide animation view on failure
        }

        // Add failure listener for Lottie animation
        lottieAnimationView.addLottieOnCompositionLoadedListener { composition ->
            if (composition == null) {
                Toast.makeText(context, "Failed to load Lottie animation", Toast.LENGTH_LONG).show()
                lottieAnimationView.visibility = View.GONE // Hide animation view on failure
            }
        }

        return view
    }

    private fun setupRecyclerView() {
        adapter = PromptsAdapter(emptyList()) { prompt ->
            showEditPromptDialog(prompt)
        }
        recyclerView.adapter = adapter
        recyclerView.layoutManager = LinearLayoutManager(context)
    }

    private fun fetchPrompts() {
        progressBar.visibility = View.GONE
        lottieAnimationView.visibility = View.VISIBLE // Show animation
        recyclerView.visibility = View.GONE // Keep RecyclerView hidden
        lifecycleScope.launch {
            try {
                val response = RetrofitInstance.api.getPrompts()
                if (response.isSuccessful) {
                    adapter.updatePrompts(response.body() ?: emptyList())
                    // Optionally show RecyclerView and hide animation after loading
                    // recyclerView.visibility = View.VISIBLE
                    // lottieAnimationView.visibility = View.GONE
                } else {
                    Toast.makeText(context, "Failed to load prompts", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                progressBar.visibility = View.GONE
            }
        }
    }

    private fun showEditPromptDialog(prompt: Prompt) {
        val editText = EditText(requireContext()).apply {
            setText(prompt.instructions)
            val padding = (16 * resources.displayMetrics.density).toInt()
            setPadding(padding, padding, padding, padding)
        }

        AlertDialog.Builder(requireContext())
            .setTitle("Edit Instructions for ${prompt.promptType.replaceFirstChar { it.uppercase() }}")
            .setView(editText)
            .setPositiveButton("Save") { _, _ ->
                val newInstructions = editText.text.toString()
                updatePrompt(prompt.promptType, newInstructions)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun updatePrompt(promptType: String, instructions: String) {
        progressBar.visibility = View.GONE
        lifecycleScope.launch {
            try {
                val request = UpdatePromptRequest(instructions)
                val response = RetrofitInstance.api.updatePrompt(promptType, request)
                if (response.isSuccessful) {
                    Toast.makeText(context, "Prompt saved!", Toast.LENGTH_SHORT).show()
                    fetchPrompts() // Refresh the list with the updated data
                } else {
                    throw Exception("Failed to update prompt")
                }
            } catch (e: Exception) {
                Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                progressBar.visibility = View.GONE
            }
        }
    }

    override fun onPause() {
        super.onPause()
        // Pause animation when fragment is paused
        if (::lottieAnimationView.isInitialized) {
            lottieAnimationView.pauseAnimation()
        }
    }

    override fun onResume() {
        super.onResume()
        // Resume animation when fragment is resumed
        if (::lottieAnimationView.isInitialized) {
            try {
                lottieAnimationView.playAnimation()
            } catch (e: Exception) {
                Toast.makeText(context, "Failed to resume animation: ${e.message}", Toast.LENGTH_LONG).show()
                lottieAnimationView.visibility = View.GONE
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        // Cancel animation when view is destroyed
        if (::lottieAnimationView.isInitialized) {
            lottieAnimationView.cancelAnimation()
        }
    }
}