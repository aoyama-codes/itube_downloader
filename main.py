import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from pytubefix import YouTube
import threading
import re
import os
import sys
from PIL import Image
import requests
from io import BytesIO
from customtkinter import CTkImage  # Import CTkImage

ctk.set_appearance_mode("system")

def resource_path(relative_path):
    # Get absolute path to resource, works for pyinstaller
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Initialize main window
root = ctk.CTk()
root.title("ITube Downloader")
root.geometry("1280x720")
root.iconbitmap(resource_path("logo.ico"))

# Centering Frame
center_frame = ctk.CTkFrame(master=root, fg_color="transparent")
center_frame.pack(expand=True)

# YouTube URL Entry
ctk.CTkLabel(
    master=center_frame,
    text="Enter YouTube URL:",
    font=("Arial", 20),
    pady=5,
    padx=5
).pack(pady=10)

url_entry = ctk.CTkEntry(
    master=center_frame,
    width=800,
    corner_radius=5,
    placeholder_text="Paste Link Here",
    border_color="#07F036",
    border_width=1
)
url_entry.pack(pady=5)

# Video Title Label
video_title_label = ctk.CTkLabel(
    master=center_frame,
    text="",
    font=("Arial", 18),
    text_color="#000000"
)
video_title_label.pack(pady=5)

# Thumbnail Label
thumbnail_label = ctk.CTkLabel(
    master=center_frame,
    text=""
)
thumbnail_label.pack(pady=10)

# Spinner Label
spinner_label = ctk.CTkLabel(
    master=center_frame,
    text="Loading...",
    font=("Arial", 16),
    text_color="#000000"
)
spinner_label.pack_forget()  # Initially hidden

# Display video title and thumbnail when link is pasted
def display_video_info(event=None):
    url = url_entry.get()
    normalized_url = normalize_youtube_url(url)

    if not normalized_url:
        video_title_label.configure(text="")  # Clear previous title if invalid
        thumbnail_label.configure(image="")   # Clear previous thumbnail if invalid
        return

    # Show spinner while loading video info
    spinner_label.pack(pady=5)
    threading.Thread(target=load_video_info, args=(normalized_url,)).start()

def load_video_info(normalized_url):
    try:
        yt = YouTube(normalized_url)
        root.after(0, lambda: video_title_label.configure(text=yt.title))  # Display the video title

        # Fetch and display the thumbnail
        thumbnail_url = yt.thumbnail_url
        response = requests.get(thumbnail_url)
        if response.status_code == 200:
            thumbnail_image = Image.open(BytesIO(response.content))
            # Resize while maintaining aspect ratio
            thumbnail_image.thumbnail((600, 500))  # Max size
            thumbnail_ctk_image = CTkImage(thumbnail_image)  # Convert to CTkImage for better scaling support
            root.after(0, lambda: update_thumbnail(thumbnail_ctk_image))  # Update the thumbnail in the main thread
        else:
            messagebox.showerror("Error", "Failed to retrieve thumbnail image.")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        root.after(0, spinner_label.pack_forget)  # Hide spinner once loading is done

def update_thumbnail(thumbnail_ctk_image):
    thumbnail_label.configure(image=thumbnail_ctk_image)
    thumbnail_label.image = thumbnail_ctk_image  # Keep a reference to avoid garbage collection

# Resolution Dropdown
ctk.CTkLabel(
    master=center_frame,
    text="Select Resolution:",
    font=("Arial", 16),
    pady=5,
    padx=5
).pack(pady=10)

resolution_var = ctk.StringVar(value="Highest")
resolution_dropdown = ctk.CTkComboBox(
    master=center_frame,
    values=["Highest", "720p", "480p", "360p", "Audio Only"],
    dropdown_fg_color="#FFFFFF",
    dropdown_hover_color="#19fc47",
    border_width=1,
    border_color="#07F036",
    button_color="#07F036",
    button_hover_color="#19fc47",
    variable=resolution_var
)
resolution_dropdown.pack(pady=2)

# Progress Bar
progress = ctk.CTkProgressBar(
    master=center_frame,
    width=800,
    mode="determinate",
    height=30,
    fg_color="#FFFFFF",
    progress_color="#07F036",
    determinate_speed=2
)
progress.set(0)
progress.pack(pady=20)

# Percentage Label
percentage_label = ctk.CTkLabel(
    master=center_frame,
    text="",
    text_color="#000000"
)
percentage_label.pack()

# Folder Selection
def choose_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_path.set(folder)

folder_path = ctk.StringVar()
ctk.CTkButton(
    master=center_frame,
    text="Choose Download Folder",
    width=200,
    height=40,
    command=choose_folder,
    fg_color="#07F036",
    text_color="#FFFFFF",
    font=("Arial", 18),
    hover_color="#19fc47"
).pack(pady=10)

ctk.CTkLabel(
    master=center_frame,
    textvariable=folder_path,
).pack()

# Function to normalize YouTube URLs
def normalize_youtube_url(url):
    short_url_pattern = r"https?://youtu\.be/([a-zA-Z0-9_-]+)"
    full_url_pattern = r"https?://(www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)"
    
    # Check if URL is a shortened URL
    short_match = re.match(short_url_pattern, url)
    if short_match:
        video_id = short_match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"
    
    # Check if URL is already in full format
    full_match = re.match(full_url_pattern, url)
    if full_match:
        return url
    
    # Return None if URL is invalid
    return None

# Download function with progress updates
def download_video():
    url = url_entry.get()
    normalized_url = normalize_youtube_url(url)
    download_location = folder_path.get() if folder_path.get() else None  # Default to current directory if not set
    
    if not normalized_url:
        messagebox.showerror("Error", "Please enter a valid YouTube URL")
        return
    
    try:
        yt = YouTube(normalized_url, on_progress_callback=on_progress)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        return
    
    # Select the appropriate stream based on resolution
    stream = None
    if resolution_var.get() == "Audio Only":
        stream = yt.streams.filter(only_audio=True).first()
    elif resolution_var.get() == "Highest":
        stream = yt.streams.get_highest_resolution()
    else:
        stream = yt.streams.filter(res=resolution_var.get()).first()
    
    if stream:
        download_thread = threading.Thread(target=stream.download, kwargs={"output_path": download_location})
        download_thread.start()
    else:
        messagebox.showerror("Error", "Resolution not available")

# Update progress bar during download
def on_progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    progress.set(bytes_downloaded / total_size)
    percentage_label.configure(text=f"{int((bytes_downloaded / total_size) * 100)}%")  # Update percentage label
    root.after(0)

# Call display_video_info when a valid link is detected
url_entry.bind("<FocusOut>", display_video_info)

# Download Button
download_button = ctk.CTkButton(
    master=center_frame,
    text="Download",
    command=download_video,
    width=200,
    height=40,
    fg_color="#07F036",
    text_color="#FFFFFF",
    font=("Arial", 18),
    hover_color="#19fc47"
)
download_button.pack(pady=20)

root.mainloop()
