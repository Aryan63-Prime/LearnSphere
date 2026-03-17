# 🎓 LearnSphere

AI-Powered Learning Platform with multiple learning modalities powered by Google Gemini 2.0 Flash.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![Gemini](https://img.shields.io/badge/Gemini-2.0%20Flash-purple.svg)

## ✨ Features

- **📖 Text Explanation** - Get comprehensive explanations with adjustable depth levels
- **⚡ Code Generation** - Generate production-ready code with dependencies and documentation
- **🎵 Audio Learning** - Listen to AI-generated audio lessons using text-to-speech
- **🖼️ Visual Learning** - Understand concepts through AI-generated visual descriptions

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Aryan63-Prime/LearnSphere.git
   cd LearnSphere
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   # Create .env file and add your API key
   GEMINI_API_KEY=your_gemini_api_key_here
   FLASK_SECRET_KEY=your_secret_key_here
   FLASK_DEBUG=True
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open browser**
   Navigate to `http://localhost:5000`

## 📁 Project Structure

```
LearnSphere/
├── app.py                 # Flask application
├── config.py              # Configuration management
├── genai_utils.py         # Gemini AI integration
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in repo)
├── .gitignore
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Home page
│   ├── text_explanation.html
│   ├── code_generation.html
│   ├── audio_learning.html
│   └── image_visualization.html
└── static/
    ├── css/
    │   └── style.css      # Styling
    └── js/
        └── main.js        # JavaScript utilities
```

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, Flask |
| Frontend | HTML5, CSS3, JavaScript |
| AI | Google Gemini 2.0 Flash |
| Audio | Web Speech API |
| Styling | Vanilla CSS with glassmorphism |

## 📝 Usage

### Text Explanation
1. Navigate to the Text Explanation page
2. Enter your topic (e.g., "neural networks")
3. Select depth level (Brief/Comprehensive/In-Depth)
4. Click "Generate Explanation"

### Code Generation
1. Navigate to Code Generation page
2. Enter what code you need (e.g., "binary search implementation")
3. Select complexity level
4. Generate and download the code

### Audio Learning
1. Navigate to Audio Learning page
2. Enter your topic
3. Select narration style
4. Generate and listen using built-in player

### Visual Learning
1. Navigate to Visual Learning page
2. Enter concept to visualize
3. Get AI-generated visual descriptions

## 🔐 Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `FLASK_SECRET_KEY` | Flask secret key for sessions |
| `FLASK_DEBUG` | Enable debug mode (True/False) |

## 👥 Team

**Developed by Hackaholics Squad**

| Member | Role |
|--------|------|
| Aryan Patel | Team Member |
| Chetan Singh | Team Member |
| Tejas Singh Nirvan | Team Member |

## 📄 License

MIT License - feel free to use this project for learning and development.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
