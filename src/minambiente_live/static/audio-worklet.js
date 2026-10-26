/* PCM16 mono a 16 kHz con promedio ponderado y estado entre bloques. */
class PCM16Capture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / 16000;
    this.remaining = this.ratio;
    this.sum = 0;
    this.buffer = new Int16Array(3200);
    this.index = 0;
    this.energy = 0;
    this.port.onmessage = e => {
      if (e.data === 'flush') { this.flush(); this.port.postMessage({flushed: true}); }
    };
  }
  flush() {
    if (!this.index) return;
    const samples = this.buffer.slice(0, this.index);
    this.port.postMessage({pcm: samples.buffer, rms: Math.sqrt(this.energy / this.index)}, [samples.buffer]);
    this.index = 0;
    this.energy = 0;
  }
  process(inputs, outputs) {
    const channels = inputs[0];
    // Salida explícitamente muda: nunca reproduce la mezcla por altavoces.
    for (const channel of outputs[0] || []) channel.fill(0);
    if (!channels || !channels.length) return true;
    for (let i = 0; i < channels[0].length; i++) {
      let value = 0;
      for (const ch of channels) value += ch[i] || 0;
      value /= channels.length;
      let weight = 1;
      while (weight > 1e-8) {
        const part = Math.min(weight, this.remaining);
        this.sum += value * part;
        weight -= part;
        this.remaining -= part;
        if (this.remaining < 1e-8) {
          const sample = Math.max(-1, Math.min(1, this.sum / this.ratio));
          this.buffer[this.index++] = Math.round(sample * (sample < 0 ? 32768 : 32767));
          this.energy += sample * sample;
          this.sum = 0;
          this.remaining = this.ratio;
          if (this.index === this.buffer.length) this.flush();
        }
      }
    }
    return true;
  }
}
registerProcessor('pcm16-capture', PCM16Capture);
