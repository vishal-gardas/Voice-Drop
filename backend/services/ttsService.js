const axios = require("axios");

class TtsService {
  constructor() {
    this.pythonBackendUrl =
      process.env.PYTHON_BACKEND_URL || "http://localhost:5000";
    this.isSpeaking = false;
    this.speechQueue = [];
    this.mulawTable = this.buildMulawTable();
    this.mulawToLinearTable = this.buildMulawToLinearTable();

    console.log(
      `[TTS] Self-Hosted Neural TTS Service initialized (Endpoint: ${this.pythonBackendUrl}/api/speech/tts)`,
    );
  }

  /**
   * Pre-build µ-law conversion lookup table for volume boost
   */
  buildMulawTable() {
    const table = new Array(65536);
    for (let i = 0; i < 65536; i++) {
      const sample = i - 32768; // Convert to signed 16-bit
      table[i] = this.linearToMulaw(sample);
    }
    return table;
  }

  /**
   * Pre-build µ-law to linear PCM decoding table for volume boost
   */
  buildMulawToLinearTable() {
    const table = new Array(256);
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
   * Convert linear PCM sample to µ-law (Exact G.711 ITU-T specification)
   */
  linearToMulaw(sample) {
    const BIAS = 0x84;
    const CLIP = 32635;
    let sign = 0;
    if (sample < 0) {
      sample = -sample;
      sign = 0x80;
    }
    if (sample > CLIP) sample = CLIP;
    sample += BIAS;
    let exponent = 7;
    for (
      let expMask = 0x4000;
      (sample & expMask) === 0 && exponent > 0;
      expMask >>= 1
    ) {
      exponent--;
    }
    let mantissa = (sample >> (exponent + 3)) & 0x0f;
    return ~(sign | (exponent << 4) | mantissa) & 0xff;
  }

  /**
   * Boost audio volume of µ-law buffer cleanly without clipping
   */
  boostMulawVolume(mulawBuffer, gain = 2.0) {
    if (!mulawBuffer || !mulawBuffer.length) return mulawBuffer;
    const boosted = Buffer.alloc(mulawBuffer.length);
    for (let i = 0; i < mulawBuffer.length; i++) {
      let sample = Math.round(this.mulawToLinearTable[mulawBuffer[i]] * gain);
      if (sample > 32635) sample = 32635;
      if (sample < -32635) sample = -32635;
      boosted[i] = this.mulawTable[(sample + 32768) & 0xffff];
    }
    return boosted;
  }

  /**
   * Main TTS function - Routes to local Python Neural TTS endpoint
   * @param {string} text - Text to speak
   * @param {string} lang - Language code ('en', 'hi', 'en-IN')
   */
  async textToSpeech(text, lang = "en") {
    if (!text || text.trim().length === 0) {
      console.log("[TTS] No text provided");
      return null;
    }

    try {
      console.log(
        `[TTS] 🔊 Converting text to speech locally: "${text.substring(0, 50)}..." [Lang: ${lang}]`,
      );
      const startTime = Date.now();
      return await this.generateLocalTTS(text, lang, startTime);
    } catch (error) {
      console.error(
        "[TTS] Error generating speech:",
        error.response?.data || error.message,
      );
      return null;
    }
  }

  /**
   * Generate TTS using local Python Neural TTS service
   */
  async generateLocalTTS(text, lang, startTime) {
    const response = await axios.post(
      `${this.pythonBackendUrl}/api/speech/tts`,
      {
        text: text,
        language: lang || "en",
      },
      {
        headers: { "Content-Type": "application/json" },
        timeout: 30000,
      },
    );

    if (!response.data || !response.data.audio) {
      throw new Error(
        response.data?.error || "Empty audio returned from Python TTS",
      );
    }

    const rawMulawBuffer = Buffer.from(response.data.audio, "base64");

    // Apply slight volume boost for telephony clarity
    const boostedBuffer = this.boostMulawVolume(rawMulawBuffer, 1.8);
    const audioBase64 = boostedBuffer.toString("base64");
    const totalTime = Date.now() - startTime;

    console.log(
      `[TTS] ✅ Local Neural TTS completed in ${totalTime}ms - Audio payload: ${audioBase64.length} chars`,
    );
    return audioBase64;
  }

  /**
   * Add text to speech queue
   * @param {string} text
   * @param {string} lang
   */
  async queueSpeech(text, lang = "en") {
    return new Promise((resolve) => {
      this.speechQueue.push({ text, lang, resolve });
      this.processQueue();
    });
  }

  /**
   * Process queued TTS requests
   */
  async processQueue() {
    if (this.isSpeaking || this.speechQueue.length === 0) return;

    this.isSpeaking = true;
    const { text, lang, resolve } = this.speechQueue.shift();

    try {
      const audio = await this.textToSpeech(text, lang);
      resolve(audio);
    } catch (error) {
      console.error("[TTS] Queue processing error:", error);
      resolve(null);
    }

    this.isSpeaking = false;
    setTimeout(() => this.processQueue(), 50);
  }
}

// Export singleton instance
const ttsService = new TtsService();

module.exports = {
  TtsService,
  textToSpeech: (text, lang = "en") => ttsService.textToSpeech(text, lang),
  queueSpeech: (text, lang = "en") => ttsService.queueSpeech(text, lang),
};
