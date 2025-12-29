"""
Face Recognition Model
Uses InsightFace (ArcFace) for face embedding and verification
"""

import numpy as np
from typing import Optional, Tuple, List
import cv2
import base64
from io import BytesIO
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class FaceRecognitionModel:
    """
    Face recognition using InsightFace/ArcFace
    
    Features:
    - Extract 512D face embedding
    - Compare embeddings (cosine similarity)
    - Liveness detection (blink detection)
    """
    
    def __init__(self):
        """Initialize InsightFace model"""
        try:
            from insightface.app import FaceAnalysis
            
            # Use CPU provider for cost efficiency
            # Change to CUDAExecutionProvider for GPU
            self.app = FaceAnalysis(
                name='buffalo_l',
                providers=['CPUExecutionProvider']
            )
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("InsightFace model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load InsightFace: {e}")
            self.app = None
    
    def decode_base64_image(self, image_base64: str) -> np.ndarray:
        """Convert base64 string to OpenCV image"""
        # Remove data URL prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB then BGR (OpenCV format)
        image_rgb = np.array(image.convert('RGB'))
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        
        return image_bgr
    
    def extract_embedding(self, image_base64: str) -> Tuple[Optional[List[float]], bool, str]:
        """
        Extract face embedding from image
        
        Args:
            image_base64: Base64 encoded image
            
        Returns:
            Tuple of (embedding, face_detected, error_message)
        """
        if self.app is None:
            return None, False, "Model not loaded"
        
        try:
            # Decode image
            img = self.decode_base64_image(image_base64)
            
            # Detect faces
            faces = self.app.get(img)
            
            if len(faces) == 0:
                return None, False, "No face detected"
            
            if len(faces) > 1:
                return None, False, "Multiple faces detected - please use a photo with only one person"
            
            # Get embedding (512D vector)
            embedding = faces[0].embedding.tolist()
            
            return embedding, True, ""
            
        except Exception as e:
            logger.error(f"Face extraction error: {e}")
            return None, False, str(e)
    
    def verify_faces(
        self,
        embedding1: List[float],
        embedding2: List[float],
        threshold: float = 0.85
    ) -> Tuple[bool, float]:
        """
        Verify if two face embeddings belong to the same person
        
        Args:
            embedding1: First face embedding (512D)
            embedding2: Second face embedding (512D)
            threshold: Similarity threshold (default 0.85 = 85%)
            
        Returns:
            Tuple of (is_verified, similarity_score)
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1).reshape(1, -1)
        vec2 = np.array(embedding2).reshape(1, -1)
        
        # Compute cosine similarity
        # ArcFace embeddings are already normalized
        similarity = np.dot(vec1, vec2.T)[0][0]
        
        # Convert to 0-1 range (cosine similarity is -1 to 1)
        normalized_score = (similarity + 1) / 2
        
        is_verified = normalized_score >= threshold
        
        return is_verified, float(normalized_score)
    
    def detect_liveness(self, frames_base64: List[str], required_blinks: int = 2) -> Tuple[bool, int, str]:
        """
        Detect liveness from video frames using blink detection
        
        Args:
            frames_base64: List of base64 encoded video frames
            required_blinks: Minimum number of blinks required
            
        Returns:
            Tuple of (is_live, blink_count, message)
        """
        try:
            import mediapipe as mp
            
            mp_face_mesh = mp.solutions.face_mesh
            face_mesh = mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5
            )
            
            blink_count = 0
            was_blinking = False
            
            for frame_base64 in frames_base64:
                frame = self.decode_base64_image(frame_base64)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                results = face_mesh.process(rgb)
                
                if not results.multi_face_landmarks:
                    continue
                
                landmarks = results.multi_face_landmarks[0].landmark
                
                # Calculate Eye Aspect Ratio (EAR)
                left_ear = self._calculate_ear(landmarks, [33, 160, 158, 133, 153, 144])
                right_ear = self._calculate_ear(landmarks, [362, 385, 387, 263, 373, 380])
                avg_ear = (left_ear + right_ear) / 2.0
                
                # Blink threshold
                is_blinking = avg_ear < 0.21
                
                # Count blink transitions (closed -> open)
                if was_blinking and not is_blinking:
                    blink_count += 1
                
                was_blinking = is_blinking
            
            face_mesh.close()
            
            is_live = blink_count >= required_blinks
            message = "Live person detected" if is_live else f"Please blink naturally ({blink_count}/{required_blinks})"
            
            return is_live, blink_count, message
            
        except Exception as e:
            logger.error(f"Liveness detection error: {e}")
            return False, 0, str(e)
    
    def _calculate_ear(self, landmarks, eye_indices: List[int]) -> float:
        """Calculate Eye Aspect Ratio from landmarks"""
        points = [(landmarks[i].x, landmarks[i].y) for i in eye_indices]
        
        # Vertical distances
        v1 = ((points[1][0] - points[5][0])**2 + (points[1][1] - points[5][1])**2)**0.5
        v2 = ((points[2][0] - points[4][0])**2 + (points[2][1] - points[4][1])**2)**0.5
        
        # Horizontal distance
        h = ((points[0][0] - points[3][0])**2 + (points[0][1] - points[3][1])**2)**0.5
        
        return (v1 + v2) / (2.0 * h) if h > 0 else 0
