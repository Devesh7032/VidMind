import os
import tempfile
import cv2
import numpy as np
import yt_dlp
from typing import List, Dict, Any, Optional, Tuple


class VideoFrameExtractorService:
    """
    Real Video Keyframe Extraction Engine using yt-dlp & OpenCV.
    Downloads low-resolution video stream and extracts timestamped keyframes.
    Performs perceptual duplicate frame filtering before sending to AI vision.
    """

    def download_low_res_stream(self, source_url: str, output_dir: str) -> Optional[str]:
        """
        Downloads a low-resolution video stream (e.g. 360p) for fast keyframe extraction.
        Returns the absolute local path to the downloaded video file.
        """
        os.makedirs(output_dir, exist_ok=True)
        out_template = os.path.join(output_dir, "stream_video.%(ext)s")

        ydl_opts = {
            "format": "bv*[height<=360]/bv*/worstvideo/worst",
            "outtmpl": out_template,
            "overwrites": True,
            "quiet": True,
            "no_warnings": True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(source_url, download=True)
                ext = info.get("ext", "mp4")
                downloaded_file = os.path.join(output_dir, f"stream_video.{ext}")
                if os.path.exists(downloaded_file):
                    return downloaded_file
                # Fallback check for any generated stream file
                for fname in os.listdir(output_dir):
                    if fname.startswith("stream_video"):
                        return os.path.join(output_dir, fname)
            return None
        except Exception as e:
            print(f"[VideoFrameExtractor] Failed to download video stream for '{source_url}': {e}")
            return None

    def calculate_image_diff(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Calculates normalized mean absolute pixel difference between two frames."""
        try:
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            return float(np.mean(diff))
        except Exception:
            return 100.0

    def extract_keyframes_from_file(
        self,
        video_filepath: str,
        candidate_timestamps: List[float],
        max_frames: int = 10,
        min_diff_threshold: float = 12.0
    ) -> List[Dict[str, Any]]:
        """
        Samples real video frames at candidate timestamps, applies perceptual duplicate filtering,
        and returns list of extracted frame records with JPEG bytes and dimensions.
        """
        if not os.path.exists(video_filepath):
            return []

        cap = cv2.VideoCapture(video_filepath)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_frames / fps if fps > 0 else 0

        extracted_records: List[Dict[str, Any]] = []
        last_frame_img: Optional[np.ndarray] = None
        duplicates_removed = 0

        for t in candidate_timestamps:
            if len(extracted_records) >= max_frames:
                break

            target_t = max(0.0, min(float(t), duration_seconds - 0.5))
            frame_index = int(target_t * fps) if fps > 0 else 0

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = cap.read()

            if not ret or frame is None:
                continue

            # Perceptual duplicate frame filtering
            if last_frame_img is not None:
                diff = self.calculate_image_diff(last_frame_img, frame)
                if diff < min_diff_threshold:
                    duplicates_removed += 1
                    continue

            # Encode frame to JPEG bytes
            success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if not success:
                continue

            h, w = frame.shape[:2]
            extracted_records.append({
                "timestamp_seconds": round(target_t, 1),
                "image_bytes": buffer.tobytes(),
                "width": w,
                "height": h
            })
            last_frame_img = frame

        cap.release()
        return extracted_records


# Global singleton instance for video frame extractor service
video_frame_extractor = VideoFrameExtractorService()
