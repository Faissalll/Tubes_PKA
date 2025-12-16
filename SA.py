import json
import random
import math
import copy
import csv
import os
from collections import defaultdict
from typing import List, Dict, Tuple


# Parameter SA 
INITIAL_TEMPERATURE = 2000.0     
FINAL_TEMPERATURE = 0.01         
COOLING_RATE = 0.97              
MAX_ITERATIONS = 2000            
MAX_NO_IMPROVEMENT = 500         

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
    
    num_rooms = len(ruang_list)
    solution = []

    for mk in matkul_list:
        allowed = [ts for ts in timeslots if ts["session"] in mk["allowed_sessions"]]

        if mk["sks"] == 2:
            allowed = [ts for ts in allowed if ts["type"] == 2]
        else:
            allowed = [ts for ts in allowed if ts["type"] == 3]

        if not allowed:
            allowed = timeslots

        ts = random.choice(allowed)
        room_idx = random.randrange(num_rooms)

        gene = (ts["index"], room_idx)
        solution.append(gene)

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
<<<<<<< HEAD
    penalty = calculate_penalty(solution, timeslots, ruang_list, matkul_list)
    fitness = 1.0 / (1.0 + penalty)
    return fitness, penalty


# Generate neighbor
def generate_neighbor(current_solution, timeslots, ruang_list, matkul_list) -> List[Tuple[int, int]]:

    neighbor = copy.deepcopy(current_solution)
    num_rooms = len(ruang_list)
    
    rand = random.random()
    if rand < 0.6:
        num_changes = 1
    elif rand < 0.9:
        num_changes = random.randint(2, 3)
    else:
        num_changes = random.randint(4, 5)
    
    indices = random.sample(range(len(neighbor)), min(num_changes, len(neighbor)))
    
=======
    
    penalty = calculate_penalty(solution, timeslots, ruang_list, matkul_list)
    fitness = 1.0 / (1.0 + penalty)
    return fitness, penalty


# Generate neighbor
def generate_neighbor(current_solution, timeslots, ruang_list, matkul_list) -> List[Tuple[int, int]]:

    neighbor = copy.deepcopy(current_solution)
    num_rooms = len(ruang_list)
    
    rand = random.random()
    if rand < 0.6:
        num_changes = 1
    elif rand < 0.9:
        num_changes = random.randint(2, 3)
    else:
        num_changes = random.randint(4, 5)
    
    indices = random.sample(range(len(neighbor)), min(num_changes, len(neighbor)))
    
>>>>>>> 2c91b92f8c3fde510e0fc9fbcc811645111d450b
    for i in indices:
        mk = matkul_list[i]
        
        allowed = [ts for ts in timeslots if ts["session"] in mk["allowed_sessions"]]
        
        if mk["sks"] == 2:
            allowed = [ts for ts in allowed if ts["type"] == 2]
        else:
            allowed = [ts for ts in allowed if ts["type"] == 3]
        
        if not allowed:
            allowed = timeslots
        
        ts = random.choice(allowed)
     
        if random.random() < 0.7:
            room_idx = random.randrange(num_rooms)
        else:
            room_idx = neighbor[i][1]  
        
        neighbor[i] = (ts["index"], room_idx)
    
    return neighbor

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
            print(f"\n [SUCCESS] Solusi OPTIMAL (penalty=0) ditemukan di iterasi {iteration}!")
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
                
<<<<<<< HEAD
                print(f"Iterasi {iteration:4d} | Fitness: {best_fitness:.5f} | Penalty: {best_penalty} | Temp: {temperature:.2f}")
=======
                print(f"Iterasi {iteration:4d} | NEW BEST | Fitness: {best_fitness:.5f} | Penalty: {best_penalty} | Temp: {temperature:.2f}")
>>>>>>> 2c91b92f8c3fde510e0fc9fbcc811645111d450b
            else:
                no_improvement_count += 1
        else:
            no_improvement_count += 1
        
        temperature *= COOLING_RATE
        iteration += 1
        
        if iteration % 100 == 0:
            print(f"Iterasi {iteration:4d} | Fitness: {best_fitness:.5f} | Penalty: {best_penalty} | Temp: {temperature:.2f}")
        
        if no_improvement_count >= MAX_NO_IMPROVEMENT:
            print(f"\n⚠ [EARLY STOP] Tidak ada perbaikan setelah {MAX_NO_IMPROVEMENT} iterasi")
            break
    
    print("\n" + "=" * 50)
<<<<<<< HEAD
    print(" HASIL AKHIR SIMULATED ANNEALING")
=======
    print("=== HASIL AKHIR SIMULATED ANNEALING ===")
>>>>>>> 2c91b92f8c3fde510e0fc9fbcc811645111d450b
    print("=" * 50)
    print(f"Total Iterasi: {iteration}")
    print(f"Fitness Terbaik: {best_fitness:.6f}")
    print(f"Penalty Terbaik: {best_penalty}")
    
    return best_solution, best_penalty, best_fitness

<<<<<<< HEAD
=======
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
            "paralel": mk["paralel"],
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
            f"Paralel {r['paralel']} | SKS {r['sks']} | Dosen: {r['dosen']}"
        )

>>>>>>> 2c91b92f8c3fde510e0fc9fbcc811645111d450b

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
<<<<<<< HEAD
            "kelas": mk["kelas"],
=======
            "paralel": mk["paralel"],
>>>>>>> 2c91b92f8c3fde510e0fc9fbcc811645111d450b
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

<<<<<<< HEAD
    print(f"\nFile CSV berhasil dibuat: {filepath}")
=======
    print(f"\n✓ File CSV berhasil dibuat: {filepath}")
>>>>>>> 2c91b92f8c3fde510e0fc9fbcc811645111d450b


# Run fn

def main():
    """Main function untuk menjalankan Simulated Annealing"""
    
    # Load data
    timeslots, ruang_list, matkul_list = load_data()
    
<<<<<<< HEAD
    print(f"\nData yang dimuat:")
=======
    print(f"\n📊 Data yang dimuat:")
>>>>>>> 2c91b92f8c3fde510e0fc9fbcc811645111d450b
    print(f"  - Jumlah Timeslot: {len(timeslots)}")
    print(f"  - Jumlah Ruang: {len(ruang_list)}")
    print(f"  - Jumlah Mata Kuliah: {len(matkul_list)}")
    
    # run Simulated Annealing
    best_solution, best_penalty, best_fitness = simulated_annealing(
        timeslots, ruang_list, matkul_list
    )
    
<<<<<<< HEAD
=======
    # Print jadwal 
    print("\n" + "=" * 80)
    print("JADWAL HASIL SIMULATED ANNEALING")
    print("=" * 80)
    print_schedule(best_solution, timeslots, ruang_list, matkul_list)
>>>>>>> 2c91b92f8c3fde510e0fc9fbcc811645111d450b
    
    # Export CSV
    export_to_csv(best_solution, timeslots, ruang_list, matkul_list)


if __name__ == "__main__":
    main()