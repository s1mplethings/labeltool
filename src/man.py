import os
import tkinter as tk
from tkinter import filedialog, simpledialog
from PIL import Image, ImageTk
import json


class ImageSelectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Selector")

        self.config_file = "config.json"
        self.log_file = "log.txt"
        self.load_config()

        self.frame = tk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.frame, cursor="cross")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(self.frame, width=200)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(self.sidebar)
        self.listbox.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.root.bind("<Return>", self.save_coordinates)
        self.root.bind("<space>", self.next_image)
        self.root.bind("<MouseWheel>", self.zoom)
        self.root.bind("<Delete>", self.delete_selection)

        self.rect = None
        self.start_x = None
        self.start_y = None
        self.current_x = None
        self.current_y = None
        self.h_line = None
        self.v_line = None

        self.image = None
        self.tk_image = None

        self.image_files = []
        self.current_image_index = 0
        self.coordinates = []

        self.colors = self.generate_light_colors(50)

        self.menu = tk.Menu(root)
        root.config(menu=self.menu)

        file_menu = tk.Menu(self.menu)
        self.menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Folder", command=self.open_folder)
        file_menu.add_command(label="Select Save Location", command=self.select_save_location)

        self.toolbar = tk.Frame(root, bd=1, relief=tk.RAISED)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.select_tool_btn = tk.Button(self.toolbar, text="Select Tool", command=self.activate_select_tool)
        self.select_tool_btn.pack(side=tk.LEFT, padx=2, pady=2)
        self.rect_tool_btn = tk.Button(self.toolbar, text="Rectangle Tool", command=self.activate_rect_tool)
        self.rect_tool_btn.pack(side=tk.LEFT, padx=2, pady=2)

        self.current_tool = 'rectangle'  # Default tool

        self.save_location = None
        self.zoom_factor = 1.0

        self.listbox.bind("<Double-1>", self.edit_name)

        if self.last_opened_folder:
            self.load_images_from_folder(self.last_opened_folder)
        if self.last_save_location:
            self.save_location = self.last_save_location

        self.selected_rect_idx = None

    def generate_light_colors(self, num_colors):
        colors = []
        step = 255 // (num_colors // 5)
        for i in range(150, 256, step):
            for j in range(150, 256, step):
                for k in range(150, 256, step):
                    if len(colors) < num_colors:
                        color = "#{:02x}{:02x}{:02x}".format(i, j, k)
                        colors.append(color)
        return colors

    def load_config(self):
        self.last_opened_folder = None
        self.last_save_location = None
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                config = json.load(f)
                self.last_opened_folder = config.get("last_opened_folder")
                self.last_save_location = config.get("last_save_location")

    def save_config(self):
        config = {
            "last_opened_folder": self.last_opened_folder,
            "last_save_location": self.last_save_location
        }
        with open(self.config_file, "w") as f:
            json.dump(config, f)

    def log(self, message):
        with open(self.log_file, "a") as log_file:
            log_file.write(message + "\n")

    def open_folder(self):
        folder_path = filedialog.askdirectory()
        if not folder_path:
            return

        self.last_opened_folder = folder_path
        self.save_config()
        self.load_images_from_folder(folder_path)

    def load_images_from_folder(self, folder_path):
        self.image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'gif'))]
        self.image_files.sort()
        self.current_image_index = 0
        self.load_image()

    def select_save_location(self):
        self.save_location = filedialog.askdirectory()
        if not self.save_location:
            self.save_location = None
        else:
            self.last_save_location = self.save_location
            self.save_config()

    def load_image(self):
        if self.current_image_index >= len(self.image_files):
            print("No more images.")
            return

        image_path = self.image_files[self.current_image_index]
        self.image = Image.open(image_path)
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.config(width=self.tk_image.width(), height=self.tk_image.height())
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        self.rect = None
        self.coordinates = []
        self.redraw_rectangles()

        self.log(f"Loaded image: {image_path}")

    def redraw_rectangles(self):
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.listbox.delete(0, tk.END)
        width = self.tk_image.width()
        height = self.tk_image.height()
        for i, (x0, y0, x1, y1, visibility, name) in enumerate(self.coordinates):
            x0 = x0 * width
            y0 = y0 * height
            x1 = x1 * width
            y1 = y1 * height
            color = self.colors[i % len(self.colors)]
            if self.selected_rect_idx == i:
                rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=3, tags=f"rect{i}")
                self.draw_corner_handles(x0, y0, x1, y1, color, i)
            else:
                rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, tags=f"rect{i}")
            self.canvas.create_text((x0 + x1) / 2, y0 - 10, text=name, fill=color, tags=f"text{i}")
            button = tk.Button(self.root, text=str(visibility), command=lambda idx=i: self.change_visibility(idx))
            self.canvas.create_window(x1, y1, window=button, anchor=tk.NW)
            self.canvas.tag_bind(f"rect{i}", "<Button-3>", lambda event, idx=i: self.change_visibility(idx))
            self.canvas.tag_bind(f"text{i}", "<Button-3>", lambda event, idx=i: self.change_visibility(idx))
            self.canvas.tag_bind(f"rect{i}", "<ButtonPress-1>", lambda event, idx=i: self.select_rectangle(event, idx))
            self.listbox.insert(tk.END, f"{name} - ({x0, y0, x1, y1})")
            self.listbox.itemconfig(tk.END, {'bg': color})

    def draw_corner_handles(self, x0, y0, x1, y1, color, idx):
        handle_size = 8
        self.canvas.create_rectangle(x0 - handle_size, y0 - handle_size, x0 + handle_size, y0 + handle_size, outline=color, fill=color, tags=f"handle_tl_{idx}")
        self.canvas.create_rectangle(x1 - handle_size, y0 - handle_size, x1 + handle_size, y0 + handle_size, outline=color, fill=color, tags=f"handle_tr_{idx}")
        self.canvas.create_rectangle(x0 - handle_size, y1 - handle_size, x0 + handle_size, y1 + handle_size, outline=color, fill=color, tags=f"handle_bl_{idx}")
        self.canvas.create_rectangle(x1 - handle_size, y1 - handle_size, x1 + handle_size, y1 + handle_size, outline=color, fill=color, tags=f"handle_br_{idx}")

        self.canvas.tag_bind(f"handle_tl_{idx}", "<ButtonPress-1>", lambda event, idx=idx: self.start_resize(event, idx, 'tl'))
        self.canvas.tag_bind(f"handle_tr_{idx}", "<ButtonPress-1>", lambda event, idx=idx: self.start_resize(event, idx, 'tr'))
        self.canvas.tag_bind(f"handle_bl_{idx}", "<ButtonPress-1>", lambda event, idx=idx: self.start_resize(event, idx, 'bl'))
        self.canvas.tag_bind(f"handle_br_{idx}", "<ButtonPress-1>", lambda event, idx=idx: self.start_resize(event, idx, 'br'))

    def change_visibility(self, idx):
        new_visibility = simpledialog.askinteger("Visibility", "Enter visibility (0, 1, 2):", minvalue=0, maxvalue=2)
        if new_visibility is not None:
            x0, y0, x1, y1, _, name = self.coordinates[idx]
            self.coordinates[idx] = (x0, y0, x1, y1, new_visibility, name)
            self.redraw_rectangles()

    def edit_name(self, event):
        selected_idx = self.listbox.curselection()
        if selected_idx:
            idx = selected_idx[0]
            _, _, _, _, visibility, _ = self.coordinates[idx]
            new_name = simpledialog.askstring("Edit Name", "Enter new name:")
            if new_name:
                self.coordinates[idx] = (*self.coordinates[idx][:4], visibility, new_name)
                self.coordinates.sort(key=lambda x: x[5])
                self.redraw_rectangles()

    def save_coordinates(self, event=None):
        if not self.coordinates:
            return

        if self.save_location:
            save_path = os.path.join(self.save_location, f"{os.path.splitext(os.path.basename(self.image_files[self.current_image_index]))[0]}.txt")
        else:
            save_path = f"{self.image_files[self.current_image_index]}.txt"

        width, height = self.image.size
        with open(save_path, "w") as file:
            file.write("0 ")
            for i, (x0, y0, x1, y1, visibility, name) in enumerate(sorted(self.coordinates, key=lambda x: x[5])):
                if x0 is not None and y0 is not None and x1 is not None and y1 is not None:
                    if visibility == 0:
                        center_x = 0.0
                        center_y = 0.0
                    else:
                        center_x = (x0 + x1) / 2
                        center_y = (y0 + y1) / 2
                    if i == 0:
                        box_width = abs(x1 - x0)
                        box_height = abs(y1 - y0)
                        file.write(f"{center_x:.6f} {center_y:.6f} {box_width:.6f} {box_height:.6f}")
                    else:
                        file.write(f" {center_x:.6f} {center_y:.6f} {float(visibility):.6f}")
        print(f"Coordinates saved to {save_path}")
        self.log(f"Coordinates saved to {save_path}")

    def next_image(self, event=None):
        self.save_coordinates()
        self.current_image_index += 1
        if self.current_image_index < len(self.image_files):
            self.load_image()
        else:
            print("No more images.")

    def on_button_press(self, event):
        if self.current_tool == 'rectangle':
            self.start_x = event.x
            self.start_y = event.y
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red")
            self.h_line = self.canvas.create_line(0, event.y, self.canvas.winfo_width(), event.y, fill="black", dash=(4, 2))
            self.v_line = self.canvas.create_line(event.x, 0, event.x, self.canvas.winfo_height(), fill="black", dash=(4, 2))
        elif self.current_tool == 'select' and self.selected_rect_idx is not None:
            self.start_x = event.x
            self.start_y = event.y

    def on_mouse_move(self, event):
        if self.current_tool == 'rectangle' and self.rect:
            self.current_x = event.x
            self.current_y = event.y
            self.canvas.coords(self.rect, self.start_x, self.start_y, self.current_x, self.current_y)
            self.canvas.coords(self.h_line, 0, self.current_y, self.canvas.winfo_width(), self.current_y)
            self.canvas.coords(self.v_line, self.current_x, 0, self.current_x, self.canvas.winfo_height())
        elif self.current_tool == 'select' and self.selected_rect_idx is not None:
            self.current_x = event.x
            self.current_y = event.y
            self.move_rectangle(event)
            self.start_x, self.start_y = self.current_x, self.current_y  # 更新开始位置

    def on_button_release(self, event):
        if self.current_tool == 'rectangle':
            self.current_x = event.x
            self.current_y = event.y
            if self.start_x is not None and self.start_y is not None and self.current_x is not None and self.current_y is not None:
                name = simpledialog.askstring("Name", "Enter name for this rectangle:")
                if not name:
                    name = f"Rect{len(self.coordinates) + 1}"
                self.coordinates.append((self.start_x/self.tk_image.width(), self.start_y/self.tk_image.height(), 
                                         self.current_x/self.tk_image.width(), self.current_y/self.tk_image.height(), 2, name))
                self.coordinates.sort(key=lambda x: x[5])
                self.redraw_rectangles()
                print(f"Selected coordinates: {(self.start_x, self.start_y, self.current_x, self.current_y)}")
            self.canvas.delete(self.rect)
            self.rect = None
            if self.h_line:
                self.canvas.delete(self.h_line)
                self.h_line = None
            if self.v_line:
                self.canvas.delete(self.v_line)
                self.v_line = None
        elif self.current_tool == 'select':
            self.start_x = None
            self.start_y = None
            self.canvas.bind("<B1-Motion>", self.on_mouse_move)
            self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def on_right_click(self, event):
        pass

    def zoom(self, event):
        if event.delta > 0:
            self.zoom_factor *= 1.1
        else:
            self.zoom_factor /= 1.1
        self.apply_zoom()

    def apply_zoom(self):
        if self.image:
            width, height = int(self.image.width * self.zoom_factor), int(self.image.height * self.zoom_factor)
            resized_image = self.image.resize((width, height))
            self.tk_image = ImageTk.PhotoImage(resized_image)
            self.canvas.config(width=width, height=height)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
            self.redraw_rectangles()
            for i, (x0, y0, x1, y1, visibility, name) in enumerate(self.coordinates):
                x0 = x0 * width
                y0 = y0 * height
                x1 = x1 * width
                y1 = y1 * height
                color = self.colors[i % len(self.colors)]
                rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, tags=f"rect{i}")
                self.canvas.create_text((x0 + x1) / 2, y0 - 10, text=name, fill=color, tags=f"text{i}")
                button = tk.Button(self.root, text=str(visibility), command=lambda idx=i: self.change_visibility(idx))
                self.canvas.create_window(x1, y1, window=button, anchor=tk.NW)
                self.canvas.tag_bind(f"rect{i}", "<Button-3>", lambda event, idx=i: self.change_visibility(idx))
                self.canvas.tag_bind(f"text{i}", "<Button-3>", lambda event, idx=i: self.change_visibility(idx))

    def activate_rect_tool(self):
        self.current_tool = 'rectangle'

    def activate_select_tool(self):
        self.current_tool = 'select'

    def select_rectangle(self, event, idx):
        self.selected_rect_idx = idx
        self.redraw_rectangles()

    def move_rectangle(self, event):
        if self.selected_rect_idx is not None:
            x0, y0, x1, y1, visibility, name = self.coordinates[self.selected_rect_idx]
            dx = event.x - self.start_x
            dy = event.y - self.start_y
            self.coordinates[self.selected_rect_idx] = (x0 + dx, y0 + dy, x1 + dx, y1 + dy, visibility, name)
            self.redraw_rectangles()

    def start_resize(self, event, idx, corner):
        self.selected_rect_idx = idx
        self.resize_corner = corner
        self.start_x = event.x
        self.start_y = event.y
        self.canvas.bind("<B1-Motion>", self.resize_rectangle)
        self.canvas.bind("<ButtonRelease-1>", self.stop_resize)

    def resize_rectangle(self, event):
        if self.selected_rect_idx is not None:
            x0, y0, x1, y1, visibility, name = self.coordinates[self.selected_rect_idx]
            if self.resize_corner == 'tl':
                self.coordinates[self.selected_rect_idx] = (event.x, event.y, x1, y1, visibility, name)
            elif self.resize_corner == 'tr':
                self.coordinates[self.selected_rect_idx] = (x0, event.y, event.x, y1, visibility, name)
            elif self.resize_corner == 'bl':
                self.coordinates[self.selected_rect_idx] = (event.x, y0, x1, event.y, visibility, name)
            elif self.resize_corner == 'br':
                self.coordinates[self.selected_rect_idx] = (x0, y0, event.x, event.y, visibility, name)
            self.redraw_rectangles()

    def stop_resize(self, event):
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.resize_corner = None
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def delete_selection(self, event):
        if self.selected_rect_idx is not None:
            del self.coordinates[self.selected_rect_idx]
            self.selected_rect_idx = None
            self.redraw_rectangles()
        elif self.listbox.curselection():
            selected_idx = self.listbox.curselection()[0]
            del self.coordinates[selected_idx]
            self.redraw_rectangles()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1400x800")  # Increase the resolution of the interface
    app = ImageSelectorApp(root)
    root.mainloop()
