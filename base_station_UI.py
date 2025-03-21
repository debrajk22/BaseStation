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

    def update_local_world_map(self, data):
        self.local_world_map = data

    def move(self, direction):
        print(f"Moving {self.name} in direction: {direction}")

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


class GlobalWorldMap:
    def __init__(self):
        # 12m x 9m field
        self.field_dimensions = (12, 9)
        # A global ball position
        self.ball_position = [6, 4.5]  # Center of the field
        self.obstacles = []

    def update_from_robots(self, robots):
        # Sensor fusion logic goes here
        self.ball_position = [0, 0]
        self.obstacles = []
        for robot in robots:
            robot.lock.acquire()
            self.ball_position[0] += robot.ball_position[0]
            self.ball_position[1] += robot.ball_position[1]
            self.obstacles.extend(robot.obstacles)
            robot.lock.release()
        self.ball_position[0] /= len(robots)
        self.ball_position[1] /= len(robots)

class BaseStationUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Team Era Base Station")
        self.root.geometry("1200x800")

        self.global_world = GlobalWorldMap()
        self.current_detailed_robot = None
        self.logging_text = None

        # HOME ROBOTS
        self.robots = [Robot(i + 1, "Player", color="blue") for i in range(5)]
        # Arbitrary positions
        self.robots[0].position = (2, 4)
        self.robots[0].orientation = 0
        self.robots[1].position = (3, 2)
        self.robots[1].orientation = 45
        self.robots[2].position = (4, 6)
        self.robots[2].orientation = 90
        self.robots[3].position = (2, 7)
        self.robots[3].orientation = 135
        self.robots[4].position = (1, 1)
        self.robots[4].orientation = 270

        # self.robots[0].robot_ip = "192.168.123.88"
        # self.robots[0].robot_port = 10001

        # OPPONENT ROBOTS
        self.opponents = [Robot(i + 1, "Opponent", color="red") for i in range(5)]
        # Arbitrary positions
        self.opponents[0].position = (8, 4)
        self.opponents[0].orientation = 180
        self.opponents[1].position = (9, 2)
        self.opponents[1].orientation = 220
        self.opponents[2].position = (10, 6)
        self.opponents[2].orientation = 45
        self.opponents[3].position = (8, 7)
        self.opponents[3].orientation = 315
        self.opponents[4].position = (10, 3)
        self.opponents[4].orientation = 90

        # We'll create logic after the UI so we can pass self to it
        self.logic = None

        self.setup_ui()
        self.robot_images = {}

    def setup_ui(self):
        # Banner
        banner_frame = tk.Frame(self.root, bg="#a8328d", height=80)
        banner_frame.pack(fill=tk.X)
        banner_frame.pack_propagate(0)

        # Left (Team Logo)
        try:
            team_logo_img = ImageTk.PhotoImage(
                Image.open("robocup_logo.png").resize((220, 70))
            )
            team_logo_label = tk.Label(banner_frame, image=team_logo_img, bg="#a8328d")
            team_logo_label.image = team_logo_img
        except Exception:
            team_logo_label = tk.Label(
                banner_frame, text="Team Logo", fg="white", bg="#a8328d", font=("Arial", 16)
            )
        team_logo_label.pack(side=tk.LEFT, padx=10)

        # Center (RoboCup MSL Logo)
        center_logo_frame = tk.Frame(banner_frame, bg="#a8328d")
        center_logo_frame.pack(side=tk.LEFT, expand=True)
        try:
            msl_logo_img = ImageTk.PhotoImage(
                Image.open("era_logo.png").resize((100, 100))
            )
            msl_logo_label = tk.Label(center_logo_frame, image=msl_logo_img, bg="#a8328d")
            msl_logo_label.image = msl_logo_img
            msl_logo_label.pack()
        except Exception:
            msl_logo_label = tk.Label(
                center_logo_frame,
                text="RoboCup MSL Logo",
                fg="white",
                bg="#a8328d",
                font=("Arial", 16),
            )
            msl_logo_label.pack()

        # Right (Institute Logo) + Connect to RefBox
        right_frame = tk.Frame(banner_frame, bg="#a8328d")
        right_frame.pack(side=tk.RIGHT, padx=10)

        # Institute logo
        try:
            institute_logo_img = ImageTk.PhotoImage(
                Image.open("iitk_logo.png").resize((75, 75))
            )
            institute_logo_label = tk.Label(right_frame, image=institute_logo_img, bg="#a8328d")
            institute_logo_label.image = institute_logo_img
            institute_logo_label.pack(side=tk.RIGHT, padx=5)
        except Exception:
            institute_logo_label = tk.Label(
                right_frame, text="Institute Logo", fg="white", bg="#a8328d", font=("Arial", 16)
            )
            institute_logo_label.pack(side=tk.RIGHT, padx=5)

        # Connect to RefBox button
        self.refbox_status_label = tk.Label(right_frame, text="RefBox: Disconnected", fg="red", bg="#a8328d")
        self.refbox_status_label.pack(side=tk.RIGHT, padx=10)

        self.refbox_connect_btn = tk.Button(
            right_frame, text="Connect to RefBox", command=self.handle_refbox_connect
        )
        self.refbox_connect_btn.pack(side=tk.RIGHT, padx=5)

        # Main content
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Panel: Robot Selection
        left_panel = tk.Frame(content_frame, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        left_panel.pack_propagate(False)

        robot_grid = tk.Frame(left_panel)
        robot_grid.pack(fill=tk.BOTH, expand=True)

        # 5 robots in a 2-col layout
        # 5 robots in a 2-col layout
        for i, robot in enumerate(self.robots):
            row = i // 2
            col = i % 2
            robot_frame = tk.Frame(robot_grid, width=180, height=180, bd=2, relief=tk.RAISED)
            robot_frame.grid(row=row, column=col, padx=5, pady=5)
            robot_frame.grid_propagate(False)

            tk.Label(robot_frame, text=f"Player {robot.robot_id}", font=("Arial", 12)).pack(pady=5)

            # Load and place bot image
            try:
                bot_img = Image.open("bot.png").resize((150, 120))
                bot_photo = ImageTk.PhotoImage(bot_img)
                # Create a label with the image. The transparent parts will merge with the background.
                robot_image_label = tk.Label(robot_frame, image=bot_photo, bg=robot_frame.cget("bg"))
                robot_image_label.image = bot_photo  # keep a reference
            except Exception as e:
                print(f"Error loading image: {e}")
                robot_image_label = tk.Label(robot_frame, text="No Image", fg="black")
            robot_image_label.pack()

            # Bind click event if needed for detailed view
            robot_image_label.bind("<Button-1>", lambda e, r=robot: self.show_robot_detail(r))

            # Status indicator + Battery
            status_text = "Connected" if robot.connected else "Disconnected"
            status_color = "green" if robot.connected else "red"
            status_label = tk.Label(robot_frame, text=status_text, fg=status_color, font=("Arial", 10, "bold"))
            status_label.pack()

            battery_str = f"Battery: {robot.parameters['battery_level']}%"
            battery_label = tk.Label(robot_frame, text=battery_str, fg="blue", font=("Arial", 10))
            battery_label.pack()

            # Store references for updates
            robot.status_label = status_label
            robot.battery_label = battery_label


        # Center Panel: Field View
        middle_panel = tk.Frame(content_frame)
        middle_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(middle_panel, text="Field", font=("Arial", 12, "bold")).pack(pady=5)
        self.field_canvas = tk.Canvas(middle_panel, bg="green", height=400)
        self.field_canvas.pack(fill=tk.BOTH, expand=True, pady=5)

        self.draw_field()
        self.field_canvas.bind("<Configure>", lambda e: self.redraw_field())

        tk.Label(middle_panel, text="Global World Map").pack()

        # Right Panel: Logging
        logging_panel = tk.Frame(content_frame, width=300, bd=2, relief=tk.SUNKEN)
        logging_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        logging_panel.pack_propagate(False)

        tk.Label(logging_panel, text="Logs", font=("Arial", 12, "bold")).pack(pady=5)
        self.logging_text = tk.Text(logging_panel, wrap=tk.WORD)
        self.logging_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Logging buttons
        log_buttons_frame = tk.Frame(logging_panel)
        log_buttons_frame.pack(fill=tk.X, pady=5)
        tk.Button(log_buttons_frame, text="Start Logging", command=self.start_logging).pack(side=tk.LEFT, padx=5)
        tk.Button(log_buttons_frame, text="Stop Logging", command=self.stop_logging).pack(side=tk.LEFT, padx=5)
        tk.Button(log_buttons_frame, text="Save Log", command=self.save_log).pack(side=tk.LEFT, padx=5)

        # Bottom Panel: Additional Buttons
        bottom_panel = tk.Frame(main_frame, height=50)
        bottom_panel.pack(fill=tk.X, pady=10)
        additional_btn_frame = tk.Frame(bottom_panel)
        additional_btn_frame.pack(side=tk.LEFT, padx=20)

        functions = ["Play/Pause", "Reset Position", "Camera Check"]
        for func in functions:
            tk.Button(additional_btn_frame, text=func, width=12).pack(side=tk.LEFT, padx=5)

    ###########################################################################
    # RefBox UI Integration
    ###########################################################################
    def handle_refbox_connect(self):
        """Called when the user clicks 'Connect to RefBox'."""
        if self.logic and not self.logic.refbox_connected:
            self.logic.connect_to_refbox(ip="127.0.0.1", port=28097)  # Adjust IP/port as needed
        else:
            self.log_message("RefBox already connected or logic not ready.\n")

    def update_refbox_status(self, connected):
        """Update the label in the banner to show refbox status."""
        if connected:
            self.refbox_status_label.config(text="RefBox: Connected", fg="green")
            self.log_message("Connected to RefBox.\n")
        else:
            self.refbox_status_label.config(text="RefBox: Disconnected", fg="red")
            self.log_message("Disconnected from RefBox.\n")

    def log_refbox_message(self, message):
        """Log a new message from the RefBox into the UI."""
        self.log_message(f"RefBox => {message}\n")

    ###########################################################################
    # Field / Robot Drawing
    ###########################################################################
    def draw_field(self):
        """Draw field lines, robots, and the ball."""
        w = self.field_canvas.winfo_width() or 600
        h = self.field_canvas.winfo_height() or 400
        self.field_canvas.delete("all")
        self.draw_soccer_lines(self.field_canvas, w, h)
        self.draw_robots_on_field(self.field_canvas, self.robots, w, h)
        self.draw_robots_on_field(self.field_canvas, self.opponents, w, h)
        self.draw_ball_on_field(self.field_canvas, w, h)

    def redraw_field(self):
        self.draw_field()

    def draw_soccer_lines(self, canvas, w, h):
        canvas.create_rectangle(10, 10, w - 10, h - 10, outline="white", width=2)
        canvas.create_line(w // 2, 10, w // 2, h - 10, fill="white", width=2)
        center_x, center_y = w // 2, h // 2
        circle_radius = min(w, h) * 0.1
        canvas.create_oval(
            center_x - circle_radius,
            center_y - circle_radius,
            center_x + circle_radius,
            center_y + circle_radius,
            outline="white",
            width=2,
        )
        canvas.create_rectangle(5, h // 2 - 50, 10, h // 2 + 50, fill="blue", outline="blue")
        canvas.create_rectangle(w - 10, h // 2 - 50, w - 5, h // 2 + 50, fill="yellow", outline="yellow")

    def draw_robots_on_field(self, canvas, robots, w, h):
        field_w, field_h = self.global_world.field_dimensions
        scale_x = (w - 20) / field_w
        scale_y = (h - 20) / field_h

        for robot in robots:
            rx, ry = robot.position
            cx = 10 + rx * scale_x
            cy = 10 + ry * scale_y
            r = 10
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=robot.color, outline="white", width=2)
            angle_rad = math.radians(robot.orientation)
            line_len = 20
            x_end = cx + line_len * math.cos(angle_rad)
            y_end = cy + line_len * math.sin(angle_rad)
            canvas.create_line(cx, cy, x_end, y_end, fill="white", width=2)

    def draw_ball_on_field(self, canvas, w, h):
        field_w, field_h = self.global_world.field_dimensions
        bx, by = self.global_world.ball_position
        scale_x = (w - 20) / field_w
        scale_y = (h - 20) / field_h
        cx = 10 + bx * scale_x
        cy = 10 + by * scale_y
        ball_radius = 6
        canvas.create_oval(cx - ball_radius, cy - ball_radius, cx + ball_radius, cy + ball_radius,
                           fill="white", outline="black", width=2)

    ###########################################################################
    # Detailed Robot View
    ###########################################################################
    def show_robot_detail(self, robot):
        self.current_detailed_robot = robot
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Detailed View - {robot.name}")
        detail_window.geometry("800x600")

        info_frame = tk.Frame(detail_window)
        info_frame.pack(fill=tk.X, pady=10)

        tk.Label(info_frame, text=f"{robot.name}", font=("Arial", 16)).pack(side=tk.LEFT, padx=20)
        tk.Label(info_frame,
                 text=f"Status: {'Connected' if robot.connected else 'Disconnected'}",
                 fg="green" if robot.connected else "red",
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=20)
        tk.Label(info_frame, text=f"Battery: {robot.parameters['battery_level']}%", font=("Arial", 12)).pack(side=tk.LEFT, padx=20)

        tk.Button(info_frame, text="Change Parameters", command=self.open_parameters_window).pack(side=tk.RIGHT, padx=20)

        content_frame = tk.Frame(detail_window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # Left: Parameters
        left_section = tk.Frame(content_frame, width=300)
        left_section.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, expand=True)
        left_section.pack_propagate(False)

        param_frame = tk.LabelFrame(left_section, text="Parameters")
        param_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        row = 0
        for param, value in robot.parameters.items():
            tk.Label(param_frame, text=param.replace('_', ' ').title()).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            tk.Label(param_frame, text=str(value)).grid(row=row, column=1, sticky="e", padx=10, pady=5)
            row += 1

        # Right: Local World Map
        right_section = tk.Frame(content_frame)
        right_section.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

        tk.Label(right_section, text="Local World Map").pack(pady=5)
        local_map_canvas = tk.Canvas(right_section, bg="lightgreen")
        local_map_canvas.pack(fill=tk.BOTH, expand=True, pady=5)

        def draw_local_map_lines(event=None):
            w_local = local_map_canvas.winfo_width()
            h_local = local_map_canvas.winfo_height()
            local_map_canvas.delete("all")
            self.draw_soccer_lines(local_map_canvas, w_local, h_local)

            # Robot in the center
            cx, cy = w_local // 2, h_local // 2
            rr = 15
            local_map_canvas.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                                         fill=robot.color, outline="white", width=2)
            angle_rad = math.radians(robot.orientation)
            line_len = 30
            x_end = cx + line_len * math.cos(angle_rad)
            y_end = cy + line_len * math.sin(angle_rad)
            local_map_canvas.create_line(cx, cy, x_end, y_end, fill="white", width=3)

            # Demo ball
            local_map_canvas.create_oval(cx + 50 - rr, cy - rr, cx + 50 + rr, cy + rr,
                                         fill="white", outline="black", width=2)

        local_map_canvas.bind("<Configure>", draw_local_map_lines)

        # Bottom: Additional Controls
        control_frame = tk.Frame(detail_window)
        control_frame.pack(fill=tk.X, pady=10)

        tk.Button(control_frame, text="test kicking angle").pack(side=tk.LEFT, padx=10)
        tk.Button(control_frame, text="Charge").pack(side=tk.LEFT, padx=10)
        tk.Button(control_frame, text="Kick").pack(side=tk.LEFT, padx=10)
        tk.Button(control_frame, text="Close", command=detail_window.destroy).pack(side=tk.RIGHT, padx=20)

        # Movement Controls
        movement_controls_frame = tk.Frame(detail_window)
        movement_controls_frame.pack(pady=10)

        tk.Button(movement_controls_frame, text="↑", width=5, command=lambda: self.move_robot("forward")).grid(row=0, column=1)
        tk.Button(movement_controls_frame, text="←", width=5, command=lambda: self.move_robot("left")).grid(row=1, column=0)
        tk.Button(movement_controls_frame, text="Stop", width=5, command=lambda: self.move_robot("stop")).grid(row=1, column=1)
        tk.Button(movement_controls_frame, text="→", width=5, command=lambda: self.move_robot("right")).grid(row=1, column=2)
        tk.Button(movement_controls_frame, text="↓", width=5, command=lambda: self.move_robot("backward")).grid(row=2, column=1)
        tk.Button(movement_controls_frame, text="⟲", width=5, command=lambda: self.move_robot("rotate_left")).grid(row=3, column=0, pady=5)
        tk.Button(movement_controls_frame, text="⟳", width=5, command=lambda: self.move_robot("rotate_right")).grid(row=3, column=2, pady=5)

    ###########################################################################
    # Parameters Window
    ###########################################################################
    def open_parameters_window(self):
        if not self.current_detailed_robot:
            self.current_detailed_robot = self.robots[0]

        param_window = tk.Toplevel(self.root)
        param_window.title(f"Parameters - {self.current_detailed_robot.name}")
        param_window.geometry("500x600")

        param_frame = tk.Frame(param_window)
        param_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        tk.Label(param_frame, text="Robot Parameters", font=("Arial", 14, "bold")).pack(pady=10)

        entries = {}
        for param, value in self.current_detailed_robot.parameters.items():
            row_frame = tk.Frame(param_frame)
            row_frame.pack(fill=tk.X, pady=5)

            tk.Label(row_frame, text=param.replace('_', ' ').title() + ":", width=20, anchor="w").pack(side=tk.LEFT)
            entry = tk.Entry(row_frame, width=15)
            entry.insert(0, str(value))
            entry.pack(side=tk.LEFT, padx=10)
            entries[param] = entry

        buttons_frame = tk.Frame(param_window)
        buttons_frame.pack(fill=tk.X, pady=10)

        def save_parameters():
            try:
                for param, entry in entries.items():
                    value = float(entry.get())
                    self.current_detailed_robot.parameters[param] = value
                self.save_parameters_to_file()
                messagebox.showinfo("Success", "Parameters saved successfully!")
            except ValueError:
                messagebox.showerror("Error", "Invalid parameter value. Please enter numeric values.")

        def load_parameters():
            filename = filedialog.askopenfilename(
                title="Load Parameters",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                try:
                    with open(filename, 'r') as f:
                        params = json.load(f)
                    for param, val in params.items():
                        if param in entries:
                            entries[param].delete(0, tk.END)
                            entries[param].insert(0, str(val))
                    messagebox.showinfo("Success", "Parameters loaded successfully!")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load parameters: {str(e)}")

        def send_parameters():
            try:
                for param, entry in entries.items():
                    value = float(entry.get())
                    self.current_detailed_robot.parameters[param] = value
                # For demonstration: print them
                print(f"Sending parameters to {self.current_detailed_robot.name}:")
                for param, val in self.current_detailed_robot.parameters.items():
                    print(f"  {param}: {val}")
                    self.current_detailed_robot.send_to_robot(f"SET {param} {val}")
                messagebox.showinfo("Success", "Parameters sent to robot!")
            except ValueError:
                messagebox.showerror("Error", "Invalid parameter value. Please enter numeric values.")

        def send_to_all():
            """Send the same parameter values to all robots."""
            try:
                # Gather the new param values from entries
                new_params = {}
                for param, entry in entries.items():
                    new_params[param] = float(entry.get())

                # Update each robot
                for robot in self.robots:
                    robot.parameters.update(new_params)
                    print(f"Sending parameters to {robot.name}:")
                    for p, val in robot.parameters.items():
                        print(f"  {p}: {val}")
                        robot.send_to_robot(f"SET {p} {val}")
                messagebox.showinfo("Success", "Parameters sent to ALL robots!")
            except ValueError:
                messagebox.showerror("Error", "Invalid parameter value. Please enter numeric values.")

        tk.Button(buttons_frame, text="Load", command=load_parameters).pack(side=tk.LEFT, padx=10)
        tk.Button(buttons_frame, text="Save", command=save_parameters).pack(side=tk.LEFT, padx=10)
        tk.Button(buttons_frame, text="Send to Robot", command=send_parameters).pack(side=tk.LEFT, padx=10)
        tk.Button(buttons_frame, text="Send to All", command=send_to_all).pack(side=tk.LEFT, padx=10)
        tk.Button(buttons_frame, text="Close", command=param_window.destroy).pack(side=tk.RIGHT, padx=10)

    def save_parameters_to_file(self):
        filename = filedialog.asksaveasfilename(
            title="Save Parameters",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.current_detailed_robot.parameters, f, indent=4)

    ###########################################################################
    # Robot Movement / Logging
    ###########################################################################
    def move_robot(self, direction):
        if self.current_detailed_robot:
            self.current_detailed_robot.move(direction)
            self.log_message(f"Moved {self.current_detailed_robot.name} {direction}\n")
        else:
            print("No robot selected")

    def start_logging(self):
        self.log_message("Logging started...\n")

    def stop_logging(self):
        self.log_message("Logging stopped.\n")

    def save_log(self):
        filename = filedialog.asksaveasfilename(
            title="Save Log",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(self.logging_text.get("1.0", tk.END))
            print(f"Log saved to {filename}")

    def log_message(self, msg):
        """Append a message to the logging text box."""
        if self.logging_text:
            self.logging_text.insert(tk.END, msg)
            self.logging_text.see(tk.END)