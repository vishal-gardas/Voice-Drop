package com.app.echomi

import android.media.MediaPlayer
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.app.echomi.Adapter.TranscriptAdapter
import com.app.echomi.Network.RetrofitInstance
import com.app.echomi.data.CallLog
import kotlinx.coroutines.launch
import java.util.Date

class CallDetailScreen : AppCompatActivity() {
    private var mediaPlayer: MediaPlayer? = null
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var transcriptAdapter: TranscriptAdapter
    private lateinit var transcriptRecyclerView: RecyclerView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_call_detail_screen)

        val callId = intent.getStringExtra("CALL_ID")
        if (callId == null) {
            Toast.makeText(this, "Error: Call ID not found", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        val toolbar: Toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        toolbar.setNavigationOnClickListener { finish() }

        setupTranscriptRecyclerView()
        fetchCallDetails(callId)
    }

    private fun setupTranscriptRecyclerView() {
        transcriptRecyclerView = findViewById(R.id.transcriptRecyclerView)
        transcriptAdapter = TranscriptAdapter()
        transcriptRecyclerView.apply {
            layoutManager = LinearLayoutManager(this@CallDetailScreen)
            adapter = transcriptAdapter
        }
    }

    private fun fetchCallDetails(callId: String) {
        lifecycleScope.launch {
            try {
                val response = RetrofitInstance.api.getCallLogById(callId)
                if (response.isSuccessful) {
                    val log = response.body()
                    if (log != null) {
                        bindDataToUi(log)
                    } else {
                        throw Exception("Call log data is null")
                    }
                } else {
                    throw Exception("Failed to load details")
                }
            } catch (e: Exception) {
                Toast.makeText(this@CallDetailScreen, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun bindDataToUi(log: CallLog) {
        findViewById<TextView>(R.id.callerNumberTextView).text = log.callerNumber
        findViewById<TextView>(R.id.summaryTextView).text = log.summary ?: "No summary provided."

        // Format the date better
        val formattedDate = try {
            val date = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", java.util.Locale.getDefault()).parse(log.startTime)
            java.text.SimpleDateFormat("MMM dd, yyyy 'at' hh:mm a", java.util.Locale.getDefault()).format(date ?: Date())
        } catch (e: Exception) {
            log.startTime.substring(0, 10) // fallback
        }
        findViewById<TextView>(R.id.dateTimeTextView).text = formattedDate

        // Setup the recording player if a URL exists
        if (!log.recordingUrl.isNullOrEmpty()) {
            setupMediaPlayer(log.recordingUrl)
        }

        // Display transcript
        if (log.transcript.isNotEmpty()) {
            transcriptAdapter.updateTranscript(log.transcript)
            findViewById<TextView>(R.id.transcriptHeaderTextView)?.text = "Conversation Transcript (${log.transcript.size} messages)"
        } else {
            findViewById<TextView>(R.id.transcriptHeaderTextView)?.text = "No transcript available"
        }
    }

    private fun setupMediaPlayer(url: String) {
        val playerLayout: LinearLayout = findViewById(R.id.recordingPlayerLayout)
        val playPauseButton: ImageButton = findViewById(R.id.playPauseButton)
        val seekBar: SeekBar = findViewById(R.id.seekBar)
        playerLayout.visibility = View.VISIBLE

        mediaPlayer = MediaPlayer().apply {
            setDataSource(url)
            prepareAsync()
            setOnPreparedListener { mp ->
                seekBar.max = mp.duration
                playPauseButton.setOnClickListener {
                    if (isPlaying) {
                        pause()
                        playPauseButton.setImageResource(R.drawable.play) // Change to your play icon
                    } else {
                        start()
                        playPauseButton.setImageResource(R.drawable.pause) // Change to your pause icon
                        updateSeekBar()
                    }
                }
            }
            setOnCompletionListener {
                playPauseButton.setImageResource(R.drawable.play)
                seekBar.progress = 0
            }
        }

        seekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) mediaPlayer?.seekTo(progress)
            }
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {}
        })
    }

    private fun updateSeekBar() {
        if (mediaPlayer?.isPlaying == true) {
            findViewById<SeekBar>(R.id.seekBar).progress = mediaPlayer!!.currentPosition
            handler.postDelayed({ updateSeekBar() }, 500)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        mediaPlayer?.release()
        mediaPlayer = null
    }
}