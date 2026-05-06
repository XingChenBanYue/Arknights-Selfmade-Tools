import tkinter as tk
from tkinter import ttk, simpledialog, colorchooser, messagebox, filedialog
from copy import deepcopy
import json
import os
import random

DATA_FILE = "ark_tool_data.json"

# 开发者个人简介（可直接在此处编辑）
DEVELOPER_INFO = (
    "开发者：@XingChen-星晨伴月\n"
    "Bilibili:@XingChen-星晨伴月\n"
    "简介：不会写谱的Phigros自制谱师，偶尔写点小程序\n"
    "当前版本：1.0.0 Pre\n"
    "如需反馈Bug或提出建议，请前往644408460进行反馈提议\n"
)


# ===============================
# 数据处理
# ===============================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "stage_categories": ["主线"],
            "condition_categories": ["干员类", "时间类"],
            "stages": [],
            "conditions": []
        }

    def normalize_categories(cat_list, default_color, is_condition=False):
        new_list = []
        for cat in cat_list:
            if isinstance(cat, str):
                cat_dict = {"name": cat, "color": default_color, "folded": False, "excluded": False}
                # 条件分类才需要 min/max 数量限制
                if is_condition:
                    cat_dict["min_count"] = 0
                    cat_dict["max_count"] = 10
                new_list.append(cat_dict)
            elif isinstance(cat, dict):
                cat.setdefault("folded", False)
                cat.setdefault("color", default_color)
                cat.setdefault("excluded", False)
                if is_condition:
                    cat.setdefault("min_count", 0)
                    cat.setdefault("max_count", 10)
                new_list.append(cat)
        return new_list

    data["stage_categories"] = normalize_categories(data.get("stage_categories", ["主线"]), "#7aa2f7", is_condition=False)
    data["condition_categories"] = normalize_categories(data.get("condition_categories", ["干员类","时间类"]), "#f7aa7a", is_condition=True)

    for s in data.get("stages", []):
        s.setdefault("category", data["stage_categories"][0]["name"])
        s.setdefault("color", "#ffffff")
        s.setdefault("locked", False)
        s.setdefault("excluded", False)

    for c in data.get("conditions", []):
        c.setdefault("category", data["condition_categories"][0]["name"])
        c.setdefault("color", "#ffcc66")
        c.setdefault("locked", False)
        c.setdefault("excluded", False)

    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def validate_json_format(data):
    """验证JSON数据格式是否正确"""
    try:
        # 检查必需的顶级键
        required_keys = ["stage_categories", "condition_categories", "stages", "conditions"]
        for key in required_keys:
            if key not in data:
                return False, f"缺少必需的字段：{key}"
        
        # 验证分类结构
        for cat in data["stage_categories"]:
            if not isinstance(cat, dict) or "name" not in cat:
                return False, "关卡分类格式错误：每个分类必须是字典且包含'name'字段"
        
        for cat in data["condition_categories"]:
            if not isinstance(cat, dict) or "name" not in cat:
                return False, "条件分类格式错误：每个分类必须是字典且包含'name'字段"
        
        # 验证关卡结构
        for stage in data["stages"]:
            if not isinstance(stage, dict) or "name" not in stage or "category" not in stage:
                return False, "关卡格式错误：每个关卡必须是字典且包含'name'和'category'字段"
        
        # 验证条件结构
        for cond in data["conditions"]:
            if not isinstance(cond, dict) or "name" not in cond or "category" not in cond:
                return False, "条件格式错误：每个条件必须是字典且包含'name'和'category'字段"
        
        return True, "JSON格式正确"
    except Exception as e:
        return False, f"JSON验证异常：{str(e)}"

def export_data(data, suggested_name=None):
    """导出数据到自定义位置。仅保存传入的 data（可为当前页）。
    suggested_name: 可选，作为保存对话框的默认文件名（无扩展名）
    """
    # 验证数据格式
    is_valid, msg = validate_json_format(data)
    if not is_valid:
        messagebox.showerror("导出失败", f"数据格式错误：{msg}")
        return False

    # 构建初始文件名
    init_name = (suggested_name + ".json") if suggested_name else "ark_tool_data.json"

    # 打开文件保存对话框
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        initialfile=init_name
    )

    if not file_path:
        return False

    try:
        # 再次验证要导出的数据
        is_valid, msg = validate_json_format(data)
        if not is_valid:
            messagebox.showerror("导出失败", f"数据格式错误：{msg}")
            return False

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        messagebox.showinfo("导出成功", f"数据已导出到：\n{file_path}")
        return True
    except Exception as e:
        messagebox.showerror("导出失败", f"无法保存文件：{str(e)}")
        return False

# ===============================
# 可拖拽 Listbox（禁止拖分类标题）
# ===============================
class DragListbox(tk.Listbox):
    def __init__(self, master, pool_data=None, is_stage=True, cat_var=None, categories=None, refresh_func=None, **kw):
        super().__init__(master, **kw)
        self.cur = None
        self.pool_data = pool_data
        self.is_stage = is_stage
        self.cat_var = cat_var
        self.categories = categories
        self.refresh_func = refresh_func
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<Double-Button-1>", self.on_double_click)

    def on_click(self, event):
        self.cur = self.nearest(event.y)

    def on_drag(self, event):
        i = self.nearest(event.y)
        if self.cur is None or i == self.cur:
            return
        a = self.get(self.cur)
        b = self.get(i)
        if a.startswith("[") or b.startswith("[") or a.startswith("☑") or a.startswith("☐") or b.startswith("☑") or b.startswith("☐"):
            return
        
        # 提取项目名称的辅助函数
        def extract_item_name(text):
            text = text.strip()
            if text.startswith("☑") or text.startswith("☐"):
                text = text.replace("☑ ", "").replace("☐ ", "")
            if "[排除]" in text:
                text = text.replace("[排除] ", "")
            # 去掉分类信息 [...]
            if "[" in text and "]" in text:
                text = text[:text.rfind("[")].strip()
            return text
        
        item_name_a = extract_item_name(a)
        item_name_b = extract_item_name(b)
        
        # 拖到分类标题自动归类（全部视图下）- 注意新版本没有分类标题，所以此功能可能不再适用
        if self.cat_var and self.cat_var.get() == "全部":
            # 检查b是否看起来像是分类（但在新版本中不会有这样的行）
            if "[" in b and "]" in b and not any(c["name"] in b for c in self.categories or []):
                # 这可能是分类标签，但在新版本中每个项目都有分类标签
                pass
        
        # 普通交换顺序（同步底层数据）
        # 先更新UI顺序
        self.delete(self.cur)
        self.insert(i, a)
        self.cur = i
        
        # 然后根据UI顺序重建pool_data的顺序
        if self.cat_var and self.cat_var.get() == "全部":
            # 全部视图：需要根据UI中的显示顺序重新排列pool_data
            new_order = []
            for j in range(self.size()):
                ui_text = self.get(j).strip()
                # 提取实际的项目名称
                extracted_name = extract_item_name(ui_text)
                # 在pool_data中找到对应的项目对象
                for item in self.pool_data:
                    if item["name"] == extracted_name:
                        if item not in new_order:
                            new_order.append(item)
                        break
            # 更新pool_data的顺序
            self.pool_data[:] = new_order
        else:
            # 分类视图：只需要在该分类内调整顺序
            # 获取当前分类名称
            current_cat = self.cat_var.get()
            cat_items = [item for item in self.pool_data if item["category"] == current_cat]
            new_order = []
            for j in range(self.size()):
                ui_text = self.get(j).strip()
                extracted_name = extract_item_name(ui_text)
                for item in cat_items:
                    if item["name"] == extracted_name:
                        if item not in new_order:
                            new_order.append(item)
                        break
            # 更新pool_data中该分类的项目顺序
            other_items = [item for item in self.pool_data if item["category"] != current_cat]
            self.pool_data[:] = other_items + new_order
        
        save_data(app.data)
        # 更新锁定关卡下拉框
        if self.is_stage:
            app.update_lock_stage_options()

    def on_double_click(self, event):
        """处理双击事件：双击分类标题进行收缩/展开"""
        idx = self.nearest(event.y)
        if idx < 0:
            return
        text = self.get(idx).strip()
        # 检查是否是分类标题
        if text.startswith("[") and "]" in text:
            # 提取分类名称
            cat_name = text.strip("[]").strip("+- (排除)")
            # 在全部视图下处理
            if self.cat_var and self.cat_var.get() == "全部" and self.categories:
                # 找到对应的分类并切换folded状态
                for cat in self.categories:
                    if cat["name"] == cat_name:
                        cat["folded"] = not cat.get("folded", False)
                        save_data(app.data)
                        # 刷新显示
                        if self.refresh_func:
                            self.refresh_func()
                        break

# ===============================
# 主程序
# ===============================
class ToolApp:
    def __init__(self, root):
        global app
        app = self
        self.root = root
        root.title("明日方舟随机挑战条件生成器 Arknights Random Challenge Condition Selector")
        root.geometry("1200x720")
        # 最小窗口尺寸，防止窗口缩小导致控件遮挡或按钮消失
        root.minsize(900, 600)
        # 顶部菜单：文件（导入/导出/配置页）
        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="导入数据", command=lambda: self.import_data_action())
        file_menu.add_command(label="导出数据", command=lambda: self.export_data_action())
        file_menu.add_separator()
        file_menu.add_command(label="新建配置页(空)", command=lambda: self.create_new_page(copy_current=False))
        file_menu.add_command(label="新建配置页(复制当前)", command=lambda: self.create_new_page(copy_current=True))
        file_menu.add_separator()
        file_menu.add_command(label="重命名当前配置页", command=self.rename_current_page)
        file_menu.add_command(label="清空当前配置页", command=self.clear_current_page)
        file_menu.add_command(label="删除当前配置页", command=self.delete_current_page)
        file_menu.add_separator()
        file_menu.add_command(label="上一页", command=self.prev_page)
        file_menu.add_command(label="下一页", command=self.next_page)
        # 分页开关
        self.paging_enabled = tk.BooleanVar(value=False)
        file_menu.add_checkbutton(label="启用分页", variable=self.paging_enabled, command=self.update_paging_state)
        menubar.add_cascade(label="文件", menu=file_menu)
        # 在文件按钮右侧添加“说明”快捷入口
        menubar.add_command(label="说明", command=self.show_about)
        root.config(menu=menubar)
        # 读取数据并初始化分页结构
        self.data = load_data()
        self.pages = [deepcopy(self.data)]
        self.current_page = 0
        # 页面标题列表（与 pages 对应）
        self.page_titles = ["配置1"]

        self.main = tk.PanedWindow(root, orient="horizontal")
        self.main.pack(fill="both", expand=True)

        self.left = tk.PanedWindow(self.main, orient="vertical")
        self.right = tk.Frame(self.main)

        # 保证左右两侧面板有足够的最小宽度，避免相互覆盖
        self.main.add(self.left, minsize=450)
        self.main.add(self.right, minsize=400)

        self.stage_frame = self.build_pool("关卡池", self.data["stage_categories"], self.data["stages"], True)
        self.cond_frame = self.build_pool("条件池", self.data["condition_categories"], self.data["conditions"], False)

        # 左侧为垂直分割，设置相同权重使两个池初始窗口大小一样
        self.left.add(self.stage_frame, minsize=260, height=360)
        self.left.add(self.cond_frame, minsize=260, height=360)

        self.build_result()

    # ===============================
    # 构建池子
    # ===============================
    def build_pool(self, title, categories, items, is_stage=True):
        frame = ttk.LabelFrame(self.left, text=title)
        top = ttk.Frame(frame)
        top.pack(fill="x")
        cat_var = tk.StringVar(value="全部")
        cat_box = ttk.Combobox(
            top,
            values=["全部"] + [cat["name"] for cat in categories],
            textvariable=cat_var,
            state="readonly",
            width=10
        )
        cat_box.pack(side="left", padx=5)
        ttk.Button(top, text="+分类", command=lambda:self.add_category(categories, cat_box, items)).pack(side="left")
        ttk.Button(top, text="编辑分类", command=lambda:self.edit_category(categories, cat_box, items)).pack(side="left")
        ttk.Button(top, text="删除分类", command=lambda:self.delete_category(categories, cat_box, items)).pack(side="left")

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        # 条件锁定/排除勾选框映射
        cond_vars = {}
        exclude_vars = {}
        if not is_stage:
            for c in items:
                cond_vars[c["name"]] = tk.BooleanVar(value=c.get("locked", False))
                exclude_vars[c["name"]] = tk.BooleanVar(value=c.get("excluded", False))
            self.cond_vars = cond_vars
            self.cond_exclude = exclude_vars

        def refresh():
            listbox.delete(0, tk.END)
            if cat_var.get() == "全部":
                # 全部视图：按条件类型分组排列，同一类型的条件按照添加时间排列
                # 先按分类组织条件
                categorized_items = {}
                for cat in categories:
                    categorized_items[cat["name"]] = []
                for it in items:
                    if it["category"] in categorized_items:
                        categorized_items[it["category"]].append(it)
                
                # 按分类顺序显示
                for cat in categories:
                    cat_color = cat.get("color", "#f7aa7a")
                    for it in categorized_items[cat["name"]]:
                        prefix = ""
                        if not is_stage:
                            prefix = "☑ " if cond_vars[it["name"]].get() else "☐ "
                            prefix += "[排除] " if exclude_vars[it["name"]].get() else ""
                        display_text = f"[{it['category']}] {prefix}{it['name']}"
                        listbox.insert(tk.END, display_text)
                        listbox.itemconfig(tk.END, fg=cat_color)
            else:
                cat_name = cat_var.get()
                for it in items:
                    if it["category"] == cat_name:
                        prefix = ""
                        if not is_stage:
                            prefix = "☑ " if cond_vars[it["name"]].get() else "☐ "
                            prefix += "[排除] " if exclude_vars[it["name"]].get() else ""
                        listbox.insert(tk.END, prefix+it["name"])

        listbox = DragListbox(list_frame, pool_data=items, is_stage=is_stage, cat_var=cat_var, categories=categories, refresh_func=refresh, yscrollcommand=scrollbar.set, font=("微软雅黑",11), selectmode=tk.SINGLE)
        listbox.pack(fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        cat_box.bind("<<ComboboxSelected>>", lambda e: refresh())
        refresh()

        bottom = ttk.Frame(frame)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="新增", command=lambda:self.add_item(items, categories, refresh, is_stage, cat_var)).pack(side="left")
        ttk.Button(bottom, text="编辑", command=lambda:self.edit_item(items, listbox, refresh, is_stage)).pack(side="left")
        ttk.Button(bottom, text="删除", command=lambda:self.delete_selected(items, listbox, refresh, is_stage)).pack(side="left")
        ttk.Button(bottom, text="改变分类", command=lambda:self.change_item_category(items, listbox, categories, refresh, is_stage)).pack(side="left")
        
        # 动态按键：锁定/解锁
        lock_btn = ttk.Button(bottom, text="锁定", command=lambda:self.toggle_lock(items, listbox, is_stage, refresh))
        lock_btn.pack(side="left")
        
        # 动态按键：排除/解除排除
        exclude_btn = ttk.Button(bottom, text="排除", command=lambda:self.toggle_exclude(items, listbox, is_stage, refresh))
        exclude_btn.pack(side="left")
        
        # 绑定 listbox 选择事件以更新按键状态（仅条件池需要）
        if not is_stage:
            def update_button_states(event=None):
                selection = listbox.curselection()
                if selection:
                    idx = selection[0]
                    text = listbox.get(idx).strip()
                    # 提取条件名称
                    item_name = text.replace("☑ ", "").replace("☐ ", "").replace("[排除] ", "")
                    if "[" in item_name and "]" in item_name:
                        item_name = item_name[:item_name.rfind("[")].strip()
                    
                    # 检查锁定状态
                    is_locked = cond_vars.get(item_name, tk.BooleanVar(value=False)).get() if item_name in cond_vars else False
                    lock_btn.config(text="解除锁定" if is_locked else "锁定")
                    
                    # 检查排除状态
                    is_excluded = exclude_vars.get(item_name, tk.BooleanVar(value=False)).get() if item_name in exclude_vars else False
                    exclude_btn.config(text="解除排除" if is_excluded else "排除")
                else:
                    lock_btn.config(text="锁定")
                    exclude_btn.config(text="排除")
            
            # 绑定选择事件
            listbox.bind("<<ListboxSelect>>", update_button_states)
        
        return frame

    # ===============================
    # 分类管理
    # ===============================
    def add_category(self, categories, cat_box, items):
        name = simpledialog.askstring("新增分类","分类名称：")
        if name and all(cat["name"]!=name for cat in categories):
            # 新建分类时，询问最少/最多数量限制（仅条件分类适用）
            is_condition = cat_box.get() == "全部" and any(c["name"] in ["干员类","时间类"] for c in categories)
            min_count = 0
            max_count = 10
            
            if is_condition:
                try:
                    min_str = simpledialog.askstring("设置数量限制", "最少可出现数量（默认0）:", initialvalue="0")
                    if min_str is not None:
                        min_count = max(0, int(min_str))
                except (ValueError, TypeError):
                    min_count = 0
                
                try:
                    max_str = simpledialog.askstring("设置数量限制", "最多可出现数量（默认10）:", initialvalue="10")
                    if max_str is not None:
                        max_count = max(1, int(max_str))
                except (ValueError, TypeError):
                    max_count = 10
            
            cat_dict = {"name":name,"color":"#7aa2f7","folded":False,"excluded":False}
            if is_condition:
                cat_dict["min_count"] = min_count
                cat_dict["max_count"] = max_count
            categories.append(cat_dict)
            cat_box["values"] = ["全部"]+[cat["name"] for cat in categories]
            save_data(self.data)

    def edit_category(self, categories, cat_box, items):
        old = cat_box.get()
        if old=="全部": return
        # 允许重命名、更改颜色以及数量限制
        new_name = simpledialog.askstring("重命名分类","新名称：",initialvalue=old)
        if new_name is None:
            return
        # 检查名称唯一性（允许与自身相同）
        if new_name != old and any(cat["name"]==new_name for cat in categories):
            messagebox.showwarning("警告","分类名已存在")
            return
        # 获取当前颜色作为初始颜色和数量限制
        current_color = None
        current_min = 0
        current_max = 10
        for cat in categories:
            if cat["name"]==old:
                current_color = cat.get("color", "#7aa2f7")
                current_min = cat.get("min_count", 0)
                current_max = cat.get("max_count", 10)
                break
        color = colorchooser.askcolor(title="选择分类颜色", initialcolor=current_color)[1]
        
        # 询问最少/最多数量限制（仅条件分类）
        is_condition = any(cat.get("min_count") is not None for cat in categories)
        min_count = current_min
        max_count = current_max
        
        if is_condition:
            try:
                min_str = simpledialog.askstring("设置数量限制", "最少可出现数量：", initialvalue=str(current_min))
                if min_str is not None:
                    min_count = max(0, int(min_str))
            except (ValueError, TypeError):
                min_count = current_min
            
            try:
                max_str = simpledialog.askstring("设置数量限制", "最多可出现数量：", initialvalue=str(current_max))
                if max_str is not None:
                    max_count = max(1, int(max_str))
            except (ValueError, TypeError):
                max_count = current_max
        
        # 更新分类信息
        for cat in categories:
            if cat["name"]==old:
                cat["name"] = new_name
                if color:
                    cat["color"] = color
                if is_condition:
                    cat["min_count"] = min_count
                    cat["max_count"] = max_count
        # 更新条目所属分类名称
        for it in items:
            if it["category"]==old:
                it["category"]=new_name
        cat_box["values"] = ["全部"]+[cat["name"] for cat in categories]
        save_data(self.data)
        cat_box.set(new_name)
        # 刷新整个界面以应用颜色变化
        self.refresh_all()

    def delete_category(self, categories, cat_box, items):
        old = cat_box.get()
        if old=="全部": return
        if len(categories)<=1:
            messagebox.showwarning("警告","至少保留一个分类")
            return
        if messagebox.askyesno("删除分类",f"删除分类「{old}」？该分类下条目将转移到第一个分类"):
            target = categories[0]["name"]
            categories[:] = [cat for cat in categories if cat["name"]!=old]
            for it in items:
                if it["category"]==old: it["category"]=target
            cat_box["values"] = ["全部"]+[cat["name"] for cat in categories]
            cat_box.set(target)
            save_data(self.data)

    # ===============================
    # 条目管理
    # ===============================
    def add_item(self, items, categories, refresh, is_stage=True, cat_var=None):
        name = simpledialog.askstring("新增","名称：")
        if not name: return
        color = colorchooser.askcolor()[1] or "#ffffff"
        if cat_var:
            selected_cat = cat_var.get()
            if selected_cat=="全部":
                selected_cat = categories[0]["name"]
        else:
            selected_cat = categories[0]["name"]
        items.append({"name":name,"category":selected_cat,"color":color,"locked":False,"excluded":False})
        if not is_stage:
            self.cond_vars[name] = tk.BooleanVar(value=False)
            self.cond_exclude[name] = tk.BooleanVar(value=False)
        save_data(self.data)
        refresh()
        if is_stage:
            self.update_lock_stage_options()

    def edit_item(self, items, listbox, refresh, is_stage=True):
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("警告","请先选择一个项目")
            return
        idx = selection[0]
        name = listbox.get(idx).strip()
        # 提取条目名称（去掉前缀和分类信息）
        if name.startswith("☑") or name.startswith("☐"):
            name = name.replace("☑ ", "").replace("☐ ", "")
        if "[排除]" in name:
            name = name.replace("[排除] ", "")
        # 去掉分类信息 [...]
        if "[" in name and "]" in name:
            name = name[:name.rfind("[")].strip()
        
        new_name = simpledialog.askstring("编辑","请输入新名称",initialvalue=name)
        if not new_name: return
        for it in items:
            if it["name"]==name:
                it["name"]=new_name
        if not is_stage:
            self.cond_vars[new_name] = self.cond_vars.pop(name)
            self.cond_exclude[new_name] = self.cond_exclude.pop(name)
        save_data(self.data)
        refresh()
        if is_stage:
            self.update_lock_stage_options()

    def delete_selected(self, items, listbox, refresh, is_stage=True):
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("警告","请先选择一个项目")
            return
        names_to_delete = []
        for idx in selection:
            name = listbox.get(idx).strip()
            # 提取条目名称（去掉前缀和分类信息）
            if name.startswith("☑") or name.startswith("☐"):
                name = name.replace("☑ ", "").replace("☐ ", "")
            if "[排除]" in name:
                name = name.replace("[排除] ", "")
            # 去掉分类信息 [...]
            if "[" in name and "]" in name:
                name = name[:name.rfind("[")].strip()
            if name:
                names_to_delete.append(name)
        if not names_to_delete: return
        items[:] = [it for it in items if it["name"] not in names_to_delete]
        if not is_stage:
            for n in names_to_delete:
                self.cond_vars.pop(n,None)
                self.cond_exclude.pop(n,None)
        save_data(self.data)
        refresh()
        if is_stage:
            self.update_lock_stage_options()

    def toggle_lock(self, items, listbox, is_stage=True, refresh=None):
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("警告","请先选择一个项目")
            return
        if is_stage: return
        for idx in selection:
            name = listbox.get(idx).strip()
            # 提取条目名称（去掉前缀和分类信息）
            if name.startswith("☑") or name.startswith("☐"):
                name = name.replace("☑ ", "").replace("☐ ", "")
            if "[排除]" in name:
                name = name.replace("[排除] ", "")
            # 去掉分类信息 [...]
            if "[" in name and "]" in name:
                name = name[:name.rfind("[")].strip()
            
            if name in self.cond_vars:
                self.cond_vars[name].set(not self.cond_vars[name].get())
                for it in items:
                    if it["name"]==name:
                        it["locked"]=self.cond_vars[name].get()
        save_data(self.data)
        # 如果提供了 refresh 函数，调用它刷新显示；否则全局刷新
        if refresh:
            refresh()
        else:
            self.refresh_all()

    def toggle_exclude(self, items, listbox, is_stage=True, refresh=None):
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("警告","请先选择一个项目")
            return
        for idx in selection:
            name = listbox.get(idx).strip()
            if not is_stage:
                # 提取条目名称（去掉前缀和分类信息）
                if name.startswith("☑") or name.startswith("☐"):
                    name = name.replace("☑ ", "").replace("☐ ", "")
                if "[排除]" in name:
                    name = name.replace("[排除] ", "")
                # 去掉分类信息 [...]
                if "[" in name and "]" in name:
                    name = name[:name.rfind("[")].strip()
                
                if name in self.cond_exclude:
                    self.cond_exclude[name].set(not self.cond_exclude[name].get())
                    for it in items:
                        if it["name"]==name:
                            it["excluded"]=self.cond_exclude[name].get()
            else:
                # 对分类进行排除
                for cat in self.data["stage_categories"]:
                    if cat["name"]==name.strip("[]+- "):
                        cat["excluded"]=not cat.get("excluded",False)
        save_data(self.data)
        if refresh:
            refresh()
        else:
            self.refresh_all()

    def change_item_category(self, items, listbox, categories, refresh, is_stage=True):
        """改变选中条目的分类"""
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("警告","请先选择一个项目")
            return
        
        # 获取选中的条目名称
        selected_names = []
        for idx in selection:
            text = listbox.get(idx).strip()
            # 提取条目名称（去掉前缀和分类信息）
            if text.startswith("☑") or text.startswith("☐"):
                text = text.replace("☑ ", "").replace("☐ ", "")
            if "[排除]" in text:
                text = text.replace("[排除] ", "")
            # 去掉分类信息 [...]
            if "[" in text and "]" in text:
                text = text[:text.rfind("[")].strip()
            selected_names.append(text)
        
        if not selected_names: return
        
        # 弹出分类选择对话框
        cat_names = [cat["name"] for cat in categories]
        if not cat_names: return
        
        # 创建一个简单的选择窗口
        new_cat = simpledialog.askstring("改变分类", 
                                         f"请选择新分类:\n" + "\n".join(f"{i+1}. {c}" for i, c in enumerate(cat_names)),
                                         initialvalue=cat_names[0])
        
        if not new_cat or new_cat not in cat_names: 
            return
        
        # 更新所有选中条目的分类
        for item_name in selected_names:
            for it in items:
                if it["name"] == item_name:
                    it["category"] = new_cat
                    break
        
        save_data(self.data)
        refresh()
        if is_stage:
            self.update_lock_stage_options()

    # ===============================
    # 随机抽取区（时间类限制为最多一条）
    # ===============================
    def build_result(self):
        # 清空右侧区域
        for widget in self.right.winfo_children():
            widget.destroy()

        frame = ttk.LabelFrame(self.right,text="随机结果")
        frame.pack(fill="both",expand=True,padx=6,pady=6)

        self.lock_stage_var = tk.StringVar(value="不启用")
        ttk.Label(frame,text="锁定关卡:").pack(anchor="w")
        
        # 按照分类顺序组织关卡，确保顺序与关卡池一致
        categorized_stages = {}
        for cat in self.data["stage_categories"]:
            categorized_stages[cat["name"]] = []
        for stage in self.data["stages"]:
            if stage["category"] in categorized_stages:
                categorized_stages[stage["category"]].append(stage)
        
        # 按分类顺序排列关卡
        sorted_stages = []
        for cat in self.data["stage_categories"]:
            sorted_stages.extend(categorized_stages[cat["name"]])
        
        # 在下拉中加入"不启用"选项并默认选中
        self.lock_stage_cb = ttk.Combobox(frame,textvariable=self.lock_stage_var,
                                          values=["不启用"] + [s["name"] for s in sorted_stages],state="readonly")
        self.lock_stage_cb.pack(fill="x")

        # 时间类条件开关
        self.enable_time_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="启用时间类条件", variable=self.enable_time_var, command=self.update_condition_hint).pack(anchor="w")

        # 条件数量选择区域
        num_frame = ttk.Frame(frame)
        num_frame.pack(anchor="w")
        ttk.Label(num_frame, text="选择条件数量:").pack(side="left")
        self.num_var = tk.IntVar(value=2)
        ttk.Spinbox(num_frame, from_=1, to=10, textvariable=self.num_var, width=5).pack(side="left", padx=5)
        # 条件提示标签（动态更新）
        self.hint_label = ttk.Label(num_frame, text="", foreground="gray")
        self.hint_label.pack(side="left")
        
        # 初始化提示
        self.update_condition_hint()

        self.stage_label = ttk.Label(frame,text="关卡：-",font=("微软雅黑",18))
        self.stage_label.pack(pady=10)
        self.cond_text = tk.Text(frame,height=10,font=("微软雅黑",14), state=tk.DISABLED)
        self.cond_text.pack(fill="both",expand=True)
        
        # 按钮框架
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame,text="🎲 一键随机",command=self.random_pick).pack(side="left", padx=5)
        
        # 底部框架：左边版本信息，右边水印
        bottom_frame = ttk.Frame(frame)
        bottom_frame.pack(fill="x", padx=5, pady=5)
        
        # 左侧版本信息
        version_info = ttk.Label(bottom_frame, text="温馨提示：当前版本为测试版，请以正式版为准\n版本号：1.0.0 Pre", 
                                 foreground="gray", font=("微软雅黑", 8), justify="left")
        version_info.pack(side="left", anchor="sw")
        
        # 右侧水印
        ttk.Label(bottom_frame, text="Developed By @XingChen-星晨伴月", foreground="gray", font=("微软雅黑", 9)).pack(side="right", anchor="se")

    def update_condition_hint(self):
        """更新条件数量的提示文本"""
        if self.enable_time_var.get():
            self.hint_label.config(text="（时间类条件不计入随机条件数）")
        else:
            self.hint_label.config(text="")

    def update_lock_stage_options(self):
        """更新锁定关卡下拉框的选项，按照关卡池中的排序（主线-Side Story-集成战略）"""
        if hasattr(self, 'lock_stage_cb'):
            current_value = self.lock_stage_var.get()
            
            # 按照分类顺序组织关卡，确保顺序与关卡池一致
            categorized_stages = {}
            for cat in self.data["stage_categories"]:
                categorized_stages[cat["name"]] = []
            for stage in self.data["stages"]:
                if stage["category"] in categorized_stages:
                    categorized_stages[stage["category"]].append(stage)
            
            # 按分类顺序排列关卡
            sorted_stages = []
            for cat in self.data["stage_categories"]:
                sorted_stages.extend(categorized_stages[cat["name"]])
            
            new_values = ["不启用"] + [s["name"] for s in sorted_stages]
            self.lock_stage_cb["values"] = new_values
            # 如果当前选中的关卡不存在（或被删除），设为“不启用”
            if current_value not in new_values:
                self.lock_stage_var.set("不启用")

    def random_pick(self):
        # 获取未排除的关卡和条件
        stages = [s for s in self.data["stages"] if not s.get("excluded",False)]
        conditions = [c for c in self.data["conditions"] if not c.get("excluded",False)]

        # 随机或锁定关卡
        lock_stage = self.lock_stage_var.get()
        # 将“不启用”视为未锁定
        if lock_stage and lock_stage != "不启用":
            stage = next((s for s in stages if s["name"]==lock_stage), random.choice(stages))
        else:
            stage = random.choice(stages)
        self.stage_label.config(text=f"关卡：{stage['name']}")

        self.cond_text.config(state=tk.NORMAL)
        self.cond_text.delete("1.0",tk.END)
        num = self.num_var.get()

        # 先加入锁定条件
        locked = [c for c in conditions if self.cond_vars[c["name"]].get()]
        
        picks = list(locked)

        # 检查是否启用时间类条件
        if self.enable_time_var.get():
            # 时间类条件处理（启用时）
            time_conditions = [c for c in conditions if c["category"]=="时间类"]
            locked_time = [c for c in locked if c["category"]=="时间类"]
            remaining_conditions = [c for c in conditions if c not in locked]

            # 时间类随机抽取1条（如果锁定中没有时间类）
            if not locked_time:
                remaining_time = [c for c in remaining_conditions if c["category"]=="时间类"]
                if remaining_time:
                    picks.append(random.choice(remaining_time))
                    remaining_conditions = [c for c in remaining_conditions if c["category"]!="时间类"]

            # 其他条件随机补足数量（应用分类数量限制）
            num_needed = num - len([c for c in picks if c["category"]!="时间类"])
            remaining_other = [c for c in remaining_conditions if c["category"]!="时间类"]
            
            # 应用分类数量约束
            if num_needed > 0:
                picked_counts = {}
                for c in picks:
                    cat_name = c["category"]
                    picked_counts[cat_name] = picked_counts.get(cat_name, 0) + 1
                
                # 筛选可以继续添加的条件（未超过该分类的最多数量）
                available = []
                for c in remaining_other:
                    cat = next((cat for cat in self.data["condition_categories"] if cat["name"]==c["category"]), None)
                    max_count = cat.get("max_count", 10) if cat else 10
                    current_count = picked_counts.get(c["category"], 0)
                    if current_count < max_count:
                        available.append(c)
                
                picks += random.sample(available, min(num_needed, len(available)))
        else:
            # 禁用时间类条件（不抽取时间类条件）
            remaining_conditions = [c for c in conditions if c not in locked and c["category"]!="时间类"]
            num_needed = num - len(picks)
            
            # 应用分类数量约束
            if num_needed > 0:
                picked_counts = {}
                for c in picks:
                    cat_name = c["category"]
                    picked_counts[cat_name] = picked_counts.get(cat_name, 0) + 1
                
                # 筛选可以继续添加的条件（未超过该分类的最多数量）
                available = []
                for c in remaining_conditions:
                    cat = next((cat for cat in self.data["condition_categories"] if cat["name"]==c["category"]), None)
                    max_count = cat.get("max_count", 10) if cat else 10
                    current_count = picked_counts.get(c["category"], 0)
                    if current_count < max_count:
                        available.append(c)
                
                picks += random.sample(available, min(num_needed, len(available)))

        # 输出
        for i,c in enumerate(picks,1):
            self.cond_text.insert(tk.END,f"{i}. {c['name']}\n")
        self.cond_text.config(state=tk.DISABLED)

    def export_data_action(self):
        """导出数据的UI操作"""
        # 导出当前页，仅保存当前配置数据，文件名使用当前页标题（若存在）
        suggested = None
        if getattr(self, 'page_titles', None) and len(self.page_titles) > self.current_page:
            suggested = self.page_titles[self.current_page]
        export_data(self.data, suggested_name=suggested)

    def import_data_action(self):
        """导入 JSON 配置并覆盖当前数据（会询问确认）"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if not file_path:
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
        except Exception as e:
            messagebox.showerror("导入失败", f"无法读取文件：{str(e)}")
            return False

        is_valid, msg = validate_json_format(loaded)
        if not is_valid:
            messagebox.showerror("导入失败", f"文件格式非法：{msg}")
            return False

        # 询问导入方式：覆盖当前页(是) 或 新建配置页(否)
        choice = messagebox.askyesno("导入方式", "选择导入方式：\n是：覆盖当前页；否：新建配置页并导入")
        try:
            if choice:
                # 覆盖当前页并写入主数据文件以保持兼容
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(loaded, f, ensure_ascii=False, indent=2)
                # 重新加载并应用
                self.data = load_data()
                # 如果只有一个页面，更新该页内容；否则也同步当前页面
                if len(self.pages) == 1:
                    self.pages[0] = deepcopy(self.data)
                else:
                    self.pages[self.current_page] = deepcopy(self.data)
                self.refresh_all()
                messagebox.showinfo("导入成功", f"已覆盖当前页并从 {file_path} 导入配置")
                return True
            else:
                # 新建一页并加入（不改变磁盘上的主数据文件）
                self.pages.append(deepcopy(loaded))
                self.current_page = len(self.pages) - 1
                # 页面标题，使用文件名作为默认标题
                title = os.path.splitext(os.path.basename(file_path))[0] or f"配置{self.current_page+1}"
                if not hasattr(self, 'page_titles'):
                    self.page_titles = [f"配置{i+1}" for i in range(len(self.pages)-1)]
                self.page_titles.append(title)
                self.data = self.pages[self.current_page]
                self.refresh_all()
                messagebox.showinfo("导入成功", f"已新建配置页并从 {file_path} 导入配置 (当前页 {self.current_page+1}/{len(self.pages)})")
                self.update_title()
                return True
        except Exception as e:
            messagebox.showerror("导入失败", f"导入过程发生错误：{str(e)}")
            return False

    def refresh_all(self):
        for widget in self.left.winfo_children():
            widget.destroy()
        self.stage_frame = self.build_pool("关卡池",self.data["stage_categories"],self.data["stages"],True)
        self.cond_frame = self.build_pool("条件池",self.data["condition_categories"],self.data["conditions"],False)
        # 重新添加时保留最小高度，避免某一面板被压缩覆盖
        self.left.add(self.stage_frame, minsize=260)
        self.left.add(self.cond_frame, minsize=260)
        # 确保左侧两个面板的相对初始大小合理
        try:
            # 将 sash 移动到大约左侧高度的一半位置
            total_h = self.left.winfo_height() or 600
            self.left.sash_place(0, 0, int(total_h * 0.5))
        except Exception:
            pass
        self.build_result()

    # 分页相关方法
    def create_new_page(self, copy_current=False):
        if copy_current:
            new_page = deepcopy(self.data)
        else:
            # 新建空页，保留分类信息
            new_page = {
                "stage_categories": deepcopy(self.data.get("stage_categories", [])),
                "condition_categories": deepcopy(self.data.get("condition_categories", [])),
                "stages": [],
                "conditions": []
            }
        self.pages.append(new_page)
        self.current_page = len(self.pages) - 1
        self.data = self.pages[self.current_page]
        # 页面标题管理
        if not hasattr(self, 'page_titles'):
            self.page_titles = [f"配置{i+1}" for i in range(len(self.pages)-1)]
        # 新建页名：复制则在原名后加-copy，否则默认命名
        if copy_current and hasattr(self, 'page_titles'):
            new_title = f"{self.page_titles[self.current_page-1]}-copy"
        else:
            new_title = f"配置{self.current_page+1}"
        self.page_titles.append(new_title)
        self.refresh_all()
        messagebox.showinfo("新建配置页", f"已创建第 {self.current_page+1} 页，共 {len(self.pages)} 页")

    def rename_current_page(self):
        """为当前配置页命名"""
        current_title = self.page_titles[self.current_page] if hasattr(self, 'page_titles') and len(self.page_titles)>self.current_page else f"配置{self.current_page+1}"
        new_title = simpledialog.askstring("重命名配置页", "请输入新名称：", initialvalue=current_title)
        if new_title:
            # 确保 page_titles 长度同步
            if not hasattr(self, 'page_titles'):
                self.page_titles = [f"配置{i+1}" for i in range(len(self.pages))]
            self.page_titles[self.current_page] = new_title
            self.update_title()

    def clear_current_page(self):
        """清空当前配置页的关卡与条件，但保留分类信息和页面本身"""
        if messagebox.askyesno("清空配置页", "确定要清空当前配置页的所有关卡与条件吗？此操作不可撤销。"):
            pg = self.pages[self.current_page]
            pg['stages'] = []
            pg['conditions'] = []
            # 如果当前页就是正在编辑的 self.data，也同步
            self.data = self.pages[self.current_page]
            self.refresh_all()
            messagebox.showinfo("已清空", "当前配置页已被清空（保留分类）。")

    def delete_current_page(self):
        """删除当前配置页，但至少保留一页"""
        if len(self.pages) <= 1:
            messagebox.showwarning("无法删除", "至少保留一个配置页，无法删除最后一页。")
            return
        if not messagebox.askyesno("删除配置页", f"确定要删除当前配置页 “{self.page_titles[self.current_page] if hasattr(self,'page_titles') else self.current_page+1}” 吗？"):
            return
        # 执行删除
        del self.pages[self.current_page]
        if hasattr(self, 'page_titles') and len(self.page_titles) > self.current_page:
            del self.page_titles[self.current_page]
        # 调整当前页索引
        if self.current_page >= len(self.pages):
            self.current_page = len(self.pages) - 1
        self.data = self.pages[self.current_page]
        self.refresh_all()
        self.update_title()
        messagebox.showinfo("已删除", f"已删除配置页，当前页为 {self.current_page+1}/{len(self.pages)}")

    def prev_page(self):
        if not getattr(self, 'paging_enabled', tk.BooleanVar()).get():
            messagebox.showinfo("分页未启用", "请先在“文件”菜单中启用分页功能")
            return
        if self.current_page > 0:
            self.current_page -= 1
            self.data = self.pages[self.current_page]
            self.refresh_all()
            self.update_title()
        else:
            messagebox.showinfo("第一页", "已经是第一页")

    def next_page(self):
        if not getattr(self, 'paging_enabled', tk.BooleanVar()).get():
            messagebox.showinfo("分页未启用", "请先在“文件”菜单中启用分页功能")
            return
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.data = self.pages[self.current_page]
            self.refresh_all()
            self.update_title()
        else:
            messagebox.showinfo("最后一页", "已经是最后一页")

    def update_paging_state(self):
        # 切换分页功能
        self.update_title()

    def update_title(self):
        base = "明日方舟随机挑战条件生成器 Arknights Random Challenge Condition Selector"
        if getattr(self, 'paging_enabled', tk.BooleanVar()).get():
            title = self.page_titles[self.current_page] if hasattr(self, 'page_titles') and len(self.page_titles)>self.current_page else f"配置{self.current_page+1}"
            self.root.title(f"{base} - {title} ({self.current_page+1}/{len(self.pages)})")
        else:
            self.root.title(base)

    def show_about(self):
        """显示开发者说明弹窗，内容居中且窗口自适应内容大小"""
        win = tk.Toplevel(self.root)
        win.title("说明")
        win.transient(self.root)
        win.resizable(False, False)

        # 内容容器，确保居中
        container = ttk.Frame(win)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        # 使用Label显示文本，居中显示并自动换行
        lbl = ttk.Label(container, text=DEVELOPER_INFO, justify="center", anchor="center")
        lbl.pack(expand=True)

        # 根据内容调整窗口大小（限制最大宽度）
        win.update_idletasks()
        screen_w = win.winfo_screenwidth()
        max_w = min(900, screen_w - 100)
        req_w = lbl.winfo_reqwidth() + 24
        req_h = lbl.winfo_reqheight() + 24
        w = min(req_w, max_w)
        h = req_h
        # 如果内容较宽，设置 wraplength 并重新计算高度
        if req_w > max_w:
            lbl.config(wraplength=max_w - 24)
            win.update_idletasks()
            h = lbl.winfo_reqheight() + 24
            w = max_w

        # 让窗口相对于主窗口居中显示
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_w = self.root.winfo_width() or 800
        root_h = self.root.winfo_height() or 600
        x = root_x + max(0, int((root_w - w) / 2))
        y = root_y + max(0, int((root_h - h) / 2))
        win.geometry(f"{w}x{h}+{x}+{y}")

        # 关闭按钮
        ttk.Button(container, text="关闭", command=win.destroy).pack(pady=(8,0))

# ===============================
# 运行程序
# ===============================
if __name__=="__main__":
    root = tk.Tk()
    app = ToolApp(root)
    root.mainloop()
