# Gemini Copilot

Gemini Copilot is an advanced AI-powered chatbot application that leverages the power of Google's Gemini API to provide intelligent, context-aware responses. This desktop application offers a user-friendly interface for interacting with AI, managing multiple conversations, and analyzing various types of media.

![Gemini Copilot Screenshot](logo.png)

## Features

- **AI-Powered Conversations**: Utilizes Google's Gemini API for generating human-like responses.
- **Multi-Modal Input**: Supports text, images, audio, and video inputs for comprehensive AI analysis.
- **Multiple Chat Sessions**: Manage and switch between different conversations easily.
- **File Upload and Analysis**: Upload and analyze various file types, including images, audio, and video.
- **Text-to-Speech**: Convert AI responses to speech for an enhanced interactive experience.
- **Conversation History**: Automatically saves and loads chat history for continued interactions.
- **User-Friendly Interface**: Built with tkinter and ttkbootstrap for a modern, intuitive design.
- **Customizable AI Models**: Choose between different Gemini models for varied capabilities.
- **Context Menu**: Right-click functionality for easy access to features like response regeneration.
- **Detailed Logging**: Comprehensive logging system for troubleshooting and performance monitoring.

## Prerequisites

Before you begin, ensure you have the following:

- Python 3.7 or higher
- A Gemini API key from Google (sign up at [Google AI Studio](https://makersuite.google.com/app/apikey))

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/robotic-s/Gemini-Copilot.git
   cd Gemini-Copilot
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up your Gemini API key:
   - Create a file named `.env` in the project root directory
   - Add the following line to the file:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```
   - Replace `your_api_key_here` with your actual Gemini API key
5. On Linux
   - Install Tkinter
     ```
     sudo apt install python3-tk
     ```
   -Install Port audio
     ```
      sudo apt update
      sudo apt install portaudio19-dev

     ```
   -Then install requirements.txt

## Usage

To launch Gemini Copilot:
-Make sure you have placed you api key correctly in gemini api key in file!!

```
python gemini_copilot.py
```

### Getting Started

1. **Start a New Chat**: Click the "New Chat" button to begin a fresh conversation.
2. **Select a Model**: Choose your preferred Gemini model from the dropdown menu.
3. **Send a Message**: Type your message in the input field and press Enter or click the Send button.
4. **Upload Files**: Click the paperclip icon to upload images, audio, or video for AI analysis.
5. **Use Text-to-Speech**: Append "/speak" to your message to have the AI response read aloud.

### Advanced Features

- **Regenerate Response**: Right-click on the chat area and select "Regenerate response" to get a new AI reply.
- **Switch Conversations**: Select different chats from the list on the left to switch between conversations.
- **View Conversation Details**: Each chat displays creation time, date, and a unique ID for easy reference.

### Tips for Best Results

- Be clear and specific in your queries for more accurate responses.
- When uploading files, ensure they are in supported formats (PNG, JPG, MP3, MP4, etc.).
- Experiment with different Gemini models to find the best fit for your needs.
- Use the text-to-speech feature for a more interactive experience, especially for longer responses.

## Troubleshooting

- If you encounter any issues, check the `logs` directory for detailed error logs.
- Ensure your API key is correctly set in the `.env` file.
- For file upload problems, verify that the file type is supported and the file is not corrupted.

## Contributing

Contributions to Gemini Copilot are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit your changes (`git commit -am 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Create a new Pull Request


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Google Gemini API](https://ai.google.dev/)
- [tkinter](https://docs.python.org/3/library/tkinter.html) for the GUI framework
- [ttkbootstrap](https://ttkbootstrap.readthedocs.io/) for enhanced UI elements
- [edge-tts](https://github.com/rany2/edge-tts) for text-to-speech functionality

## Contact

For support or queries, please open an issue on GitHub or raise issues....s.s.

---

Enjoy your journey with Gemini Copilot, your AI-powered conversation partner!
