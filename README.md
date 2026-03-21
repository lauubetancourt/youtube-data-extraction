# YouTube Data Extraction

This project extracts and analyzes YouTube video and comment data with the YouTube Data API.

## Features

- Search and filter videos by topic, date range, views, and comments.
- Export batch snapshots in JSONL and Parquet.
- Clean noisy comments while preserving emotional signals for polarization analysis.
- Replay historical comments as a simulated stream with Streamz.

## Project Structure

- `notebooks/`: End-to-end notebooks.
- `src/youtube_pipeline/`: Reusable modules for storage, cleaning, and playback.
- `data/`: Batch and processed datasets.
- `docs/stream_processing_blueprint.md`: Integration guide for the 3-phase pipeline.

## Setup

```bash
pip install -r requirements.txt
```
