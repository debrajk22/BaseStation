import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import math
import socket
import threading
from PIL import Image, ImageTk
from base_station_UI import *

class BaseStationLogic:
    def __init__(self, ui):
        self.ui = ui
        self.robots = ui.robots
        self.opponents = ui.opponents
        self.global_world = ui.global_world
        self.connection_status = False

        # RefBox connection
        self.refbox_socket = None
        self.refbox_connected = False
        self.refbox_messages = []  # store all messages from RefBox here
        self.refbox_thread = None
        self.refbox_running = False

    def connect_to_robots(self):
        self.connection_status = True
        for robot in self.robots:
            if robot.robot_ip is not None:
                robot.lock.acquire()
                robot.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                robot.connected = True
                robot.recieve_thread = threading.Thread(target=robot.receive_from_robot, daemon=True).start()

                if hasattr(robot, "status_label"):
                    robot.status_label.config(text="Connected", fg="green")
                robot.lock.release()
                print("Connected to robot", robot.name)

    def disconnect_from_robots(self):
        self.connection_status = False
        for robot in self.robots:
            if robot.socket:
                robot.socket.close()
                robot.socket = None
                if robot.receive_thread and robot.receive_thread.is_alive():
                    robot.receive_thread.join()
            robot.connected = False
            if hasattr(robot, "status_label"):
                robot.status_label.config(text="Disconnected", fg="red")
        print("Disconnected from robots")

    def connect_to_refbox(self, ip="127.0.0.1", port=28097):
        """Connect to the RefBox in a separate thread so UI doesn't freeze."""
        if self.refbox_connected:
            print("Already connected to RefBox.")
            return

        self.refbox_running = True
        self.refbox_thread = threading.Thread(
            target=self._refbox_listen_loop, args=(ip, port), daemon=True
        )
        self.refbox_thread.start()

    def _refbox_listen_loop(self, ip, port):
        """Threaded function to connect to the RefBox and read messages."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                self.refbox_socket = s
                self.refbox_connected = True
                print(f"Connected to RefBox at {ip}:{port}")
                self.ui.update_refbox_status(connected=True)

                while self.refbox_running:
                    data = s.recv(1024)
                    if not data:
                        break
                    message = data.decode("utf-8").strip()
                    if message:
                        self.refbox_messages.append(message)
                        # Also log to the UI
                        self.ui.log_refbox_message(message)
                        self.parse_message(message)

        except (ConnectionError, OSError) as e:
            print(f"RefBox connection error: {e}")
        finally:
            self.refbox_connected = False
            self.ui.update_refbox_status(connected=False)
            print("RefBox connection closed.")

    def stop_refbox(self):
        """Stop the RefBox reading loop."""
        self.refbox_running = False
        if self.refbox_socket:
            try:
                self.refbox_socket.close()
            except OSError:
                pass
        print("Stopped RefBox communication.")

    def update_world_state(self):
        # Update global world map from robots
        self.global_world.update_from_robots(self.robots)
        # Redraw field
        self.ui.redraw_field()
        # Re-check battery or other updates as needed

        # Keep scheduling next update
        self.ui.root.after(100, self.update_world_state)

    def parse_message(self, message):
        print(message)

def main():
    root = tk.Tk()
    app = BaseStationUI(root)
    # Create logic after UI so it can reference app
    logic = BaseStationLogic(app)
    app.logic = logic

    # Example: logic.connect_to_robots() or logic.disconnect_from_robots()
    logic.connect_to_robots()
    logic.update_world_state()
    root.mainloop()


if __name__ == "__main__":
    main()
