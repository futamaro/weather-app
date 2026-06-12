import os
import json
import threading
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

# ==============================================================================
# 設定與資料管理
# ==============================================================================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weather_config.json")

DEFAULT_CONFIG = {
    "api_key": "",
    "temp_unit": "C",  # 'C' 代表攝氏, 'F' 代表華氏
    "favorites": ["台北", "東京", "紐約", "倫敦"]
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        try:
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        except Exception:
            return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            for key, val in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = val
            return config
    except Exception:
        return DEFAULT_CONFIG

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"無法儲存設定檔: {e}")

# ==============================================================================
# 數據獲取引擎 (支援 Mock 與真實 API 雙模式)
# ==============================================================================
WEATHER_TYPES = {
    "sunny": {"emoji": "☀️", "desc": "晴朗", "color": "#FF8C00"},
    "cloudy": {"emoji": "☁️", "desc": "多雲", "color": "#7F8C8D"},
    "rainy": {"emoji": "🌧️", "desc": "陣雨", "color": "#3498DB"},
    "snowy": {"emoji": "❄️", "desc": "降雪", "color": "#9B59B6"},
    "stormy": {"emoji": "⚡", "desc": "雷陣雨", "color": "#E74C3C"},
    "misty": {"emoji": "🌫️", "desc": "有霧", "color": "#95A5A6"}
}

def get_mock_weather_data(city, unit="C"):
    city_clean = city.strip().lower()
    today_str = datetime.now().strftime("%Y-%m-%d")
    seed_base = sum(ord(c) for c in city_clean) + sum(ord(c) for c in today_str)
    
    preset_cities = {
        "台北": {"temp": 28, "type": "sunny", "humidity": 75, "wind": 3.2},
        "taipei": {"temp": 28, "type": "sunny", "humidity": 75, "wind": 3.2},
        "東京": {"temp": 18, "type": "cloudy", "humidity": 65, "wind": 4.1},
        "tokyo": {"temp": 18, "type": "cloudy", "humidity": 65, "wind": 4.1},
        "紐約": {"temp": 22, "type": "rainy", "humidity": 85, "wind": 5.5},
        "new york": {"temp": 22, "type": "rainy", "humidity": 85, "wind": 5.5},
        "倫敦": {"temp": 14, "type": "misty", "humidity": 90, "wind": 6.2},
        "london": {"temp": 14, "type": "misty", "humidity": 90, "wind": 6.2}
    }
    
    if city_clean in preset_cities:
        base = preset_cities[city_clean]
        base_temp = base["temp"]
        w_type = base["type"]
        base_humidity = base["humidity"]
        base_wind = base["wind"]
    else:
        base_temp = 12 + (seed_base % 22)
        w_types = list(WEATHER_TYPES.keys())
        w_type = w_types[seed_base % len(w_types)]
        base_humidity = 40 + (seed_base % 51)
        base_wind = 1.0 + (seed_base % 10) * 0.8
    
    hour_factor = datetime.now().hour
    temp_offset = ((seed_base + hour_factor) % 5) - 2
    current_temp = base_temp + temp_offset
    
    if unit == "F":
        current_temp = (current_temp * 9/5) + 32
        
    weather_info = WEATHER_TYPES[w_type]
    
    current_data = {
        "city": city,
        "temp": round(current_temp, 1),
        "desc": weather_info["desc"],
        "emoji": weather_info["emoji"],
        "type": w_type,
        "humidity": base_humidity,
        "wind_speed": round(base_wind, 1),
        "is_mock": True,
        "update_time": datetime.now().strftime("%H:%M:%S")
    }
    
    forecast_data = []
    w_types_list = list(WEATHER_TYPES.keys())
    for i in range(1, 4):
        day_seed = seed_base + i * 17
        forecast_date = (datetime.now() + timedelta(days=i)).strftime("%m/%d")
        day_temp_base = base_temp + ((day_seed % 7) - 3)
        temp_min = day_temp_base - 3
        temp_max = day_temp_base + 4
        
        if unit == "F":
            temp_min = (temp_min * 9/5) + 32
            temp_max = (temp_max * 9/5) + 32
            
        day_type = w_types_list[day_seed % len(w_types_list)]
        forecast_data.append({
            "date": forecast_date,
            "weekday": get_weekday_chinese((datetime.now() + timedelta(days=i)).weekday()),
            "temp_min": round(temp_min, 1),
            "temp_max": round(temp_max, 1),
            "desc": WEATHER_TYPES[day_type]["desc"],
            "emoji": WEATHER_TYPES[day_type]["emoji"]
        })
        
    return current_data, forecast_data

def get_weekday_chinese(weekday_idx):
    days = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    return days[weekday_idx] if 0 <= weekday_idx < 7 else ""

def get_real_weather_data(city, api_key, unit="C"):
    try:
        units_param = "metric" if unit == "C" else "imperial"
        city_encoded = urllib.parse.quote(city.strip())
        
        current_url = f"https://api.openweathermap.org/data/2.5/weather?q={city_encoded}&appid={api_key}&units={units_param}&lang=zh_tw"
        req = urllib.request.Request(current_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            current_raw = json.loads(response.read().decode('utf-8'))
            
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city_encoded}&appid={api_key}&units={units_param}&lang=zh_tw"
        req_fore = urllib.request.Request(forecast_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_fore, timeout=8) as response:
            forecast_raw = json.loads(response.read().decode('utf-8'))
            
        weather_id = current_raw["weather"][0]["id"]
        w_type = parse_weather_type_by_id(weather_id)
        
        current_data = {
            "city": current_raw["name"],
            "temp": round(current_raw["main"]["temp"], 1),
            "desc": current_raw["weather"][0]["description"],
            "emoji": WEATHER_TYPES[w_type]["emoji"],
            "type": w_type,
            "humidity": current_raw["main"]["humidity"],
            "wind_speed": round(current_raw["wind"]["speed"], 1),
            "is_mock": False,
            "update_time": datetime.now().strftime("%H:%M:%S")
        }
        
        forecast_list = forecast_raw.get("list", [])
        daily_groups = {}
        today_str = datetime.now().strftime("%Y-%m-%d")
        for item in forecast_list:
            dt_txt = item.get("dt_txt", "")
            if not dt_txt: continue
            date_part = dt_txt.split(" ")[0]
            if date_part == today_str: continue
            if date_part not in daily_groups:
                daily_groups[date_part] = []
            daily_groups[date_part].append(item)
            
        forecast_data = []
        sorted_dates = sorted(list(daily_groups.keys()))[:3]
        
        for date_str in sorted_dates:
            items = daily_groups[date_str]
            temps = [it["main"]["temp"] for it in items]
            temp_min = min(temps)
            temp_max = max(temps)
            
            repr_item = items[len(items) // 2]
            for it in items:
                if "12:00:00" in it.get("dt_txt", ""):
                    repr_item = it
                    break
                    
            w_id = repr_item["weather"][0]["id"]
            d_type = parse_weather_type_by_id(w_id)
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            forecast_data.append({
                "date": dt_obj.strftime("%m/%d"),
                "weekday": get_weekday_chinese(dt_obj.weekday()),
                "temp_min": round(temp_min, 1),
                "temp_max": round(temp_max, 1),
                "desc": repr_item["weather"][0]["description"],
                "emoji": WEATHER_TYPES[d_type]["emoji"]
            })
            
        return current_data, forecast_data
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise Exception("API 金鑰無效或尚未啟用，請至設定檢查。")
        elif e.code == 404:
            raise Exception("找不到該城市，請輸入英文名稱或確認拼字。")
        else:
            raise Exception(f"網路請求失敗，錯誤代碼: {e.code}")
    except Exception as e:
        raise Exception(f"無法取得即時天氣: {str(e)}")

def parse_weather_type_by_id(weather_id):
    if 200 <= weather_id < 300: return "stormy"
    elif 300 <= weather_id < 600: return "rainy"
    elif 600 <= weather_id < 700: return "snowy"
    elif 700 <= weather_id < 800: return "misty"
    elif weather_id == 800: return "sunny"
    else: return "cloudy"

# ==============================================================================
# 生活助手引擎
# ==============================================================================
def generate_life_suggestions(weather_type, temp, humidity, wind_speed, unit="C"):
    temp_c = temp if unit == "C" else (temp - 32) * 5/9
    suggestions = []
    
    # 1. 穿衣指南
    if temp_c < 12:
        suggestions.append(("👕 穿衣指南", "寒流來襲！建議穿著厚重羽絨外套、發熱衣，並配戴圍巾與手套防寒。"))
    elif temp_c < 18:
        suggestions.append(("👕 穿衣指南", "天氣偏冷。建議穿著大衣、毛衣或厚夾克，內搭長袖上衣保暖。"))
    elif temp_c < 24:
        suggestions.append(("👕 穿衣指南", "氣溫舒適宜人。適合穿著針織衫、薄外套或長袖襯衫，採洋蔥式穿法。"))
    elif temp_c < 30:
        suggestions.append(("👕 穿衣指南", "天氣溫暖。建議穿著透氣棉質短袖、短褲或薄長袖防曬。"))
    else:
        suggestions.append(("👕 穿衣指南", "天氣酷熱！請穿著輕便、排汗吸濕的短袖衣物，並盡量待在陰涼處。"))
        
    # 2. 雨具防護
    if weather_type in ["rainy", "stormy"]:
        suggestions.append(("🌂 雨具防護", "外面正在下雨或即將有雷雨。出門務必攜帶雨傘或雨衣，注意行車安全。"))
    elif weather_type == "cloudy" or humidity > 80:
        suggestions.append(("🌂 雨具防護", "天空較為陰暗或濕度偏高，有局部飄雨的可能。建議隨身攜帶折疊傘備用。"))
    else:
        suggestions.append(("🌂 雨具防護", "目前降雨機率低、天氣穩定。出門不需要攜帶雨具，可放心外出行程。"))
        
    # 3. 戶外運動
    if weather_type in ["rainy", "stormy", "snowy"]:
        suggestions.append(("🏃 戶外運動", "天候不佳，道路濕滑。不建議進行戶外慢跑或球類運動，可改在室內健身。"))
    elif weather_type == "misty":
        suggestions.append(("🏃 戶外運動", "戶外能見度較低且可能伴隨霧霾。請避免劇烈運動，外出建議配戴口罩。"))
    elif temp_c > 32:
        suggestions.append(("🏃 戶外運動", "室外氣溫過高，紫外線強烈。請避免在中午陽光暴曬時段進行戶外運動。"))
    elif wind_speed > 8.0:
        suggestions.append(("🏃 戶外運動", "目前風力強勁。戶外進行球類或單車運動會受干擾，請特別注意高空落物。"))
    else:
        suggestions.append(("🏃 戶外運動", "今天天氣非常適合戶外活動！散步、慢跑或騎單車都是絕佳的選擇。"))
        
    # 4. 健康生活
    if weather_type == "sunny" and temp_c > 26:
        suggestions.append(("🧴 健康生活", "陽光與紫外線強烈。外出請記得塗抹防曬乳、配戴墨鏡，並多補充水分。"))
    elif humidity < 45:
        suggestions.append(("🧴 健康生活", "空氣十分乾燥。皮膚容易缺水，請適度使用保濕保養品並多喝水。"))
    elif humidity > 80:
        suggestions.append(("🧴 健康生活", "環境濕氣過重。室內容易孳生黴菌，建議開啟除濕機並保持空氣流通。"))
    else:
        suggestions.append(("🧴 健康生活", "氣候溫和舒適。維持正常作息，室內保持適度通風即可。"))
        
    return suggestions

# ==============================================================================
# UI 主介面類別
# ==============================================================================
class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.title("天氣預報與生活助手")
        self.geometry("980x700")
        self.configure(bg="#F5F7FA")
        self.resizable(True, True)
        self.setup_styles()
        self.create_widgets()
        
        default_city = "台北"
        if self.config["favorites"]:
            default_city = self.config["favorites"][0]
        self.search_city(default_city)
        
    def setup_styles(self):
        self.style = ttk.Style()
        try: self.style.theme_use("clam")
        except Exception: pass
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#3A8DFF", foreground="white", borderwidth=0, focuscolor="none")
        self.style.map("TButton", background=[("active", "#1E70E0"), ("pressed", "#105CB3")])
        self.style.configure("Favorite.TButton", font=("Segoe UI", 10), background="#E2E8F0", foreground="#2C3E50", borderwidth=0)
        self.style.configure("TEntry", fieldbackground="white", bordercolor="#CBD5E1", lightcolor="#CBD5E1", darkcolor="#CBD5E1")
        
    def create_widgets(self):
        # 左側邊欄
        sidebar = tk.Frame(self, bg="#FFFFFF", width=240, bd=0, highlightbackground="#E2E8F0", highlightthickness=1)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        brand_label = tk.Label(sidebar, text="🌦️ 天氣小助手", font=("Segoe UI", 16, "bold"), bg="#FFFFFF", fg="#2C3E50")
        brand_label.pack(anchor="w", padx=20, pady=25)
        
        fav_title = tk.Label(sidebar, text="常用城市清單", font=("Segoe UI", 10, "bold"), bg="#FFFFFF", fg="#94A3B8")
        fav_title.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.favorites_container = tk.Frame(sidebar, bg="#FFFFFF")
        self.favorites_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        self.refresh_favorites_list()
        
        settings_btn = tk.Button(sidebar, text="⚙️ 設定與 API 金鑰", font=("Segoe UI", 10, "bold"), bg="#F1F5F9", fg="#475569", activebackground="#E2E8F0", bd=0, relief=tk.FLAT, pady=10, cursor="hand2", command=self.open_settings_dialog)
        settings_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=20)
        
        # 右側主要內容區
        main_content = tk.Frame(self, bg="#F8FAFC")
        main_content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        top_bar = tk.Frame(main_content, bg="#FFFFFF", height=70, bd=0, highlightbackground="#E2E8F0", highlightthickness=1)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        top_bar.pack_propagate(False)
        
        search_frame = tk.Frame(top_bar, bg="#FFFFFF")
        search_frame.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=15)
        
        self.search_var = tk.StringVar(value="台北")
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=22, font=("Segoe UI", 11))
        self.search_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.search_entry.bind("<Return>", lambda e: self.on_search_click())
        
        search_btn = ttk.Button(search_frame, text="🔍 搜尋", command=self.on_search_click, width=8)
        search_btn.pack(side=tk.LEFT, padx=(8, 0))
        
        self.fav_toggle_btn = tk.Button(search_frame, text="☆ 加入常用", font=("Segoe UI", 10, "bold"), bg="#F1F5F9", fg="#64748B", bd=0, padx=10, cursor="hand2", command=self.toggle_favorite)
        self.fav_toggle_btn.pack(side=tk.LEFT, padx=(8, 0))
        
        self.mode_label = tk.Label(top_bar, text="模擬模式", font=("Segoe UI", 9, "bold"), bg="#FEF3C7", fg="#D97706", padx=8, pady=4)
        self.mode_label.pack(side=tk.RIGHT, padx=20, pady=20)
        
        content_frame = tk.Frame(main_content, bg="#F8FAFC")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)
        content_frame.grid_columnconfigure(0, weight=4)
        content_frame.grid_columnconfigure(1, weight=5)
        content_frame.grid_rowconfigure(0, weight=1)
        
        left_layout = tk.Frame(content_frame, bg="#F8FAFC")
        left_layout.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right_layout = tk.Frame(content_frame, bg="#F8FAFC")
        right_layout.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        
        # --- 左欄內容 ---
        self.weather_card = tk.Frame(left_layout, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        self.weather_card.pack(fill=tk.X, pady=(0, 12))
        
        self.city_label = tk.Label(self.weather_card, text="載入中...", font=("Segoe UI", 20, "bold"), bg="#FFFFFF", fg="#1E293B")
        self.city_label.pack(anchor="w", padx=25, pady=(25, 5))
        self.time_label = tk.Label(self.weather_card, text="今天", font=("Segoe UI", 10), bg="#FFFFFF", fg="#64748B")
        self.time_label.pack(anchor="w", padx=25)
        
        temp_icon_frame = tk.Frame(self.weather_card, bg="#FFFFFF")
        temp_icon_frame.pack(fill=tk.X, padx=25, pady=10)
        self.emoji_label = tk.Label(temp_icon_frame, text="☀️", font=("Segoe UI", 64), bg="#FFFFFF")
        self.emoji_label.pack(side=tk.LEFT)
        self.temp_label = tk.Label(temp_icon_frame, text="--°", font=("Segoe UI", 48, "bold"), bg="#FFFFFF", fg="#0F172A")
        self.temp_label.pack(side=tk.LEFT, padx=(15, 0))
        
        self.desc_label = tk.Label(self.weather_card, text="晴朗", font=("Segoe UI", 15, "bold"), bg="#FFFFFF", fg="#3A8DFF")
        self.desc_label.pack(anchor="w", padx=25, pady=(0, 10))
        
        tk.Frame(self.weather_card, bg="#E2E8F0", height=1).pack(fill=tk.X, padx=25, pady=5)
        details_frame = tk.Frame(self.weather_card, bg="#FFFFFF")
        details_frame.pack(fill=tk.X, padx=25, pady=(10, 15))
        
        self.humidity_lbl = tk.Label(details_frame, text="💧 濕度: --%", font=("Segoe UI", 11), bg="#FFFFFF", fg="#475569")
        self.humidity_lbl.pack(side=tk.LEFT, expand=True, anchor="w")
        self.wind_lbl = tk.Label(details_frame, text="💨 風速: -- m/s", font=("Segoe UI", 11), bg="#FFFFFF", fg="#475569")
        self.wind_lbl.pack(side=tk.LEFT, expand=True, anchor="w")
        
        # 預報卡片
        self.forecast_card = tk.Frame(left_layout, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        self.forecast_card.pack(fill=tk.X, pady=(12, 0))
        tk.Label(self.forecast_card, text="未來 3 天天氣預報", font=("Segoe UI", 11, "bold"), bg="#FFFFFF", fg="#1E293B").pack(anchor="w", padx=20, pady=(15, 10))
        
        self.forecast_items_frame = tk.Frame(self.forecast_card, bg="#FFFFFF")
        self.forecast_items_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        self.forecast_widgets = []
        for i in range(3):
            item_frame = tk.Frame(self.forecast_items_frame, bg="#F8FAFC", highlightbackground="#E2E8F0", highlightthickness=1, pady=10)
            item_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            day_lbl = tk.Label(item_frame, text="--/--", font=("Segoe UI", 9, "bold"), bg="#F8FAFC", fg="#475569")
            day_lbl.pack()
            week_lbl = tk.Label(item_frame, text="--", font=("Segoe UI", 9), bg="#F8FAFC", fg="#64748B")
            week_lbl.pack()
            emoji_lbl = tk.Label(item_frame, text="❓", font=("Segoe UI", 24), bg="#F8FAFC")
            emoji_lbl.pack(pady=2)
            temp_lbl = tk.Label(item_frame, text="--° / --°", font=("Segoe UI", 9, "bold"), bg="#F8FAFC", fg="#0F172A")
            temp_lbl.pack()
            
            self.forecast_widgets.append({"day": day_lbl, "week": week_lbl, "emoji": emoji_lbl, "temp": temp_lbl})
            
        # --- 右欄內容：生活助手建議 ---
        self.tips_card = tk.Frame(right_layout, bg="#FFFFFF", highlightbackground="#E2E8F0", highlightthickness=1)
        self.tips_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(self.tips_card, text="💡 生活助手今日建議 (點擊卡片查看)", font=("Segoe UI", 13, "bold"), bg="#FFFFFF", fg="#1E293B").pack(anchor="w", padx=20, pady=(20, 10))
        
        self.tips_container = tk.Frame(self.tips_card, bg="#FFFFFF")
        self.tips_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

    def refresh_favorites_list(self):
        for child in self.favorites_container.winfo_children(): child.destroy()
        for idx, city in enumerate(self.config["favorites"]):
            btn_frame = tk.Frame(self.favorites_container, bg="#FFFFFF")
            btn_frame.pack(fill=tk.X, pady=4)
            
            city_btn = tk.Button(btn_frame, text=f"📍 {city}", font=("Segoe UI", 10), bg="#F8FAFC", fg="#334155", activebackground="#E2E8F0", bd=0, anchor="w", padx=15, pady=8, cursor="hand2", command=lambda c=city: self.search_city(c))
            city_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            del_btn = tk.Button(btn_frame, text="✕", font=("Segoe UI", 9), bg="#FFFFFF", fg="#94A3B8", activebackground="#F1F5F9", bd=0, padx=8, cursor="hand2", command=lambda c=city: self.remove_favorite(c))
            del_btn.pack(side=tk.RIGHT, fill=tk.Y)
            
    def toggle_favorite(self):
        current_city = self.city_label.cget("text")
        if not current_city or current_city in ["載入中...", "請重新搜尋"]: return
        if current_city in self.config["favorites"]:
            self.remove_favorite(current_city)
        else:
            if len(self.config["favorites"]) >= 8:
                messagebox.showwarning("常用上限", "常用城市清單上限為 8 個。")
                return
            self.config["favorites"].append(current_city)
            save_config(self.config)
            self.refresh_favorites_list()
            self.update_favorite_toggle_btn(current_city)
            
    def remove_favorite(self, city):
        if city in self.config["favorites"]:
            self.config["favorites"].remove(city)
            save_config(self.config)
            self.refresh_favorites_list()
            self.update_favorite_toggle_btn(self.city_label.cget("text"))
            
    def update_favorite_toggle_btn(self, city):
        if city in self.config["favorites"]:
            self.fav_toggle_btn.configure(text="★ 已加常用", fg="#F59E0B", bg="#FEF3C7")
        else:
            self.fav_toggle_btn.configure(text="☆ 加入常用", fg="#64748B", bg="#F1F5F9")
            
    def on_search_click(self):
        city = self.search_var.get().strip()
        if not city:
            messagebox.showwarning("欄位空白", "請輸入城市名稱。")
            return
        self.search_city(city)
        
    def search_city(self, city):
        self.city_label.configure(text="載入中...")
        self.temp_label.configure(text="--°")
        self.desc_label.configure(text="正在連線...")
        self.search_entry.configure(state="disabled")
        
        t = threading.Thread(target=self.bg_fetch_weather, args=(city,))
        t.daemon = True
        t.start()
        
    def bg_fetch_weather(self, city):
        api_key = self.config.get("api_key", "").strip()
        unit = self.config.get("temp_unit", "C")
        try:
            if api_key: current, forecast = get_real_weather_data(city, api_key, unit)
            else: current, forecast = get_mock_weather_data(city, unit)
            self.after(0, self.update_weather_ui, current, forecast)
        except Exception as e:
            self.after(0, self.handle_search_error, str(e))
            
    def update_weather_ui(self, current, forecast):
        self.search_entry.configure(state="normal")
        self.city_label.configure(text=current["city"])
        self.search_var.set(current["city"])
        self.time_label.configure(text=f"今日天氣 (更新時間: {current['update_time']})")
        
        unit_sym = "°C" if self.config.get("temp_unit", "C") == "C" else "°F"
        self.temp_label.configure(text=f"{current['temp']}{unit_sym}")
        self.emoji_label.configure(text=current["emoji"])
        self.desc_label.configure(text=current["desc"])
        self.desc_label.configure(fg=WEATHER_TYPES.get(current["type"], {"color": "#3A8DFF"})["color"])
        
        self.humidity_lbl.configure(text=f"💧 濕度: {current['humidity']}%")
        self.wind_lbl.configure(text=f"💨 風速: {current['wind_speed']} m/s")
        
        if current.get("is_mock", True): self.mode_label.configure(text="模擬數據模式", bg="#FEF3C7", fg="#D97706")
        else: self.mode_label.configure(text="真實氣象模式", bg="#D1FAE5", fg="#059669")
            
        self.update_favorite_toggle_btn(current["city"])
        
        for idx, item in enumerate(forecast):
            if idx < len(self.forecast_widgets):
                w = self.forecast_widgets[idx]
                w["day"].configure(text=item["date"])
                w["week"].configure(text=item["weekday"])
                w["emoji"].configure(text=item["emoji"])
                w["temp"].configure(text=f"{item['temp_min']}° / {item['temp_max']}°")
                
        self.update_life_suggestions(current["type"], current["temp"], current["humidity"], current["wind_speed"])
        
    def handle_search_error(self, error_msg):
        self.search_entry.configure(state="normal")
        self.city_label.configure(text="請重新搜尋")
        self.desc_label.configure(text="讀取失敗", fg="#EF4444")
        messagebox.showerror("查詢錯誤", error_msg)

    def show_custom_popup(self, title, message):
        popup = tk.Toplevel(self)
        popup.title(title)
        popup.geometry("380x200")
        popup.configure(bg="#FFFFFF")
        popup.resizable(False, False)
        popup.transient(self) 
        popup.grab_set()      
        
        x = self.winfo_x() + (self.winfo_width() // 2) - 190
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        popup.geometry(f"+{x}+{y}")
        
        tk.Label(popup, text=title, font=("Segoe UI", 13, "bold"), bg="#FFFFFF", fg="#3A8DFF").pack(pady=(20, 10))
        tk.Label(popup, text=message, font=("Segoe UI", 10), bg="#FFFFFF", fg="#475569", wraplength=320, justify="left").pack(padx=20)
        
        btn = ttk.Button(popup, text="關閉了解", command=popup.destroy)
        btn.pack(side="bottom", pady=20)
        
    def update_life_suggestions(self, weather_type, temp, humidity, wind_speed):
        for child in self.tips_container.winfo_children(): child.destroy()
        
        unit = self.config.get("temp_unit", "C")
        tips = generate_life_suggestions(weather_type, temp, humidity, wind_speed, unit)
            
        for title, content in tips:
            # ⭐ 修正 3：稍微縮小卡片間的 pady，讓沒有 Scrollbar 也能剛剛好放滿 4 張卡片。
            tip_box = tk.Frame(self.tips_container, bg="#F8FAFC", highlightbackground="#E2E8F0", highlightthickness=1, pady=8, padx=15, cursor="hand2")
            tip_box.pack(fill=tk.X, pady=4, padx=2)
            
            title_lbl = tk.Label(tip_box, text=title, font=("Segoe UI", 11, "bold"), bg="#F8FAFC", fg="#1E293B", cursor="hand2")
            title_lbl.pack(anchor="w")
            
            # 因為沒有 scrollbar 吃掉寬度，把 wraplength 加寬到 380 讓排版更好看
            content_lbl = tk.Label(tip_box, text=content, font=("Segoe UI", 10), bg="#F8FAFC", fg="#475569", justify=tk.LEFT, wraplength=380, cursor="hand2")
            content_lbl.pack(anchor="w", pady=(2, 0))

            click_cmd = lambda e, t=title, c=content: self.show_custom_popup(t, c)
            
            tip_box.bind("<Button-1>", click_cmd)
            title_lbl.bind("<Button-1>", click_cmd)
            content_lbl.bind("<Button-1>", click_cmd)

    # ==============================================================================
    # 設定對話框
    # ==============================================================================
    def open_settings_dialog(self):
        settings_win = tk.Toplevel(self)
        settings_win.title("設定")
        settings_win.geometry("480x420")
        settings_win.minsize(450, 390)
        settings_win.resizable(True, True)
        settings_win.configure(bg="#FFFFFF")
        settings_win.transient(self)
        settings_win.grab_set()
        
        btn_frame = tk.Frame(settings_win, bg="#F8FAFC", bd=0, highlightbackground="#E2E8F0", highlightthickness=1)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        save_btn = ttk.Button(btn_frame, text="儲存設定", width=12, command=lambda: self.save_settings_action(settings_win))
        save_btn.pack(side=tk.RIGHT, padx=20, pady=12)
        
        cancel_btn = tk.Button(btn_frame, text="取消", font=("Segoe UI", 10), bg="#E2E8F0", fg="#64748B", bd=0, padx=15, cursor="hand2", command=settings_win.destroy)
        cancel_btn.pack(side=tk.RIGHT, pady=12)
        
        tk.Label(settings_win, text="⚙️ 系統設定", font=("Segoe UI", 14, "bold"), bg="#FFFFFF", fg="#2C3E50").pack(anchor="w", padx=25, pady=(20, 15))
        
        unit_frame = tk.Frame(settings_win, bg="#FFFFFF")
        unit_frame.pack(fill=tk.X, padx=25, pady=10)
        tk.Label(unit_frame, text="溫度顯示單位:", font=("Segoe UI", 10, "bold"), bg="#FFFFFF", fg="#475569").pack(side=tk.LEFT)
        
        self.unit_var = tk.StringVar(value=self.config.get("temp_unit", "C"))
        tk.Radiobutton(unit_frame, text="攝氏 (°C)", variable=self.unit_var, value="C", bg="#FFFFFF", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(20, 10))
        tk.Radiobutton(unit_frame, text="華氏 (°F)", variable=self.unit_var, value="F", bg="#FFFFFF", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=10)
        
        api_frame = tk.Frame(settings_win, bg="#FFFFFF")
        api_frame.pack(fill=tk.X, padx=25, pady=15)
        tk.Label(api_frame, text="OpenWeather API 金鑰:", font=("Segoe UI", 10, "bold"), bg="#FFFFFF", fg="#475569").pack(anchor="w")
        
        self.api_key_var = tk.StringVar(value=self.config.get("api_key", ""))
        ttk.Entry(api_frame, textvariable=self.api_key_var, font=("Segoe UI", 10), width=40).pack(anchor="w", pady=(5, 5))
        tk.Label(api_frame, text="* 留空則使用「模擬數據」。可免費至 openweathermap.org 申請金鑰。", font=("Segoe UI", 9), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w")
        
        tk.Frame(settings_win, bg="#E2E8F0", height=1).pack(fill=tk.X, padx=25, pady=10)
        
    def save_settings_action(self, window):
        self.config["temp_unit"] = self.unit_var.get()
        self.config["api_key"] = self.api_key_var.get().strip()
        save_config(self.config)
        window.destroy()
        self.refresh_favorites_list()
        current_city = self.city_label.cget("text")
        if current_city and current_city not in ["載入中...", "請重新搜尋"]:
            self.search_city(current_city)
            
if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()