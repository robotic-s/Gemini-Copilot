import tkinter as tk
from tkinter import ttk, filedialog
import google.generativeai as genai
import threading
import re
import sqlite3
from datetime import datetime
import queue
import time
import os
import logging
from ttkbootstrap import Style
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
from ttkbootstrap.tooltip import ToolTip
from PIL import Image
import asyncio
import edge_tts
from langdetect import detect
import tempfile
import sounddevice as sd
import soundfile as sf
import random
from PIL import Image, ImageTk
import platform

# Set up logging and runtime details
def setup_logging_and_runtime():
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    runtime_dir = os.path.join("logs", f"runtime_{current_time}")
    os.makedirs(runtime_dir, exist_ok=True)

    # Create runtime details file
    details_file = os.path.join(runtime_dir, "runtime_details.txt")
    with open(details_file, "w") as f:
        f.write(f"Runtime started at: {current_time}\n")
        f.write(f"Python version: {platform.python_version()}\n")
        f.write(f"Operating System: {platform.system()} {platform.release()}\n")

    # Set up logging
    log_file = os.path.join(runtime_dir, f"copilot_{current_time}.log")
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    return runtime_dir

# Set up Gemini API
genai.configure(api_key="AIzaSyB5tYQjDHteq_lfZQpjbJffBpBtEgeLM_4")

class CustomCopilot:
    def __init__(self, master):
        self.master = master
        master.title("gemini copilot")
        
        # Set up logging and runtime details
        self.runtime_dir = setup_logging_and_runtime()
        logging.info("Application started")
        
        # Get screen dimensions
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()
        
        # Set window size to 90% of screen width and 90% of screen height
        window_width = int(screen_width * 0.9)  
        window_height = int(screen_height * 0.9)
        master.geometry(f"{window_width}x{window_height}")
        
        # Use ttkbootstrap for a modern look
        self.style = Style(theme="darkly")
        
        # Initialize database  
        self.init_db()
        self.set_window_icon()

        # Fetch available models
        self.models = self.get_available_models()

        # Create main container
        self.main_container = ttk.Frame(master)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Create side panel for chat management
        self.side_panel = ttk.Frame(self.main_container, style="Secondary.TFrame", width=250)
        self.side_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Add "New Chat" button
        self.new_chat_btn = ttk.Button(self.side_panel, text="New Chat", command=self.start_new_chat, style="success.TButton")
        self.new_chat_btn.pack(pady=10, padx=5, fill=tk.X)

        # Add model selection dropdown
        self.model_var = tk.StringVar(value=list(self.models.keys())[0])
        self.model_dropdown = ttk.OptionMenu(self.side_panel, self.model_var, self.model_var.get(), *self.models.keys(), command=self.on_model_change)
        self.model_dropdown.pack(pady=10, padx=5, fill=tk.X)

        # Add chat list    
        self.chat_list = ttk.Treeview(self.side_panel, selectmode="browse", show="tree") 
        self.chat_list.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        self.chat_list.bind("<<TreeviewSelect>>", self.load_selected_chat)

        # Create main chat area
        self.chat_area = ttk.Frame(self.main_container, style="Primary.TFrame")
        self.chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Chat display with custom scrollbar
        self.chat_frame = ttk.Frame(self.chat_area, style="Primary.TFrame")
        self.chat_frame.pack(expand=True, fill=tk.BOTH, pady=(0, 10))

        self.chat_display = ScrolledText(self.chat_frame, 
                                         wrap=tk.WORD,
                                         font=('Segoe UI', 12),
                                         autohide=True)
        self.chat_display.pack(expand=True, fill=tk.BOTH)
        
        # Make chat display read-only
        self.chat_display.bind("<Key>", lambda e: "break")
        self.chat_display.bind("<Button-1>", lambda e: self.chat_display.focus_set())

        # Input area
        self.input_frame = ttk.Frame(self.chat_area, style="Secondary.TFrame")  
        self.input_frame.pack(fill=tk.X, pady=10)

        self.input_field = ttk.Entry(self.input_frame, font=('Segoe UI', 12), style='Custom.TEntry')
        self.input_field.pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=10, padx=(0, 10))
        self.input_field.bind("<Return>", self.send_message)
        self.input_field.insert(0, "Type your message here...")
        self.input_field.bind("<FocusIn>", self.on_entry_click)
        self.input_field.bind("<FocusOut>", self.on_focusout)

        self.send_button = ttk.Button(self.input_frame, text="Send", command=self.send_message, style='success.TButton')
        self.send_button.pack(side=tk.RIGHT)

        # Add file upload button
        self.file_button = ttk.Button(self.input_frame, text="📎", command=self.upload_file, style='info.TButton')
        self.file_button.pack(side=tk.RIGHT, padx=(0, 10))
        ToolTip(self.file_button, text="Upload file for analysis")

        # Store uploaded files
        self.uploaded_files = []
        
        # Configure text tags  
        self.configure_tags()

        # Queue for thread-safe communication
        self.queue = queue.Queue()
        self.master.after(100, self.process_queue)

        # Current chat ID
        self.current_chat_id = None

        # Load chat list
        self.load_chat_list()

        # Initialize TTS
        self.tts_queue = queue.Queue()
        self.tts_thread = threading.Thread(target=self.tts_worker)
        self.tts_thread.daemon = True
        self.tts_thread.start()

        # Flag to indicate if TTS should be used for the next response
        self.use_tts = False

        # Audio playback
        self.stop_playback = threading.Event()
        self.current_audio_thread = None
        self.audio_parts = []

        # Conversation history
        self.conversation_history = []

        # Automatically start a new chat on app launch
        self.start_new_chat()

    def get_available_models(self):
        available_models = genai.list_models()
        model_dict = {}
        for model in available_models:
            if 'gemini' in model.name:
                try:
                    model_instance = genai.GenerativeModel(model.name)
                    model_dict[model.name] = model_instance
                    logging.info(f"Model added: {model.name}")
                except Exception as e:
                    logging.warning(f"Failed to add model {model.name}: {str(e)}")
        return model_dict
    def set_window_icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "gemini_copilot_logo.png")
        if os.path.exists(icon_path):
            try:
                icon_image = Image.open(icon_path)
                
                # For Windows: create a temporary .ico file
                if platform.system() == "Windows":
                    with tempfile.NamedTemporaryFile(suffix='.ico', delete=False) as icon_file:
                        icon_image.save(icon_file.name, format='ICO')
                        self.master.iconbitmap(icon_file.name)
                    os.unlink(icon_file.name)  # Delete the temporary file
                    
                    # Set taskbar icon for Windows
                    import ctypes
                    myappid = 'com.yourdomain.geminichatbot.1.0' # arbitrary string
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                
                # For all platforms: set window icon
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.master.iconphoto(True, icon_photo)
                
                logging.info(f"Window icon set successfully from {icon_path}")
            except Exception as e:
                logging.error(f"Error setting window icon: {str(e)}")
        else:
            logging.warning(f"Icon file not found at {icon_path}")

    def on_model_change(self, *args):
        logging.info(f"Model changed to: {self.model_var.get()}")

    def init_db(self):
        self.conn = sqlite3.connect('conversation_history.db', check_same_thread=False) 
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS chats
                              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                               title TEXT,    
                               created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS messages
                              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                               chat_id INTEGER,
                               sender TEXT,
                               content TEXT,
                               timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                               generation_time REAL,     
                               FOREIGN KEY (chat_id) REFERENCES chats (id))''')
        self.conn.commit()
        logging.info("Database initialized")

    def configure_tags(self):
        self.chat_display.tag_configure('user', foreground='#007bff', font=('Segoe UI', 12, 'bold'))
        self.chat_display.tag_configure('copilot', foreground='#28a745', font=('Segoe UI', 12))
        self.chat_display.tag_configure('separator', foreground='#6c757d', font=('Segoe UI', 10))  
        self.chat_display.tag_configure('bold', foreground='#ffc107', font=('Segoe UI', 12, 'bold'))
        self.chat_display.tag_configure('italic', foreground='#17a2b8', font=('Segoe UI', 12, 'italic'))
        self.chat_display.tag_configure('highlight', background='#ffc107', foreground='#343a40')  
        self.chat_display.tag_configure('code', foreground='#dc3545', font=('Courier', 12)) 
        self.chat_display.tag_configure('time', foreground='#f8f9fa', font=('Segoe UI', 10, 'italic'))
        self.chat_display.tag_configure('error', foreground='#dc3545', font=('Segoe UI', 12, 'italic'))
        self.chat_display.tag_configure('info', foreground='#17a2b8', font=('Segoe UI', 10, 'italic'))

    def on_entry_click(self, event):
        if self.input_field.get() == "Type your message here...":
            self.input_field.delete(0, tk.END)
            self.input_field.config(foreground='white')

    def on_focusout(self, event):  
        if self.input_field.get() == "":
            self.input_field.insert(0, "Type your message here...")
            self.input_field.config(foreground='gray')

    def get_copilot_emoji(self):
        emojis = ["🤖", "🧠", "💡", "🔮", "🦾", "🚀", "🌟", "💬", "🎓", "🧪"]
        return random.choice(emojis)

    def start_new_chat(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO chats (title) VALUES (?)", ("New Chat",))  
            self.current_chat_id = cursor.lastrowid
        self.load_chat_list()
        self.clear_chat_display()
        self.conversation_history = []
        self.display_conversation_info()
        logging.info(f"New chat started with ID: {self.current_chat_id}")

    def load_chat_list(self):
        self.chat_list.delete(*self.chat_list.get_children())  
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, title FROM chats ORDER BY created_at DESC")
            for chat_id, title in cursor.fetchall(): 
                self.chat_list.insert('', 'end', iid=chat_id, text=title)
        logging.info("Chat list loaded")

    def load_selected_chat(self, event):
        selected_item = self.chat_list.selection()
        if selected_item:
            self.current_chat_id = int(selected_item[0]) 
            self.load_chat_history()
            logging.info(f"Loaded chat with ID: {self.current_chat_id}")

    def load_chat_history(self):
        self.clear_chat_display()
        self.conversation_history = []
        self.display_conversation_info()
        with self.conn:  
            cursor = self.conn.cursor()
            cursor.execute("SELECT sender, content, generation_time FROM messages WHERE chat_id = ? ORDER BY timestamp", (self.current_chat_id,))
            for sender, content, generation_time in cursor.fetchall():
                self.conversation_history.append({"role": sender, "parts": [content]})
                if sender == 'user':
                    self.append_to_chat("\n" + "-"*50 + "\n\n", 'separator')
                    self.append_to_chat(f"You: {content}\n\n", 'user')
                else:
                    copilot_emoji = self.get_copilot_emoji()
                    self.append_to_chat(f"{copilot_emoji} Copilot:\n\n", 'copilot')
                    self.process_and_append(content)
                    if generation_time:
                        self.append_to_chat(f"\n\nGeneration time: {generation_time:.2f} seconds\n", 'time')
        logging.info(f"Chat history loaded for chat ID: {self.current_chat_id}")

    def clear_chat_display(self):
        self.chat_display.delete('1.0', tk.END)

    def display_conversation_info(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT created_at FROM chats WHERE id = ?", (self.current_chat_id,))
            created_at = cursor.fetchone()[0]
        
        created_datetime = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        info_text = (f"Conversation ID: {self.current_chat_id}\n"
                     f"Created on: {created_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
                     f"Day: {created_datetime.strftime('%A')}\n"
                     f"Month: {created_datetime.strftime('%B')}\n")
        self.append_to_chat(info_text, 'info')
        self.append_to_chat("\n" + "-"*50 + "\n\n", 'separator')

    def send_message(self, event=None):
        user_message = self.input_field.get() 
        if user_message and user_message != "Type your message here...":
            self.stop_audio_playback()
            
            if user_message.strip().endswith("/speak"):
                self.use_tts = True
                user_message = user_message.rsplit("/speak", 1)[0].strip()
            else:
                self.use_tts = False

            self.append_to_chat("\n" + "-"*50 + "\n\n", 'separator')
            self.append_to_chat(f"You: {user_message}\n\n", 'user')
            self.save_message('user', user_message, 0)
            self.input_field.delete(0, tk.END) 
            
            copilot_emoji = self.get_copilot_emoji()
            self.append_to_chat(f"{copilot_emoji} Copilot:\n\n", 'copilot')

            self.conversation_history.append({"role": "user", "parts": [user_message]})

            threading.Thread(target=self.get_copilot_response, args=(user_message,)).start()
            logging.info(f"User message sent: {user_message}")

    def get_copilot_response(self, user_message):
        current_model = self.model_var.get()
        model = self.models[current_model]
        start_time = time.time()

        try:
            if self.uploaded_files:
                parts = [user_message] + self.uploaded_files
                response = model.generate_content(self.conversation_history + [{"role": "user", "parts": parts}], stream=True)
            else:
                response = model.generate_content(self.conversation_history + [{"role": "user", "parts": [user_message]}], stream=True)

            full_response = ""
            for chunk in response:
                if hasattr(chunk, 'text'):
                    chunk_text = chunk.text
                elif hasattr(chunk, 'parts'):
                    chunk_text = ''.join([part.text for part in chunk.parts if hasattr(part, 'text')])
                else:
                    continue

                if chunk_text:
                    full_response += chunk_text
                    self.queue.put(("append", chunk_text))

            generation_time = time.time() - start_time
            self.queue.put(("save", (full_response, generation_time)))

            self.conversation_history.append({"role": "model", "parts": [full_response]})

            # Display generation time
            self.queue.put(("append", f"\n\nGeneration time: {generation_time:.2f} seconds"))

            if self.use_tts:
                self.tts_queue.put(self.prepare_text_for_tts(full_response))

        except Exception as e:
            error_message = f"Error generating response: {str(e)}\n"
            self.queue.put(("append", error_message))
            logging.error(f"Error in get_copilot_response: {str(e)}")

        self.uploaded_files.clear()

        if self.is_first_message():
            self.update_chat_title(user_message[:50])

    def process_queue(self):
        try:
            while True:
                action, data = self.queue.get_nowait()
                if action == "append":
                    self.process_and_append(data)
                elif action == "save":  
                    self.save_message('copilot', data[0], data[1])
        except queue.Empty:
            pass
        self.master.after(100, self.process_queue)

    def process_and_append(self, text):
        lines = text.split('\n')
        in_code_block = False
        processed_text = ""
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                self.chat_display.insert(tk.END, line + '\n', 'code')
            elif in_code_block:
                self.chat_display.insert(tk.END, line + '\n', 'code')
            else:
                parts = re.split(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`)', line)
                for part in parts:
                    if part.startswith('***') and part.endswith('***'):
                        self.chat_display.insert(tk.END, part[3:-3], 'highlight')
                        processed_text += part[3:-3]
                    elif part.startswith('**') and part.endswith('**'):
                        self.chat_display.insert(tk.END, part[2:-2], 'bold')
                        processed_text += part[2:-2]
                    elif part.startswith('*') and part.endswith('*'):
                        self.chat_display.insert(tk.END, part[1:-1], 'italic')
                        processed_text += part[1:-1]
                    elif part.startswith('`') and part.endswith('`'):
                        self.chat_display.insert(tk.END, part[1:-1], 'code')
                        processed_text += part[1:-1]
                    else:
                        self.chat_display.insert(tk.END, part, 'copilot')
                        processed_text += part
                self.chat_display.insert(tk.END, '\n')
                processed_text += '\n'
        self.chat_display.see(tk.END)

    def append_to_chat(self, text, tag):
        self.chat_display.insert(tk.END, text, tag)
        self.chat_display.see(tk.END)

    def save_message(self, sender, content, generation_time):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO messages (chat_id, sender, content, generation_time) VALUES (?, ?, ?, ?)",
                           (self.current_chat_id, sender, content, generation_time))
        logging.info(f"Message saved: sender={sender}, chat_id={self.current_chat_id}")

    def tts_worker(self):
        while True:
            text_parts = self.tts_queue.get()
            if text_parts is None:
                break
            try:
                for part in text_parts:
                    if self.stop_playback.is_set():
                        break
                    asyncio.run(self.tts_task(part))
            except Exception as e:
                logging.error(f"Error in TTS worker: {str(e)}")
            finally:
                self.clear_audio_files()

    async def tts_task(self, text):
        voice = "en-US-EmmaMultilingualNeural"
        try:
            communicate = edge_tts.Communicate(text, voice)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                await communicate.save(temp_filename)
            
            self.audio_parts.append(temp_filename)
            self.current_audio_thread = threading.Thread(target=self.play_audio, args=(temp_filename,))
            self.current_audio_thread.start()
            self.current_audio_thread.join()
        except Exception as e:
            logging.error(f"Error in TTS task: {str(e)}")
            self.queue.put(("append", f"Error in text-to-speech: {str(e)}\n"))

    def play_audio(self, filename):
        try:
            data, samplerate = sf.read(filename)
            sd.play(data, samplerate)
            while sd.get_stream().active and not self.stop_playback.is_set():
                sd.wait()
            sd.stop()
        except Exception as e:
            logging.error(f"Error playing audio: {str(e)}")

    def regenerate_response(self, event=None):
        if self.current_chat_id is not None and len(self.conversation_history) >= 2:
            self.conversation_history.pop()
            
            last_separator = self.chat_display.search("-"*50, "end-1c", backwards=True)
            if last_separator:
                self.chat_display.delete(last_separator, tk.END)

            with self.conn:
                cursor = self.conn.cursor() 
                cursor.execute("DELETE FROM messages WHERE chat_id = ? AND sender = 'copilot' ORDER BY timestamp DESC LIMIT 1", (self.current_chat_id,))

            copilot_emoji = self.get_copilot_emoji()
            self.append_to_chat(f"{copilot_emoji} Copilot:\n\n", 'copilot')
            last_user_message = self.conversation_history[-1]['parts'][0]
            threading.Thread(target=self.get_copilot_response, args=(last_user_message,)).start()
            logging.info("Response regenerated")

    def create_context_menu(self, event):
        context_menu = tk.Menu(self.master, tearoff=0)
        context_menu.add_command(label="Regenerate response", command=self.regenerate_response)
        context_menu.tk_popup(event.x_root, event.y_root)

    def bind_context_menu(self):
        self.chat_display.bind("<Button-3>", self.create_context_menu)

    def upload_file(self):
        try:
            file_paths = filedialog.askopenfilenames(
                filetypes=[
                    ("Supported files", "*.png *.jpg *.jpeg *.gif *.bmp *.mp3 *.wav *.mp4 *.avi *.mov"),
                    ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                    ("Audio files", "*.mp3 *.wav"),
                    ("Video files", "*.mp4 *.avi *.mov"),
                    ("All files", "*.*")
                ]
            )
            if file_paths:
                self.append_to_chat("Starting upload...\n", 'copilot')
                threading.Thread(target=self.process_files, args=(file_paths,)).start()
        except Exception as e:
            error_message = f"Error in file upload: {str(e)}\n"
            self.queue.put(("append", error_message))
            logging.error(f"Error in upload_file: {str(e)}")

    def process_files(self, file_paths):
        for file_path in file_paths:
            try:
                mime_type = self.get_mime_type(file_path)
                if mime_type:
                    file = genai.upload_file(file_path, mime_type=mime_type)
                    self.uploaded_files.append(file)
                    self.queue.put(("append", f"File uploaded: {os.path.basename(file_path)}\n"))
                    self.wait_for_files_active([file])
                    logging.info(f"File uploaded: {file_path}")
                else:
                    raise ValueError("Unsupported file type")
            except Exception as e:
                error_message = f"Error uploading file: The model might not support attachments or something went wrong. Please check the logs for details.\n"
                self.queue.put(("append", error_message))
                logging.error(f"Error uploading file {file_path}: {str(e)}")
        self.queue.put(("append", "All files processed. You can now send your message.\n"))

    def wait_for_files_active(self, files):
        for file in files:
            while file.state.name == "PROCESSING":
                time.sleep(1)
            if file.state.name != "ACTIVE":
                self.queue.put(("append", f"File {file.name} failed to process\n"))
                logging.warning(f"File {file.name} failed to process")
                return False
        self.queue.put(("append", "File(s) ready for analysis.\n"))
        return True

    def get_mime_type(self, file_path):
        extension = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime'
        }
        return mime_types.get(extension, None)

    def is_first_message(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages WHERE chat_id = ?", (self.current_chat_id,))
            count = cursor.fetchone()[0]
        return count == 1

    def update_chat_title(self, title):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE chats SET title = ? WHERE id = ?", (title, self.current_chat_id))
        self.load_chat_list()

    def prepare_text_for_tts(self, text):
        text = re.sub(r'\*+', '', text)
        parts = re.split(r'(?<=[.!?])\s+', text)
        return [part.strip() for part in parts if part.strip()]

    def stop_audio_playback(self):
        self.stop_playback.set()
        if self.current_audio_thread and self.current_audio_thread.is_alive():
            self.current_audio_thread.join()
        self.stop_playback.clear()
        self.clear_audio_files()

    def clear_audio_files(self):
        for file in self.audio_parts:
            try:
                if os.path.exists(file):
                    os.unlink(file)
            except Exception as e:
                logging.error(f"Error deleting file {file}: {str(e)}")
        self.audio_parts.clear()

# Main application setup
if __name__ == "__main__":
    root = tk.Tk()
    app = CustomCopilot(root)
    app.bind_context_menu()
    root.mainloop()