#!/usr/bin/env python3
"""
YOLOv8 Sabit Kanat İHA Tespit Modülü
"""
import cv2
from ultralytics import YOLO

class FixedWingDetector:
    """
    YOLOv8 modeli kullanarak sabit kanatlı İHA tespiti yapar.
    """
    def __init__(self, model_path: str, conf_thresh: float = 0.25):
        """
        Args:
            model_path: Eğitilmiş .pt model dosyasının yolu.
            conf_thresh: Tespit için minimum güven skoru.
        """
        self.model = YOLO(model_path)
        self.conf_thresh = conf_thresh

    def detect(self, frame):
        """
        Bir görüntü karesi üzerinde tespit yapar.
        Args:
            frame: NumPy dizisi (BGR formatında).
        Returns:
            results: Modelin döndürdüğü sonuç nesneleri listesi.
        """
        # YOLOv8 otomatik olarak BGR → RGB dönüşümünü yapar
        results = self.model(frame, imgsz=640, conf=self.conf_thresh)
        return results

    def annotate(self, frame, results):
        """
        Tespit sonuçlarını görüntü karesine çizer.
        Args:
            frame: Orijinal BGR görüntü.
            results: detect() tarafından dönen sonuçlar.
        Returns:
            annotated: Üzerine kutu ve etiket çizilmiş görüntü.
        """
        annotated = results[0].plot()  # İlk sonuç zincirine göre çizim
        return annotated

if __name__ == '__main__':
    # Örnek kullanım:
    cap = cv2.VideoCapture(0)
    detector = FixedWingDetector('fixed_wing_model.pt', conf_thresh=0.3)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = detector.detect(frame)
        vis = detector.annotate(frame, results)
        cv2.imshow('Fixed-Wing Detection', vis)
        if cv2.waitKey(1) == 27:  # ESC tuşu
            break
    cap.release()
    cv2.destroyAllWindows()

