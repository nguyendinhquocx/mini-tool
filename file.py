import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import csv
from openpyxl import Workbook
import subprocess

# Hàm đổi tên (file hoặc thư mục)
def rename_items(folder_path, prefix="", old_text="", new_text="", mapping_file=None, is_folder=False):
    try:
        renamed_count = 0
        debug_info = []  # Debug information for logging
        
        if mapping_file:
            # Read mapping file
            df = pd.read_excel(mapping_file) if mapping_file.endswith('.xlsx') else pd.read_csv(mapping_file)
            debug_info.append(f"Loaded mapping file: {mapping_file} with {len(df)} rows")
            
            # Create mappings for folders and files
            folder_mapping = {}
            file_mapping = {}
            
            for idx, row in df.iterrows():
                try:
                    item_type = row['Loại']
                    old_name = row['Tên']
                    new_name = row['Tên mới'] if pd.notna(row['Tên mới']) else ""
                    path = row['Đường dẫn']
                    
                    # Only add to mapping if new name is provided and different from old name
                    if pd.notna(new_name) and new_name.strip() != "" and new_name != old_name:
                        if item_type == 'Thư mục':
                            folder_mapping[os.path.normpath(path)] = new_name
                        elif item_type == 'File':
                            file_mapping[os.path.normpath(path)] = new_name
                except Exception as row_e:
                    debug_info.append(f"Error in row {idx + 2}: {row_e}")
                    continue
            
            debug_info.append(f"Mappings created: {len(folder_mapping)} folders, {len(file_mapping)} files")
            
            # Rename folders and files
            for root, dirs, files in os.walk(folder_path, topdown=False):
                # Rename files
                for file in files:
                    file_path = os.path.normpath(os.path.join(root, file))
                    if file_path in file_mapping:
                        new_name = file_mapping[file_path] + os.path.splitext(file)[1]
                        new_path = os.path.join(root, new_name)
                        try:
                            os.rename(file_path, new_path)
                            debug_info.append(f"Renamed file: {file_path} -> {new_path}")
                            renamed_count += 1
                        except Exception as e:
                            debug_info.append(f"Error renaming file {file_path}: {e}")
                
                # Rename folders
                for dir in dirs:
                    dir_path = os.path.normpath(os.path.join(root, dir))
                    if dir_path in folder_mapping:
                        new_name = folder_mapping[dir_path]
                        new_path = os.path.join(os.path.dirname(dir_path), new_name)
                        try:
                            os.rename(dir_path, new_path)
                            debug_info.append(f"Renamed folder: {dir_path} -> {new_path}")
                            renamed_count += 1
                        except Exception as e:
                            debug_info.append(f"Error renaming folder {dir_path}: {e}")
        
        else:
            # Simple renaming without mapping file
            for item in os.listdir(folder_path):
                old_path = os.path.join(folder_path, item)
                if os.path.isfile(old_path):
                    new_name = prefix + item.replace(old_text, new_text)
                    new_path = os.path.join(folder_path, new_name)
                    try:
                        os.rename(old_path, new_path)
                        debug_info.append(f"Renamed file: {old_path} -> {new_path}")
                        renamed_count += 1
                    except Exception as e:
                        debug_info.append(f"Error renaming file {old_path}: {e}")
        
        # Write debug log
        with open("rename_debug.log", "w", encoding="utf-8") as log_file:
            log_file.write("\n".join(debug_info))
        
        if renamed_count == 0:
            debug_info.append("No items were renamed. Check input parameters or mapping file.")
            return False
        
        return True
    except Exception as e:
        debug_info.append(f"Critical error: {e}")
        with open("rename_error.log", "w", encoding="utf-8") as error_file:
            error_file.write("\n".join(debug_info))
        return False

# Hàm lấy thông tin file và thư mục từ thư mục
def get_items_info(root_path):
    folders_data = {}
    root_name = os.path.basename(root_path)
    folders_data[root_name] = []
    
    for folder_path, subdirs, files in os.walk(root_path):
        rel_folder = os.path.relpath(folder_path, root_path) if folder_path != root_path else ""
        
        if rel_folder == "":
            current_folder_key = root_name
        else:
            current_folder_key = rel_folder
            parent_folder = os.path.dirname(rel_folder) if os.path.dirname(rel_folder) else root_name
            if parent_folder not in folders_data:
                folders_data[parent_folder] = []
            
            folders_data[parent_folder].append({
                "folder": parent_folder,
                "name": os.path.basename(rel_folder),
                "path": os.path.abspath(folder_path),
                "type": "Thư mục"
            })
        
        if current_folder_key not in folders_data:
            folders_data[current_folder_key] = []
        
        for file in files:
            full_path = os.path.join(folder_path, file)
            folders_data[current_folder_key].append({
                "folder": current_folder_key,
                "name": os.path.splitext(file)[0],
                "path": os.path.abspath(full_path),
                "type": "File"
            })
    
    return folders_data

# Hàm mở file sau khi tải xuống
def open_file(file_path):
    try:
        if os.name == 'nt':
            os.startfile(file_path)
        elif os.name == 'posix':
            if os.path.exists('/usr/bin/open'):
                subprocess.call(['open', file_path])
            else:
                subprocess.call(['xdg-open', file_path])
        return True
    except Exception as e:
        print(f"Lỗi khi mở file: {e}")
        return False

# Hàm ghi file Excel cho tab "Xuất Info"
def write_to_excel_for_mapping(folders_data, output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Danh sách thư mục và file"
    
    # Add headers
    ws.append(["Thư mục", "Loại", "Tên", "Tên mới", "Đường dẫn"])
    
    # Prepare a combined list for sorting
    all_items = []
    
    # Get root folder name
    root_name = list(folders_data.keys())[0]
    
    # First add all folders
    for folder_key in folders_data:
        for item in folders_data[folder_key]:
            if item["type"] == "Thư mục":
                all_items.append(item)
    
    # Then add all files
    for folder_key in folders_data:
        for item in folders_data[folder_key]:
            if item["type"] == "File":
                all_items.append(item)
    
    # Add all items to the worksheet
    for item in all_items:
        ws.append([item["folder"], item["type"], item["name"], "", item["path"]])
    
    # Adjust column widths
    for col in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in col) + 2
        ws.column_dimensions[col[0].column_letter].width = max_length
    
    wb.save(output_path)
    
    if messagebox.askyesno("Thành công", f"Đã lưu file tại:\n{output_path}\n\nBạn có muốn mở file không?"):
        open_file(output_path)

# Hàm chọn thư mục
def select_folder(entry_var):
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Chọn thư mục chứa mục cần đổi tên")
    root.destroy()
    if folder_path:
        entry_var.set(folder_path)

# Hàm chọn file ánh xạ
def select_mapping_file(entry_var):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Chọn file ánh xạ (Excel/CSV)",
        filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")]
    )
    root.destroy()
    if file_path:
        entry_var.set(file_path)

# Hàm chọn thư mục lưu file đầu ra
def select_output_folder(entry_var):
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Chọn thư mục lưu kết quả")
    root.destroy()
    if folder_path:
        entry_var.set(folder_path)

# Hàm nhập tên file đầu ra
def get_output_filename(entry_var, file_format=".xlsx"):
    root = tk.Tk()
    root.withdraw()
    filename = filedialog.asksaveasfilename(
        title="Nhập tên file kết quả",
        defaultextension=file_format,
        filetypes=[(f"{file_format[1:].upper()} files", f"*{file_format}")],
        initialfile="file_list"
    )
    root.destroy()
    if filename:
        entry_var.set(filename)

# Giao diện chính
def main_app():
    root = tk.Tk()
    root.title("Đổi Tên File Hàng Loạt")
    root.geometry("550x500")
    root.resizable(False, False)

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 550) // 2
    y = (screen_height - 500) // 2
    root.geometry(f"550x500+{x}+{y}")
    
    style = ttk.Style()
    style.configure('TButton', font=('Arial', 10))
    style.configure('TLabel', font=('Arial', 10))
    style.configure('TEntry', font=('Arial', 10))
    style.configure('TNotebook', tabposition='n')
    style.configure('TNotebook.Tab', padding=[10, 2], font=('Arial', 9, 'bold'))

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text="Đổi File")

    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text="Ánh Xạ File")

    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text="Xuất Info")

    tab4 = ttk.Frame(notebook)
    notebook.add(tab4, text="Đổi Thư Mục")

    folder_path_tab1 = tk.StringVar()
    prefix_var_tab1 = tk.StringVar()
    old_text_var_tab1 = tk.StringVar()
    new_text_var_tab1 = tk.StringVar()

    def apply_rename_tab1():
        path = folder_path_tab1.get()
        prefix = prefix_var_tab1.get()
        old_text = old_text_var_tab1.get()
        new_text = new_text_var_tab1.get()

        if not path:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục!")
            return

        if not prefix and not old_text:
            messagebox.showerror("Lỗi", "Vui lòng nhập tiền tố hoặc ký tự cần thay!")
            return

        if rename_items(path, prefix, old_text, new_text, is_folder=False):
            messagebox.showinfo("Thành công", "Đã đổi tên file xong!")
        else:
            messagebox.showerror("Lỗi", "Không có file nào được đổi tên hoặc có lỗi xảy ra!")

    frame_tab1 = ttk.Frame(tab1, padding="10")
    frame_tab1.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame_tab1, text="Thư mục:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    entry_folder1 = ttk.Entry(frame_tab1, textvariable=folder_path_tab1, width=40)
    entry_folder1.grid(row=0, column=1, sticky=tk.W+tk.E, pady=(0, 5), padx=(5, 0))
    ttk.Button(frame_tab1, text="Chọn", width=8, command=lambda: select_folder(folder_path_tab1)).grid(row=0, column=2, padx=5, pady=(0, 5))

    ttk.Label(frame_tab1, text="Tiền tố:").grid(row=1, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab1, textvariable=prefix_var_tab1, width=40).grid(row=1, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))

    ttk.Label(frame_tab1, text="Ký tự cần thay:").grid(row=2, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab1, textvariable=old_text_var_tab1, width=40).grid(row=2, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))
    
    ttk.Label(frame_tab1, text="Ký tự thay thế:").grid(row=3, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab1, textvariable=new_text_var_tab1, width=40).grid(row=3, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))

    btn_frame1 = ttk.Frame(frame_tab1)
    btn_frame1.grid(row=4, column=0, columnspan=3, pady=20)
    ttk.Button(btn_frame1, text="Đổi Tên File", width=15, command=apply_rename_tab1).pack()

    folder_path_tab2 = tk.StringVar()
    mapping_file_tab2 = tk.StringVar()

    def apply_rename_tab2():
        path = folder_path_tab2.get()
        mapping_path = mapping_file_tab2.get()

        if not path:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục!")
            return
        
        if not mapping_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn file ánh xạ!")
            return

        if rename_items(path, mapping_file=mapping_path, is_folder=False):
            messagebox.showinfo("Thành công", "Đã đổi tên file theo ánh xạ xong!")
            if os.path.exists("rename_debug.log"):
                messagebox.showinfo("Debug Log", "Chi tiết quá trình đổi tên đã được ghi vào file rename_debug.log")
        else:
            messagebox.showerror("Lỗi", "Có lỗi xảy ra trong quá trình đổi tên! Kiểm tra file rename_error.log để biết thêm chi tiết.")

    frame_tab2 = ttk.Frame(tab2, padding="10")
    frame_tab2.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame_tab2, text="Thư mục:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    entry_folder2 = ttk.Entry(frame_tab2, textvariable=folder_path_tab2, width=40)
    entry_folder2.grid(row=0, column=1, sticky=tk.W+tk.E, pady=(0, 5), padx=(5, 0))
    ttk.Button(frame_tab2, text="Chọn", width=8, command=lambda: select_folder(folder_path_tab2)).grid(row=0, column=2, padx=5, pady=(0, 5))

    ttk.Label(frame_tab2, text="File ánh xạ:").grid(row=1, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab2, textvariable=mapping_file_tab2, width=40).grid(row=1, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))
    ttk.Button(frame_tab2, text="Chọn", width=8, command=lambda: select_mapping_file(mapping_file_tab2)).grid(row=1, column=2, padx=5, pady=5)

    btn_frame2 = ttk.Frame(frame_tab2)
    btn_frame2.grid(row=2, column=0, columnspan=3, pady=20)
    ttk.Button(btn_frame2, text="Đổi Tên File", width=15, command=apply_rename_tab2).pack()

    folder_path_tab3 = tk.StringVar()
    output_folder_tab3 = tk.StringVar()
    output_filename_tab3 = tk.StringVar()

    def apply_get_items_info():
        input_folder = folder_path_tab3.get()
        if not input_folder:
            messagebox.showerror("Lỗi", "Không chọn thư mục đầu vào!")
            return

        folders_data = get_items_info(input_folder)
        if not folders_data:
            messagebox.showerror("Lỗi", "Không tìm thấy file hoặc thư mục nào!")
            return

        output_folder = output_folder_tab3.get()
        if not output_folder:
            messagebox.showerror("Lỗi", "Không chọn thư mục lưu kết quả!")
            return

        output_filename = output_filename_tab3.get()
        if not output_filename:
            messagebox.showerror("Lỗi", "Không nhập tên file!")
            return

        try:
            write_to_excel_for_mapping(folders_data, output_filename)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file!\nChi tiết lỗi: {e}")

    frame_tab3 = ttk.Frame(tab3, padding="10")
    frame_tab3.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame_tab3, text="Thư mục đầu vào:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    entry_folder3 = ttk.Entry(frame_tab3, textvariable=folder_path_tab3, width=40)
    entry_folder3.grid(row=0, column=1, sticky=tk.W+tk.E, pady=(0, 5), padx=(5, 0))
    ttk.Button(frame_tab3, text="Chọn", width=8, command=lambda: select_folder(folder_path_tab3)).grid(row=0, column=2, padx=5, pady=(0, 5))

    ttk.Label(frame_tab3, text="Thư mục lưu kết quả:").grid(row=1, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab3, textvariable=output_folder_tab3, width=40).grid(row=1, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))
    ttk.Button(frame_tab3, text="Chọn", width=8, command=lambda: select_output_folder(output_folder_tab3)).grid(row=1, column=2, padx=5, pady=5)

    ttk.Label(frame_tab3, text="Tên file kết quả:").grid(row=2, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab3, textvariable=output_filename_tab3, width=40).grid(row=2, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))
    ttk.Button(frame_tab3, text="Chọn", width=8, command=lambda: get_output_filename(output_filename_tab3)).grid(row=2, column=2, padx=5, pady=5)

    btn_frame3 = ttk.Frame(frame_tab3)
    btn_frame3.grid(row=3, column=0, columnspan=3, pady=20)
    ttk.Button(btn_frame3, text="Lấy Thông Tin", width=15, command=apply_get_items_info).pack()

    folder_path_tab4 = tk.StringVar()
    prefix_var_tab4 = tk.StringVar()
    old_text_var_tab4 = tk.StringVar()
    new_text_var_tab4 = tk.StringVar()
    mapping_file_tab4 = tk.StringVar()

    def apply_rename_tab4():
        path = folder_path_tab4.get()
        prefix = prefix_var_tab4.get()
        old_text = old_text_var_tab4.get()
        new_text = new_text_var_tab4.get()
        mapping_path = mapping_file_tab4.get()

        if not path:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục!")
            return

        if mapping_path:
            if rename_items(path, mapping_file=mapping_path, is_folder=True):
                messagebox.showinfo("Thành công", "Đã đổi tên thư mục và file bên trong theo ánh xạ xong!")
                if os.path.exists("rename_debug.log"):
                    messagebox.showinfo("Debug Log", "Chi tiết quá trình đổi tên đã được ghi vào file rename_debug.log")
            else:
                messagebox.showinfo("Thông báo", "Có lỗi xảy ra trong quá trình đổi tên! Kiểm tra file rename_error.log để biết thêm chi tiết.")
        else:
            if not prefix and not old_text:
                messagebox.showerror("Lỗi", "Vui lòng nhập tiền tố hoặc ký tự cần thay!")
                return

            if rename_items(path, prefix, old_text, new_text, is_folder=True):
                messagebox.showinfo("Thành công", "Đã đổi tên thư mục và file bên trong xong!")
            else:
                messagebox.showerror("Lỗi", "Không có mục nào được đổi tên hoặc có lỗi xảy ra!")

    frame_tab4 = ttk.Frame(tab4, padding="10")
    frame_tab4.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame_tab4, text="Thư mục cha:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    entry_folder4 = ttk.Entry(frame_tab4, textvariable=folder_path_tab4, width=40)
    entry_folder4.grid(row=0, column=1, sticky=tk.W+tk.E, pady=(0, 5), padx=(5, 0))
    ttk.Button(frame_tab4, text="Chọn", width=8, command=lambda: select_folder(folder_path_tab4)).grid(row=0, column=2, padx=5, pady=(0, 5))

    ttk.Label(frame_tab4, text="Tiền tố:").grid(row=1, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab4, textvariable=prefix_var_tab4, width=40).grid(row=1, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))

    ttk.Label(frame_tab4, text="Ký tự cần thay:").grid(row=2, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab4, textvariable=old_text_var_tab4, width=40).grid(row=2, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))
    
    ttk.Label(frame_tab4, text="Ký tự thay thế:").grid(row=3, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab4, textvariable=new_text_var_tab4, width=40).grid(row=3, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))

    ttk.Label(frame_tab4, text="File ánh xạ:").grid(row=4, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame_tab4, textvariable=mapping_file_tab4, width=40).grid(row=4, column=1, sticky=tk.W+tk.E, pady=5, padx=(5, 0))
    ttk.Button(frame_tab4, text="Chọn", width=8, command=lambda: select_mapping_file(mapping_file_tab4)).grid(row=4, column=2, padx=5, pady=5)

    btn_frame4 = ttk.Frame(frame_tab4)
    btn_frame4.grid(row=5, column=0, columnspan=3, pady=20)
    ttk.Button(btn_frame4, text="Đổi Tên Thư Mục", width=15, command=apply_rename_tab4).pack()

    for tab in [frame_tab1, frame_tab2, frame_tab3, frame_tab4]:
        tab.columnconfigure(1, weight=1)

    root.mainloop()

if __name__ == "__main__":
    main_app()