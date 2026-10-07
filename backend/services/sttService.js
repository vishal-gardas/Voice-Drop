const axios = require("axios");
const EventEmitter = require("events");

class SttService extends EventEmitter {
  constructor() {
    super();
    this.pythonBackendUrl =
      process.env.PYTHON_BACKEND_URL || "http://localhost:5000";
    this.isProcessing = false;
    this.audioChunks = []; // Array of Buffer objects (raw mu-law bytes)
    this.silenceTimer = null;
    this.isSpeaking = false;
    this.speechStartTime = 0;

    // Silence detection & Debounce settings
    this.SILENCE_THRESHOLD_MS = 1000; // 1.0 second of silence after speech ends
    this.MIN_AUDIO_BYTES = 4800; // At least ~600ms of audio (8000 bytes/sec for 8kHz mu-law)
    this.MAX_AUDIO_BYTES = 8000 * 15; // Max 15 seconds per single utterance
    this.ENERGY_THRESHOLD = 300; // Amplitude threshold to differentiate voice from line hiss
    this.MIN_TRANSCRIPT_LENGTH = 2; // Minimum characters to process

    // Precompute mu-law to linear PCM lookup table for instant energy calculation
    this.mulawTable = this.buildMulawTable();

    console.log(
      `[STT] Self-Hosted Whisper STT Service initialized (Endpoint: ${this.pythonBackendUrl}/api/speech/stt)`,
    );
  }

  buildMulawTable() {
    const table = new Int16Array(256);
    for (let i = 0; i < 256; i++) {
      let u = ~i & 0xff;
      let sign = u & 0x80 ? -1 : 1;
      let exponent = (u >> 4) & 0x07;
      let mantissa = u & 0x0f;
      let sample = sign * (((mantissa << 3) + 0x84) << exponent) - sign * 0x84;
      table[i] = sample;
    }
    return table;
  }

  /**
   * Fast RMS energy calculation for a 20ms mu-law buffer
   */
  calculateChunkEnergy(buffer) {
    if (!buffer || buffer.length === 0) return 0;
    let sum = 0;
    for (let i = 0; i < buffer.length; i++) {
      const sample = this.mulawTable[buffer[i]];
      sum += sample * sample;
    }
    return Math.sqrt(sum / buffer.length);
  }

  /**
   * Receives incoming 8kHz mu-law audio chunk from Twilio WebSocket stream
   */
  sendAudio(audioPayload) {
    if (!audioPayload) return;

    const chunkBuffer = Buffer.from(audioPayload, "base64");
    const energy = this.calculateChunkEnergy(chunkBuffer);

    if (energy > this.ENERGY_THRESHOLD) {
      // User is speaking (Voice Activity Detected)
      if (!this.isSpeaking) {
        this.isSpeaking = true;
        this.speechStartTime = Date.now();
        console.log(`[STT] 🎙️ Speech started (RMS: ${Math.round(energy)})`);
      }

      this.clearSilenceTimer();
      this.audioChunks.push(chunkBuffer);

      // Auto-flush if utterance gets too long (e.g. 15 seconds)
      const currentBytes = this.audioChunks.reduce(
        (acc, c) => acc + c.length,
        0,
      );
      if (currentBytes > this.MAX_AUDIO_BYTES) {
        console.log(
          `[STT] Max utterance duration reached, processing chunk...`,
        );
        this.processBufferedAudio();
      }
    } else {
      // Line is silent or background noise
      if (this.isSpeaking) {
        // Keep buffering a small amount of silence tail for natural word ending
        this.audioChunks.push(chunkBuffer);

        // Start silence countdown to finalize utterance
        if (!this.silenceTimer) {
          this.silenceTimer = setTimeout(() => {
            console.log(
              `[STT] Silence threshold reached. Transcribing utterance...`,
            );
            this.processBufferedAudio();
          }, this.SILENCE_THRESHOLD_MS);
        }
      }
    }
  }

  /**
   * Concatenates buffered mu-law chunks and sends to local Python Whisper STT
   */
  async processBufferedAudio() {
    this.clearSilenceTimer();
    this.isSpeaking = false;

    if (this.isProcessing) {
      console.log("[STT] Already processing previous utterance, deferring...");
      return;
    }

    const totalChunks = this.audioChunks.length;
    if (totalChunks === 0) return;

    const combinedBuffer = Buffer.concat(this.audioChunks);
    this.audioChunks = []; // Reset buffer immediately

    // Skip if audio is too short (e.g. just a cough or key press)
    if (combinedBuffer.length < this.MIN_AUDIO_BYTES) {
      console.log(
        `[STT] Skipped short noise burst (${combinedBuffer.length} bytes)`,
      );
      return;
    }

    this.isProcessing = true;
    const base64Audio = combinedBuffer.toString("base64");
    const startTime = Date.now();

    try {
      console.log(
        `[STT] 🚀 Sending ${(combinedBuffer.length / 8000).toFixed(2)}s audio to Whisper STT...`,
      );

      const response = await axios.post(
        `${this.pythonBackendUrl}/api/speech/stt`,
        {
          audio: base64Audio,
          language: "en",
        },
        {
          headers: { "Content-Type": "application/json" },
          timeout: 7000,
        },
      );

      const data = response.data;
      const transcript = (data.transcript || "").trim();
      const elapsed = Date.now() - startTime;

      console.log(
        `[STT] Received: "${transcript}" (Confidence: ${data.confidence || 0.8}, Took: ${elapsed}ms)`,
      );

      if (this.shouldProcessTranscript(transcript)) {
        console.log(`[STT] ✅ Emitting speech_transcribed: "${transcript}"`);
        this.emit("speech_transcribed", transcript);
      }
    } catch (error) {
      console.error(
        "❌ [STT] Error calling local Python Whisper STT service:",
        error.message,
      );
    } finally {
      this.isProcessing = false;
    }
  }

  shouldProcessTranscript(transcript) {
    if (!transcript || transcript.length < this.MIN_TRANSCRIPT_LENGTH) {
      return false;
    }

    // Skip single filler words
    const fillerWords = ["um", "uh", "ah", "er", "hmm", "yeah", "ok", "you"];
    const words = transcript
      .toLowerCase()
      .split(" ")
      .filter((w) => w.length > 0);

    if (words.length === 1 && fillerWords.includes(words[0])) {
      console.log(`[STT] Skipping filler word: "${transcript}"`);
      return false;
    }

    return true;
  }

  clearSilenceTimer() {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
  }

  forceProcess() {
    if (this.audioChunks.length > 0) {
      this.processBufferedAudio();
    }
  }

  close() {
    this.clearSilenceTimer();
    this.audioChunks = [];
    this.isSpeaking = false;
    this.isProcessing = false;
  }
}

module.exports = SttService;
