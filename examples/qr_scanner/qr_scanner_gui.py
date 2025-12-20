import argparse
import sys
import tkinter as tk
from tkinter import messagebox

import cv2
from PIL import Image, ImageTk


class QRScannerApp:
    def __init__(
        self,
        master: tk.Tk,
        camera_index: int = 0,
        history_size: int = 20,
        display_scale: float = 0.5,
        decode_scale: float = 1.0,
    ):
        self.master = master
        self.master.title("QR Code Scanner")
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.running = True
        self.camera_index = camera_index
        self.display_scale = display_scale
        self.decode_scale = decode_scale

        if not self.open_camera():
            sys.exit(1)

        self.detector = cv2.QRCodeDetector()
        self.frame_label = tk.Label(master)
        self.frame_label.pack()

        self.status_var = tk.StringVar(value="Waiting for QR code...")
        self.status_label = tk.Label(master, textvariable=self.status_var, fg="blue")
        self.status_label.pack(fill="x", padx=8, pady=4)

        self.history_size = history_size
        self.decoded_history = []
        self.decoded_box = tk.Text(
            master,
            height=8,
            wrap="word",
            state="disabled",
            bg="#f8fff8",
            fg="green",
        )
        self.decoded_box.pack(fill="both", expand=True, padx=8, pady=4)

        self.resume_button = tk.Button(master, text="Resume Scan", command=self.resume_scan)
        self.resume_button.pack(fill="x", padx=8, pady=(0, 8))

        self.last_result = None
        self.update_frame()

    def update_frame(self):
        if not self.running:
            return

        ok, frame = self.video.read()
        if not ok:
            self.status_var.set("Camera read failed")
            self.master.after(200, self.update_frame)
            return

        detect_frame = frame
        if self.decode_scale != 1.0:
            detect_frame = cv2.resize(
                frame,
                None,
                fx=self.decode_scale,
                fy=self.decode_scale,
                interpolation=cv2.INTER_AREA,
            )

        decoded_texts, points = self.decode_qr(detect_frame)
        if decoded_texts:
            newest = decoded_texts[-1]
            if newest != self.last_result:
                self.last_result = newest
                self.append_history(newest)
                self.status_var.set("QR detected - camera stopped")
                self.running = False
                if self.video.isOpened():
                    self.video.release()
                messagebox.showinfo("QR detected", newest)
                return
        else:
            self.status_var.set("Waiting for QR code...")

        display_frame = frame
        if self.display_scale != 1.0:
            display_frame = cv2.resize(
                frame, None, fx=self.display_scale, fy=self.display_scale, interpolation=cv2.INTER_AREA
            )

        if points is not None:
            scale_factor = self.display_scale / self.decode_scale
            for bbox in points:
                pts = (bbox * scale_factor).astype(int).reshape(-1, 2)
                for i in range(len(pts)):
                    cv2.line(
                        display_frame,
                        tuple(pts[i]),
                        tuple(pts[(i + 1) % len(pts)]),
                        (0, 255, 0),
                        2,
                    )

        frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.frame_label.imgtk = imgtk
        self.frame_label.configure(image=imgtk)
        if self.running:
            self.master.after(10, self.update_frame)

    def decode_qr(self, frame):
        texts = []
        points = None
        retval, decoded_info, pts, _ = self.detector.detectAndDecodeMulti(frame)
        if retval:
            texts = [text for text in decoded_info if text]
            points = pts
        return texts, points

    def open_camera(self):
        # CAP_DSHOW improves startup on Windows; fallback without flag for other platforms.
        try:
            self.video = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        except Exception:
            self.video = cv2.VideoCapture(self.camera_index)
        if not self.video.isOpened():
            messagebox.showerror("Camera Error", f"Cannot open camera index {self.camera_index}")
            return False
        return True

    def resume_scan(self):
        if self.running:
            return
        if not self.open_camera():
            return
        self.last_result = None
        self.running = True
        self.status_var.set("Waiting for QR code...")
        self.update_frame()

    def append_history(self, text: str):
        if text:
            self.decoded_history.append(text)
            if len(self.decoded_history) > self.history_size:
                self.decoded_history = self.decoded_history[-self.history_size :]
            self.decoded_box.configure(state="normal")
            self.decoded_box.delete("1.0", tk.END)
            self.decoded_box.insert(tk.END, "\n".join(self.decoded_history))
            self.decoded_box.configure(state="disabled")

    def on_close(self):
        if self.video.isOpened():
            self.video.release()
        self.master.destroy()


def main():
    parser = argparse.ArgumentParser(description="QR code scanner GUI")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    args = parser.parse_args()

    root = tk.Tk()
    app = QRScannerApp(root, camera_index=args.camera, decode_scale=4.0)
    root.mainloop()


if __name__ == "__main__":
    main()
