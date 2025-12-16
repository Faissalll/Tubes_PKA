import json
import random
import math
import copy
import csv
import os
from collections import defaultdict
from typing import List, Dict, Tuple


# Parameter SA 
NUM_TRIALS = 10                   # Jumlah percobaan
INITIAL_TEMPERATURE = 1000.0      # Lebih tinggi = lebih eksplorasi
FINAL_TEMPERATURE = 0.1           # Lebih rendah = lebih eksploitasi
COOLING_RATE = 0.99               # Lebih lambat = lebih banyak iterasi
ACCEPTANCE_THRESHOLD = 0.8        # Kriteria penerimaan
TARGET_FITNESS = 0.0              # Target fitness (0 = penalty minimum)
MAX_NO_IMPROVEMENT = 100          # Lebih sabar
MAX_RETRY = 3                     # Batas mengulang iterasi
MAX_ITERATIONS = 1000             # Lebih banyak iterasi

# Hari
DAY_ORDER = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]

# Load data jadwal
def load_data():
    """Load semua data dari file JSON"""
    with open("dataset/sesi.json", "r", encoding="utf-8") as f:
        sesi_list = json.load(f)

    with open("dataset/ruang.json", "r", encoding="utf-8") as f:
        ruang_list = json.load(f)

    with open("dataset/matkul.json", "r", encoding="utf-8") as f:
        matkul_list = json.load(f)

    timeslots = []
    for i, s in enumerate(sesi_list):
        timeslots.append({
            "index": i,
            "day": s["day"],
            "session": s["session"],
            "start": s["start"],
            "end": s["end"],
            "type": s["type"],  
        })

    return timeslots, ruang_list, matkul_list

# Generate solusi awal random
def generate_initial_solution(timeslots, ruang_list, matkul_list) -> List[Tuple[int, int]]:
    """Generate solusi awal dengan greedy approach"""
    solution = []
    
    # Track penggunaan ruang dan dosen per timeslot
    used_rooms = defaultdict(set)
    used_lecturers = defaultdict(set)
    
    for mk in matkul_list:
        best_penalty = float('inf')
        best_gene = None
        
        # Filter timeslot yang sesuai
        allowed = [ts for ts in timeslots if ts["session"] in mk["allowed_sessions"]]
        if mk["sks"] == 2:
            allowed = [ts for ts in allowed if ts["type"] == 2]
        else:
            allowed = [ts for ts in allowed if ts["type"] == 3]
        
        if not allowed:
            allowed = timeslots
        
        # Coba beberapa kombinasi timeslot-ruangan
        for ts in allowed:
            for room_idx in range(len(ruang_list)):
                room = ruang_list[room_idx]
                key = (ts["day"], ts["session"])
                
                # Hitung penalty untuk kombinasi ini
                temp_penalty = 0
                
                # Cek konflik ruangan
                if room in used_rooms[key]:
                    temp_penalty += 10
                
                # Cek konflik dosen
                for dosen in mk["dosen"]:
                    if dosen in used_lecturers[key]:
                        temp_penalty += 8
                
                # Pilih kombinasi dengan penalty terendah
                if temp_penalty < best_penalty:
                    best_penalty = temp_penalty
                    best_gene = (ts["index"], room_idx)
        
        # Tambahkan ke solusi dan update tracking
        solution.append(best_gene)
        ts = timeslots[best_gene[0]]
        key = (ts["day"], ts["session"])
        used_rooms[key].add(ruang_list[best_gene[1]])
        for dosen in mk["dosen"]:
            used_lecturers[key].add(dosen)
    
    return solution


# Htung penalty 
def calculate_penalty(solution, timeslots, ruang_list, matkul_list) -> int:
    """Hitung total penalty (semakin kecil semakin baik)."""
    penalty = 0

    used_room: Dict[Tuple[str, int, str], List[int]] = defaultdict(list)
    used_dosen: Dict[Tuple[str, int, str], List[int]] = defaultdict(list)

    for i, gene in enumerate(solution):
        ts_index, room_index = gene
        mk = matkul_list[i]
        ts = timeslots[ts_index]

        day = ts["day"]
        session = ts["session"]
        room = ruang_list[room_index]

        # Soft Const: Cek allowed_sessions
        if session not in mk["allowed_sessions"]:
            penalty += 5

        # Soft Const: Cek tipe slot, kalau panjang (tipe 3) untuk sks >=3, pendek (tipe 2) untuk sks 2
        if mk["sks"] == 2 and ts["type"] != 2:
            penalty += 3
        if mk["sks"] >= 3 and ts["type"] != 3:
            penalty += 3

        # Simpan penggunaan ruangan
        used_room[(day, session, room)].append(i)

        # Simpan penggunaan dosen
        for d in mk["dosen"]:
            used_dosen[(day, session, d)].append(i)

    # Hard Const Konflik ruangan: >1 kelas di hari-sesi-ruang sama
    for _, kelas_idx in used_room.items():
        if len(kelas_idx) > 1:
            conflict_count = len(kelas_idx) - 1
            penalty += 10 * conflict_count

    # Hard Const Konflik dosen: >1 kelas di hari-sesi sama untuk dosen sama
    for _, kelas_idx in used_dosen.items():
        if len(kelas_idx) > 1:
            conflict_count = len(kelas_idx) - 1
            penalty += 8 * conflict_count

    return penalty


def calculate_fitness(solution, timeslots, ruang_list, matkul_list) -> Tuple[float, int]:
    
    penalty = calculate_penalty(solution, timeslots, ruang_list, matkul_list)
    fitness = 1.0 / (1.0 + penalty)
    return fitness, penalty


# Generate neighbor
def generate_neighbor(current_solution, timeslots, ruang_list, matkul_list) -> List[Tuple[int, int]]:
    """Generate neighbor dengan strategi perbaikan konflik"""
    neighbor = copy.deepcopy(current_solution)
    
    # Identifikasi kelas dengan konflik
    conflicts = find_conflicts(neighbor, timeslots, ruang_list, matkul_list)
    
    if conflicts:
        # Prioritas perbaiki yang berkonflik
        num_changes = min(len(conflicts), random.randint(1, 3))
        indices = random.sample(conflicts, num_changes)
    else:
        # Random change jika tidak ada konflik
        num_changes = random.randint(1, 2)
        indices = random.sample(range(len(neighbor)), num_changes)
    
    for i in indices:
        mk = matkul_list[i]
        
        # Coba cari slot yang lebih baik
        allowed = [ts for ts in timeslots if ts["session"] in mk["allowed_sessions"]]
        if mk["sks"] == 2:
            allowed = [ts for ts in allowed if ts["type"] == 2]
        else:
            allowed = [ts for ts in allowed if ts["type"] == 3]
        
        if not allowed:
            allowed = timeslots
        
        # Pilih timeslot yang meminimalkan konflik
        best_penalty = float('inf')
        best_gene = neighbor[i]
        
        for _ in range(min(5, len(allowed))):  # Coba 5 slot random
            ts = random.choice(allowed)
            room_idx = random.randrange(len(ruang_list))
            
            # Test penalty jika pakai kombinasi ini
            temp_neighbor = copy.deepcopy(neighbor)
            temp_neighbor[i] = (ts["index"], room_idx)
            penalty = calculate_penalty(temp_neighbor, timeslots, ruang_list, matkul_list)
            
            if penalty < best_penalty:
                best_penalty = penalty
                best_gene = (ts["index"], room_idx)
        
        neighbor[i] = best_gene
    
    return neighbor

def find_conflicts(solution, timeslots, ruang_list, matkul_list) -> List[int]:
    """Identifikasi index kelas yang berkonflik"""
    conflicts = set()
    
    used_room = defaultdict(list)
    used_dosen = defaultdict(list)
    
    for i, gene in enumerate(solution):
        ts_index, room_index = gene
        mk = matkul_list[i]
        ts = timeslots[ts_index]
        
        key = (ts["day"], ts["session"], ruang_list[room_index])
        used_room[key].append(i)
        
        for d in mk["dosen"]:
            key_dosen = (ts["day"], ts["session"], d)
            used_dosen[key_dosen].append(i)
    
    # Tambahkan semua kelas yang berkonflik
    for kelas_list in used_room.values():
        if len(kelas_list) > 1:
            conflicts.update(kelas_list)
    
    for kelas_list in used_dosen.values():
        if len(kelas_list) > 1:
            conflicts.update(kelas_list)
    
    return list(conflicts)

def acceptance_probability(current_penalty, neighbor_penalty, temperature) -> float:
    """
    Hitung probabilitas menerima solusi yang lebih buruk
    Menggunakan Metropolis Criterion
    """
    if neighbor_penalty < current_penalty:
        return 1.0 
    
    if temperature == 0:
        return 0.0
    
    delta = neighbor_penalty - current_penalty
    return math.exp(-delta / temperature)

# Main func
def simulated_annealing(timeslots, ruang_list, matkul_list):
    
    print("\n=== MEMULAI SIMULATED ANNEALING ===")
    print(f"Parameter:")
    print(f"  - Initial Temperature: {INITIAL_TEMPERATURE}")
    print(f"  - Final Temperature: {FINAL_TEMPERATURE}")
    print(f"  - Cooling Rate: {COOLING_RATE}")
    print(f"  - Max Iterations: {MAX_ITERATIONS}")
    print(f"  - Early Stop: {MAX_NO_IMPROVEMENT} iterasi tanpa perbaikan")
    print("=" * 50)
    
    current_solution = generate_initial_solution(timeslots, ruang_list, matkul_list)
    current_fitness, current_penalty = calculate_fitness(current_solution, timeslots, ruang_list, matkul_list)
    
    best_solution = copy.deepcopy(current_solution)
    best_fitness = current_fitness
    best_penalty = current_penalty
    
    temperature = INITIAL_TEMPERATURE
    
    iteration = 0
    no_improvement_count = 0
    
    print(f"\nSolusi awal: Fitness = {current_fitness:.5f}, Penalty = {current_penalty}")
    
    while temperature > FINAL_TEMPERATURE and iteration < MAX_ITERATIONS:
        if best_penalty == 0:
            print(f"\n[SUCCESS] Solusi OPTIMAL (penalty=0) ditemukan di iterasi {iteration}!")
            break
        
        neighbor_solution = generate_neighbor(current_solution, timeslots, ruang_list, matkul_list)
        neighbor_fitness, neighbor_penalty = calculate_fitness(neighbor_solution, timeslots, ruang_list, matkul_list)
        
        accept_prob = acceptance_probability(current_penalty, neighbor_penalty, temperature)
        
        if random.random() < accept_prob:
            current_solution = neighbor_solution
            current_penalty = neighbor_penalty
            current_fitness = neighbor_fitness
            
            if current_penalty < best_penalty:
                best_solution = copy.deepcopy(current_solution)
                best_penalty = current_penalty
                best_fitness = current_fitness
                no_improvement_count = 0
                
                print(f"Iterasi {iteration:4d} | NEW BEST | Fitness: {best_fitness:.5f} | Penalty: {best_penalty} | Temp: {temperature:.2f}")
            else:
                no_improvement_count += 1
        else:
            no_improvement_count += 1
        
        temperature *= COOLING_RATE
        iteration += 1
        
        if iteration % 100 == 0:
            print(f"Iterasi {iteration:4d} | Fitness: {best_fitness:.5f} | Penalty: {best_penalty} | Temp: {temperature:.2f}")
        
        if no_improvement_count >= MAX_NO_IMPROVEMENT:
            print(f"\n[EARLY STOP] Tidak ada perbaikan setelah {MAX_NO_IMPROVEMENT} iterasi")
            break
    
    print("\n" + "=" * 50)
    print("=== HASIL AKHIR SIMULATED ANNEALING ===")
    print("=" * 50)
    print(f"Total Iterasi: {iteration}")
    print(f"Fitness Terbaik: {best_fitness:.6f}")
    print(f"Penalty Terbaik: {best_penalty}")
    
    # Sebelum return, jalankan local search
    print("\nMenjalankan Local Search untuk perbaikan akhir...")
    best_solution = local_search(best_solution, timeslots, ruang_list, matkul_list)
    best_fitness, best_penalty = calculate_fitness(best_solution, timeslots, ruang_list, matkul_list)
    
    return best_solution, best_penalty, best_fitness

def local_search(solution, timeslots, ruang_list, matkul_list, max_iter=50):
    """Perbaiki solusi dengan hill climbing lokal"""
    current = copy.deepcopy(solution)
    current_penalty = calculate_penalty(current, timeslots, ruang_list, matkul_list)
    
    for _ in range(max_iter):
        improved = False
        conflicts = find_conflicts(current, timeslots, ruang_list, matkul_list)
        
        if not conflicts:
            break
        
        for i in conflicts:
            mk = matkul_list[i]
            allowed = [ts for ts in timeslots if ts["session"] in mk["allowed_sessions"]]
            
            if mk["sks"] == 2:
                allowed = [ts for ts in allowed if ts["type"] == 2]
            else:
                allowed = [ts for ts in allowed if ts["type"] == 3]
            
            for ts in allowed:
                for room_idx in range(len(ruang_list)):
                    neighbor = copy.deepcopy(current)
                    neighbor[i] = (ts["index"], room_idx)
                    
                    new_penalty = calculate_penalty(neighbor, timeslots, ruang_list, matkul_list)
                    
                    if new_penalty < current_penalty:
                        current = neighbor
                        current_penalty = new_penalty
                        improved = True
                        break
                
                if improved:
                    break
            
            if improved:
                break
        
        if not improved:
            break
    
    return current

# Print jafwal
def print_schedule(solution, timeslots, ruang_list, matkul_list):
    """Print jadwal dalam format terstruktur per hari"""
    records = []

    for i, gene in enumerate(solution):
        ts_index, room_index = gene
        mk = matkul_list[i]
        ts = timeslots[ts_index]
        room = ruang_list[room_index]

        records.append({
            "day": ts["day"],
            "session": ts["session"],
            "start": ts["start"],
            "end": ts["end"],
            "room": room,
            "kode_mk": mk["kode_mk"],
            "nama": mk["nama"],
            "kelas": mk["kelas"],
            "sks": mk["sks"],
            "dosen": ", ".join(mk["dosen"]),
        })

    day_order_map = {d: i for i, d in enumerate(DAY_ORDER)}
    records.sort(key=lambda r: (day_order_map.get(r["day"], 99), r["session"], r["room"]))

    current_day = None
    for r in records:
        if r["day"] != current_day:
            current_day = r["day"]
            print("\n" + "=" * 80)
            print(f"Hari: {current_day}")
            print("=" * 80)

        print(
            f"Sesi {r['session']} ({r['start']}-{r['end']}) | "
            f"Ruang {r['room']} | {r['kode_mk']} ({r['nama']}) "
            f"Kelas {r['kelas']} | SKS {r['sks']} | Dosen: {r['dosen']}"
        )


def export_to_csv(solution, timeslots, ruang_list, matkul_list, filename="jadwal_sa.csv"):
    """Export jadwal ke file CSV"""
    records = []

    for i, gene in enumerate(solution):
        ts_index, room_index = gene
        mk = matkul_list[i]
        ts = timeslots[ts_index]
        room = ruang_list[room_index]

        records.append({
            "day": ts["day"],
            "session": ts["session"],
            "start": ts["start"],
            "end": ts["end"],
            "room": room,
            "kode_mk": mk["kode_mk"],
            "nama": mk["nama"],
            "kelas": mk["kelas"],
            "sks": mk["sks"],
            "dosen": ", ".join(mk["dosen"]),
        })

    day_order_map = {d: i for i, d in enumerate(DAY_ORDER)}
    records.sort(key=lambda r: (day_order_map.get(r["day"], 99), r["session"], r["room"]))

    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print(f"\nFile CSV berhasil dibuat: {filepath}")


# Run fn

def main():
    # Load data terlebih dahulu
    timeslots, ruang_list, matkul_list = load_data()
    
    all_results = []
    
    for trial in range(NUM_TRIALS):
        print(f"\n{'='*50}")
        print(f"PERCOBAAN {trial + 1}/{NUM_TRIALS}")
        print(f"{'='*50}")
        
        best_solution, best_penalty, best_fitness = simulated_annealing(
            timeslots, ruang_list, matkul_list
        )
        
        all_results.append({
            'trial': trial + 1,
            'solution': best_solution,
            'penalty': best_penalty,
            'fitness': best_fitness
        })
    
    # Pilih hasil terbaik dari semua percobaan
    best_result = min(all_results, key=lambda x: x['penalty'])
    
    print(f"\n{'='*80}")
    print(f"RINGKASAN {NUM_TRIALS} PERCOBAAN")
    print(f"{'='*80}")
    for r in all_results:
        print(f"Percobaan {r['trial']}: Penalty = {r['penalty']}, Fitness = {r['fitness']:.6f}")
    
    print(f"\nHASIL TERBAIK: Percobaan {best_result['trial']}")
    print(f"   Penalty: {best_result['penalty']}")
    print(f"   Fitness: {best_result['fitness']:.6f}")
    
    # Print & export hasil terbaik
    print_schedule(best_result['solution'], timeslots, ruang_list, matkul_list)
    export_to_csv(best_result['solution'], timeslots, ruang_list, matkul_list)


if __name__ == "__main__":
    main()