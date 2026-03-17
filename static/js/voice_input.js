/**
 * LearnSphere Voice Input & Audio Bridge
 * Handles Speech-to-Text and Audio Analysis for Avatar Reactivity
 */

class LearnSphereVoiceUI {
    constructor(micBtnId, inputId, onComplete) {
        this.micBtn = document.getElementById(micBtnId);
        this.input = document.getElementById(inputId);
        this.onComplete = onComplete;
        this.voiceIndicator = document.getElementById('voice-indicator');

        this.recognition = null;
        this.isListening = false;

        this.initSpeech();
        this.bindEvents();
    }

    initSpeech() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("Speech Recognition not supported in this browser.");
            this.micBtn.title = "Voice Input not supported in this browser (Use Chrome or Edge)";
            this.micBtn.style.opacity = '0.5';
            this.micBtn.addEventListener('click', () => {
                alert("Voice Input is not supported by your current browser. Please use Chrome or Edge for the best experience.");
            });
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.isListening = true;
            this.micBtn.classList.add('listening');
            this.voiceIndicator.classList.remove('hidden');
        };

        this.recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0])
                .map(result => result.transcript)
                .join('');

            this.input.value = transcript;
        };

        this.recognition.onend = () => {
            this.isListening = false;
            this.micBtn.classList.remove('listening');
            this.voiceIndicator.classList.add('hidden');

            // Auto submit after a short delay if we have input
            if (this.input.value.trim().length > 3) {
                setTimeout(() => {
                    if (this.onComplete) this.onComplete(this.input.value);
                }, 800);
            }
        };

        this.recognition.onerror = (event) => {
            console.error("Speech Recognition Error:", event.error);
            if (event.error === 'not-allowed') {
                alert("Microphone access was denied. Please allow microphone permissions in your browser settings to use voice input.");
            } else if (event.error === 'network') {
                alert("Network error: The browser's speech recognition service is unreachable. This usually happens on unstable connections or if the browser service is blocked. Try refreshing or using a different browser (Chrome/Edge).");
            } else {
                alert("Voice recognition error: " + event.error);
            }
            this.stop();
        };
    }

    bindEvents() {
        if (!this.micBtn) return;
        this.micBtn.addEventListener('click', () => {
            if (this.isListening) this.stop();
            else this.start();
        });
    }

    start() {
        if (this.recognition) this.recognition.start();
    }

    stop() {
        if (this.recognition) this.recognition.stop();
    }
}

/**
 * Audio Frequency Analyzer
 * Extracts volume data from Audio elements for the avatar
 */
class AudioAnalyzer {
    constructor() {
        this.context = null;
        this.analyser = null;
        this.sourceMap = new WeakMap();
    }

    onPlay(audioElement, callback) {
        if (!this.context) {
            this.context = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.context.createAnalyser();
            this.analyser.fftSize = 256;
            this.analyser.connect(this.context.destination);
        }

        if (this.context.state === 'suspended') {
            this.context.resume();
        }

        let source;
        if (this.sourceMap.has(audioElement)) {
            source = this.sourceMap.get(audioElement);
        } else {
            source = this.context.createMediaElementSource(audioElement);
            source.connect(this.analyser);
            this.sourceMap.set(audioElement, source);
        }

        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

        const tick = () => {
            if (audioElement.paused || audioElement.ended) {
                callback(0);
                return;
            }
            this.analyser.getByteFrequencyData(dataArray);

            // Calculate average volume
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
                sum += dataArray[i];
            }
            const average = sum / dataArray.length;
            callback(average);
            requestAnimationFrame(tick);
        };

        tick();
    }
}

window.LearnSphereVoiceUI = LearnSphereVoiceUI;
window.AudioAnalyzer = AudioAnalyzer;
