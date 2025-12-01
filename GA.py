import json
import random
import csv
import os
from collections import defaultdict
from typing import List, Tuple, Dict, Any

# Konfigurasi param awal
POPULATION_SIZE = 80
NUM_GENERATIONS = 1000
TOURNAMENT_SIZE = 3
CROSSOVER_RATE = 0.8
MUTATION_RATE = 0.1
ELITISM = True  

# Hari
DAY_ORDER = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]


# Load Data 
def load_data():
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


# Inisialisasi Populasi
def create_random_individual(timeslots, ruang_list, matkul_list) -> List[Tuple[int, int]]:
    """Buat 1 individu (kromosom) random tapi tetap mengikuti allowed_sessions."""
    num_rooms = len(ruang_list)
    individual = []

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
        individual.append(gene)

    return individual


def initialize_population(pop_size, timeslots, ruang_list, matkul_list):
    return [create_random_individual(timeslots, ruang_list, matkul_list) for _ in range(pop_size)]


# Fungsi Fitness 
def compute_penalty(individual, timeslots, ruang_list, matkul_list) -> int:
    """Hitung total penalty (semakin kecil semakin baik)."""
    penalty = 0

    used_room: Dict[Tuple[str, int, str], List[int]] = defaultdict(list)
    used_dosen: Dict[Tuple[str, int, str], List[int]] = defaultdict(list)

    for i, gene in enumerate(individual):
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

# Hitung fitness
def compute_fitness(individual, timeslots, ruang_list, matkul_list) -> float:
    penalty = compute_penalty(individual, timeslots, ruang_list, matkul_list)
    return 1.0 / (1.0 + penalty), penalty


# Seleksi individu
def tournament_selection(population, fitnesses, k=TOURNAMENT_SIZE):
    """Pilih 1 individu menggunakan tournament selection."""
    selected_idx = random.sample(range(len(population)), k)
    best_idx = selected_idx[0]
    best_fit = fitnesses[best_idx]

    for idx in selected_idx[1:]:
        if fitnesses[idx] > best_fit:
            best_idx = idx
            best_fit = fitnesses[idx]

    return population[best_idx]


# Crossover 2 parent
def one_point_crossover(parent1, parent2):
    """One-point crossover. Kedua parent punya panjang sama."""
    if len(parent1) != len(parent2):
        raise ValueError("Panjang parent tidak sama")

    if random.random() > CROSSOVER_RATE:
        return parent1[:], parent2[:]

    point = random.randint(1, len(parent1) - 1)
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]
    return child1, child2


# Mutasi acak
def mutate(individual, timeslots, ruang_list, matkul_list):
    """Mutasi: dengan probabilitas tertentu, ubah timeslot atau ruang 1 gen."""
    num_rooms = len(ruang_list)

    for i, gene in enumerate(individual):
        if random.random() < MUTATION_RATE:
            ts_index, room_index = gene
            mk = matkul_list[i]

            allowed = [ts for ts in timeslots if ts["session"] in mk["allowed_sessions"]]
            if mk["sks"] == 2:
                allowed = [ts for ts in allowed if ts["type"] == 2]
            else:
                allowed = [ts for ts in allowed if ts["type"] == 3]

            if not allowed:
                allowed = timeslots

            ts = random.choice(allowed)
            if random.random() < 0.5:
                room_index = random.randrange(num_rooms)

            individual[i] = (ts["index"], room_index)

    return individual


# Cetak Jadwal 
def print_schedule(individual, timeslots, ruang_list, matkul_list):
    """Cetak jadwal dalam format manusiawi, diurutkan berdasarkan hari & sesi."""
    records = []

    for i, gene in enumerate(individual):
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
            print("\n==============================")
            print(f"Hari: {current_day}")
            print("==============================")

        print(
            f"Sesi {r['session']} ({r['start']}-{r['end']}) | "
            f"Ruang {r['room']} | {r['kode_mk']} ({r['nama']}) "
            f"Kelas {r['kelas']} | SKS {r['sks']} | Dosen: {r['dosen']}"
        )

def export_to_csv(individual, timeslots, ruang_list, matkul_list, filename="jadwal_ga.csv"):
    """Export jadwal terbaik ke file CSV."""
    records = []

    for i, gene in enumerate(individual):
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

    day_order_map = {d: i for i, d in enumerate(["Senin","Selasa","Rabu","Kamis","Jumat"])}
    records.sort(key=lambda r: (day_order_map.get(r["day"], 99), r["session"], r["room"]))

    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print(f"\nFile CSV berhasil dibuat: {filepath}")


# Main fn Loop
def run_ga():
    timeslots, ruang_list, matkul_list = load_data()

    population = initialize_population(POPULATION_SIZE, timeslots, ruang_list, matkul_list)

    best_individual = None
    best_fitness = -1.0
    best_penalty = None

    for gen in range(NUM_GENERATIONS):
        fitnesses = []
        penalties = []
        for ind in population:
            fit, pen = compute_fitness(ind, timeslots, ruang_list, matkul_list)
            fitnesses.append(fit)
            penalties.append(pen)

        for i, fit in enumerate(fitnesses):
            if fit > best_fitness:
                best_fitness = fit
                best_individual = population[i][:]
                best_penalty = penalties[i]

        if gen % 10 == 0 or gen == NUM_GENERATIONS - 1:
            print(
                f"Generasi {gen:3d} | "
                f"Fitness terbaik saat ini: {best_fitness:.5f} | "
                f"Penalty: {best_penalty}"
            )

        new_population = []

        if ELITISM:
            best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
            new_population.append(population[best_idx][:])

        while len(new_population) < POPULATION_SIZE:
            parent1 = tournament_selection(population, fitnesses, TOURNAMENT_SIZE)
            parent2 = tournament_selection(population, fitnesses, TOURNAMENT_SIZE)

            child1, child2 = one_point_crossover(parent1, parent2)

            child1 = mutate(child1, timeslots, ruang_list, matkul_list)
            child2 = mutate(child2, timeslots, ruang_list, matkul_list)

            new_population.append(child1)
            if len(new_population) < POPULATION_SIZE:
                new_population.append(child2)

        population = new_population

    # Cetak hasil jadwal setelah semua generasion
    print("\n=== HASIL AKHIR ===")
    print(f"Fitness terbaik: {best_fitness:.6f}")
    print(f"Total penalty:   {best_penalty}")
    print_schedule(best_individual, timeslots, ruang_list, matkul_list)
    export_to_csv(best_individual, timeslots, ruang_list, matkul_list)

if __name__ == "__main__":
    run_ga()
