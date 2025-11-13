import cv2
import numpy as np


class BlurDetector:
    """Detects blur in images using Laplacian variance method."""
    
    @staticmethod
    def calculate_blur_score(frame: np.ndarray) -> float:
        """
        Calculate blur score for a frame using Laplacian variance.
        Lower score = more blurry, Higher score = sharper.
        Returns the variance of the Laplacian.
        """
        if frame is None:
            return float('inf')
        
        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        # Calculate Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        return variance
    
    @staticmethod
    def is_blurry(frame: np.ndarray, threshold: float = 100.0) -> bool:
        """
        Determine if a frame is blurry based on threshold.
        
        Args:
            frame: Input image
            threshold: Blur threshold (lower = more strict)
        
        Returns:
            True if frame is blurry, False otherwise
        """
        score = BlurDetector.calculate_blur_score(frame)
        return score < threshold

