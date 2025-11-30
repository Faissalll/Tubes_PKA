import json
import random
import math
import copy
import csv

# ==========================================
# 1. SETUP DATA
# ==========================================

days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]

# Load data sesi dari JSON
with open('dataset/sesi.json', 'r', encoding='utf-8') as f:
    sessions_data = json.load(f)

# Buat mapping SKS per sesi (type = SKS)
session_sks_map = {}
session_time_map = {}  # Untuk waktu
for sesi in sessions_data:
    key = (sesi['day'], sesi['session'])
    session_sks_map[key] = sesi['type']
    session_time_map[key] = f"{sesi['start']}-{sesi['end']}"

# Load data dari file JSON
with open('dataset/matkul.json', 'r', encoding='utf-8') as f:
    classes_data = json.load(f)

# Filter data yang valid DAN isi allowed_sessions otomatis berdasarkan SKS
valid_classes = []
for cls in classes_data:
    # Validasi field wajib
    if not all(key in cls for key in ['id', 'kode_mk', 'nama', 'paralel', 'sks', 'dosen']):
        continue
    
    # Jika allowed_sessions kosong, isi otomatis berdasarkan SKS
    if not cls.get('allowed_sessions'):
        cls_sks = cls['sks']
        allowed = []
        for (day, session), sks in session_sks_map.items():
            if sks == cls_sks:  # Cocokkan SKS mata kuliah dengan type sesi
                allowed.append(session)
        
        # Hilangkan duplikat dan urutkan
        cls['allowed_sessions'] = sorted(list(set(allowed)))
    
    # Skip jika tetap tidak ada allowed_sessions
    if not cls['allowed_sessions']:
        continue
    
    valid_classes.append(cls)

classes_data = valid_classes

# ==========================================
# 2. FUNGSI LOGIKA (Simulated Annealing)
# ==========================================

def get_random_slot(allowed_sessions):
    day = random.choice(days)
    session = random.choice(allowed_sessions)
    return {"day": day, "session": session}

def generate_initial_schedule(classes):
    schedule = {}
    for cls in classes:
        slot = get_random_slot(cls['allowed_sessions'])
        schedule[cls['id']] = slot
    return schedule

def calculate_cost(schedule, classes):
    penalty = 0
    time_slots = {}
    
    # Grouping by Day-Session
    for cls_id, slot in schedule.items():
        key = f"{slot['day']}-{slot['session']}"
        if key not in time_slots:
            time_slots[key] = []
        time_slots[key].append(cls_id)
    
    # Cek Konflik Dosen dan Paralel
    for key, class_ids in time_slots.items():
        if len(class_ids) > 1:
            lecturers = []
            codes = []
            for cid in class_ids:
                cls_obj = next((c for c in classes if c['id'] == cid), None)
                if cls_obj:
                    lecturers.extend(cls_obj['dosen'])
                    codes.append(cls_obj['kode_mk'])
            
            # Konflik Dosen (dosen sama di slot sama)
            if len(lecturers) != len(set(lecturers)):
                penalty += 1
            
            # Konflik Paralel (kode MK sama di slot sama)
            if len(codes) != len(set(codes)):
                penalty += 1
    
    return penalty

def get_neighbor(schedule, classes):
    new_schedule = copy.deepcopy(schedule)
    random_class = random.choice(classes)
    cls_id = random_class['id']
    new_slot = get_random_slot(random_class['allowed_sessions'])
    new_schedule[cls_id] = new_slot
    return new_schedule

def simulated_annealing(classes, max_iter=200, initial_temp=1000.0, cooling_rate=0.95):
    current_schedule = generate_initial_schedule(classes)
    current_cost = calculate_cost(current_schedule, classes)
    
    best_schedule = current_schedule
    best_cost = current_cost
    temp = initial_temp
    
    cost_history = []
    
    for i in range(max_iter):
        if best_cost == 0:
            break
        
        # Progress setiap 10 iterasi
        if i % 10 == 0:
            fitness = 1 / (1 + best_cost) if best_cost > 0 else 1.0
            print(f"Generasi {i:3d} | Fitness terbaik saat ini: {fitness:.5f} | Penalty: {best_cost}")
            
        neighbor_schedule = get_neighbor(current_schedule, classes)
        neighbor_cost = calculate_cost(neighbor_schedule, classes)
        delta = neighbor_cost - current_cost
        
        if delta < 0 or random.random() < math.exp(-delta / temp):
            current_schedule = neighbor_schedule
            current_cost = neighbor_cost
            if current_cost < best_cost:
                best_schedule = current_schedule
                best_cost = current_cost
        
        cost_history.append(current_cost)
        temp *= cooling_rate
    
    # Print iterasi terakhir
    fitness = 1 / (1 + best_cost) if best_cost > 0 else 1.0
    print(f"Generasi {max_iter-1:3d} | Fitness terbaik saat ini: {fitness:.5f} | Penalty: {best_cost}")
    
    return best_schedule, best_cost, cost_history

# ==========================================
# 3. EKSEKUSI & PRINT TABEL
# ==========================================

if not classes_data:
    print("[ERROR] Tidak ada data mata kuliah yang valid!")
    exit(1)

# Jalankan Algoritma
final_schedule, final_penalty, cost_history = simulated_annealing(classes_data)

# Hasil Akhir
final_fitness = 1 / (1 + final_penalty) if final_penalty > 0 else 1.0
print(f"\n=== HASIL AKHIR ===")
print(f"Fitness terbaik: {final_fitness:.6f}")
print(f"Total penalty:   {final_penalty}")

# Gabungkan jadwal dengan detail kelas
complete_schedule = []
for cls in classes_data:
    cls_id = cls['id']
    if cls_id in final_schedule:
        sched = final_schedule[cls_id]
        key = (sched['day'], sched['session'])
        waktu = session_time_map.get(key, "N/A")
        
        row = {
            "kode": cls['kode_mk'],
            "nama": cls['nama'],
            "paralel": cls['paralel'],
            "sks": cls['sks'],
            "hari": sched['day'],
            "sesi": sched['session'],
            "waktu": waktu,
            "dosen": ", ".join(cls['dosen']),
            "ruang": f"R{random.randint(1, 18)}"  # Random ruangan untuk demo
        }
        complete_schedule.append(row)

# Urutkan berdasarkan Hari, Sesi, Ruang
day_order = {"Senin": 1, "Selasa": 2, "Rabu": 3, "Kamis": 4, "Jumat": 5}
complete_schedule.sort(key=lambda x: (day_order[x['hari']], x['sesi'], x['ruang']))

# Print per hari
for day in days:
    day_schedule = [s for s in complete_schedule if s['hari'] == day]
    if not day_schedule:
        continue
    
    print(f"\n{'='*30}")
    print(f"Hari: {day}")
    print(f"{'='*30}")
    
    for item in day_schedule:
        print(f"Sesi {item['sesi']} ({item['waktu']}) | Ruang {item['ruang']} | {item['kode']} ({item['nama']}) Paralel {item['paralel']} | SKS {item['sks']} | Dosen: {item['dosen']}")

# ==========================================
# 4. EXPORT KE CSV
# ==========================================
filename = "jadwal_sa.csv"
try:
    keys = ['kode', 'nama', 'paralel', 'sks', 'hari', 'sesi', 'waktu', 'ruang', 'dosen']
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(complete_schedule)
except Exception as e:
    print(f"\n[ERROR] Gagal menyimpan CSV: {e}")