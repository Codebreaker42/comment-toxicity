import gradio as gr
import pandas as pd
import numpy as np
from googleapiclient.discovery import build
from tensorflow.keras.models import load_model
import pickle
import os

# Load the dataset for toxicity labels
df1 = pd.read_csv(os.path.join('dataset', 'train.csv'))

# Load the pre-trained toxicity model
model = load_model("comment_checkpoint/toxicity.keras")

# Load tokenizer for text processing
vectorize = pickle.load(open('vectorizer.pkl', 'rb'))

# YouTube API Key
API_KEY = "AIzaSyDZ63MABQlLpjhxcPCnYmzo_of7Og3erhU"
youtube = build("youtube", "v3", developerKey=API_KEY)

MAX_LEN = 1800  # Maximum input length used in training


def predict_toxicity(comment):
    """Predict toxicity scores for a single comment and format the output."""
    processed_text = vectorize(comment)
    prediction = model.predict(np.expand_dims(processed_text, 0))

    result_html = "<div style='font-family: Arial, sans-serif; font-size: 16px;'>"

    for idx, col in enumerate(df1.columns[2:]):
        value = prediction[0][idx] > 0.5
        color = "red" if value else "green"
        result_html += f"<p style='color: {color};'><b>{col}:</b> {value}</p>"

    result_html += "</div>"
    return result_html

def fetch_youtube_comments(video_url):
    """Extract all comments from a YouTube video."""
    video_id = video_url.split("v=")[-1].split("&")[0]
    comments = []
    next_page_token = None

    while True:
        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,  # Maximum per request
            pageToken=next_page_token
        ).execute()

        for item in response.get("items", []):
            comment_text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(comment_text)

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return comments


def process_youtube_comments(video_url):
    """Fetch comments, predict toxicity, and return a DataFrame."""
    comments = fetch_youtube_comments(video_url)

    results = []
    for comment in comments:
        scores = predict_toxicity(comment)
        results.append({"Comment": comment, "Toxicity Analysis": scores})

    df = pd.DataFrame(results)
    return df.to_html(classes="table table-striped", escape=False)


def analyze_single_comment(comment):
    """Analyze a single custom comment for toxicity."""
    return predict_toxicity(comment)


# Create Gradio Interface
with gr.Blocks(title="Comment Toxicity Detector") as demo:
    gr.Markdown("# 🛑 YouTube Comment Toxicity Detector")

    with gr.Tabs():
        with gr.Tab("Custom Comment Analysis"):
            gr.Markdown("### Enter a custom comment to analyze its toxicity.")
            comment_input = gr.Textbox(label="Enter Comment", lines=2)
            comment_output = gr.HTML(label="Toxicity Result")  # Updated to HTML for color formatting
            analyze_comment_btn = gr.Button("Analyze Comment")
            analyze_comment_btn.click(analyze_single_comment, inputs=comment_input, outputs=comment_output)

        with gr.Tab("YouTube Video Analysis"):
            gr.Markdown("### Paste a YouTube Video URL to analyze its comments for toxicity.")
            video_input = gr.Textbox(label="YouTube Video URL")
            video_output = gr.HTML(label="Toxicity Analysis Table")
            analyze_video_btn = gr.Button("Analyze Video")
            analyze_video_btn.click(process_youtube_comments, inputs=video_input, outputs=video_output)

demo.launch(share=True)
