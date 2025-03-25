import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import math
import socket
import threading
from PIL import Image, ImageTk


class Robot:
    def __init__(self, robot_id, name="Robot", color="blue", ip_address=None, port=None):
        self.robot_ip = ip_address
        self.robot_port = port
        self.socket = None
        self.robot_id = robot_id
        self.recieve_thread = None
        self.name = f"{name} {robot_id}"
        self.connected = False
        self.color = color
        self.ball_position = (6, 4.5)
        self.obstacles = []
        self.lock = threading.Lock()
        # Field positions in meters (assuming 12m x 9m field)
        self.position = (0, 0)
        # Orientation in degrees, 0 = facing "east" in our coordinate assumption
        self.orientation = 0
        self.local_world_map = {}
        self.parameters = {
            "max_speed": 2.0,
            "rotation_speed": 1.0,
            "kick_power": 0.8,
            "acceleration": 1.5,
            "deceleration": 1.5,
            "battery_level": 100,  # Default battery level
            "vision_range": 5.0,
            "ball_detection_threshold": 0.7,
            "obstacle_detection_threshold": 0.6,
            "communication_range": 20.0
        }

    def set_parameters(self, parameters):
        self.parameters.update(parameters)
        print(f"Updated parameters for {self.name}")

    def send_to_robot(self, msg):
        if self.socket:
            self.socket.sendto(msg.encode(), (self.robot_ip, self.robot_port))
            print(f"Sent to {self.name}: {msg}")
        else:
            print(f"Socket not connected for {self.name}")

    def receive_from_robot(self):
        while self.connected:
            try:
                data, addr = self.socket.recvfrom(1024)
                self.lock.acquire()
                print(f"Received data from {self.name}: {data.decode()}")
                #TODO: Parse data and update self.ball_position, position, orientation, obstacles

                self.lock.release()
            except Exception as e:
                print(f"Error receiving data from {self.name}: {e}")
                break
